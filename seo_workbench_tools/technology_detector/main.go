package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"os"
	"runtime/debug"
	"sort"
	"strings"
	"sync"
	"time"

	wappalyzer "github.com/projectdiscovery/wappalyzergo"
)

const (
	detectorVersion = "0.1.0"
	providerModule  = "github.com/projectdiscovery/wappalyzergo"
	userAgent       = "SEO-Workbench/0.2 (+https://github.com/seo-workbench)"
	maxBodyBytes    = 10 * 1024 * 1024
	maxConcurrency  = 4
)

type urlList []string

func (values *urlList) String() string { return strings.Join(*values, ",") }

func (values *urlList) Set(value string) error {
	value = strings.TrimSpace(value)
	if value == "" {
		return fmt.Errorf("url cannot be empty")
	}
	*values = append(*values, value)
	return nil
}

type technology struct {
	Name        string   `json:"name"`
	Version     string   `json:"version,omitempty"`
	Categories  []string `json:"categories"`
	Description string   `json:"description,omitempty"`
	Website     string   `json:"website,omitempty"`
	CPE         string   `json:"cpe,omitempty"`
	Icon        string   `json:"icon,omitempty"`
}

type pageResult struct {
	URL               string       `json:"url"`
	FinalURL          string       `json:"final_url,omitempty"`
	StatusCode        int          `json:"status_code,omitempty"`
	ContentType       string       `json:"content_type,omitempty"`
	BodyBytes         int          `json:"body_bytes,omitempty"`
	FingerprintInputs []string     `json:"fingerprint_inputs,omitempty"`
	Technologies      []technology `json:"technologies"`
	Error             string       `json:"error,omitempty"`
}

var blockedPrefixes = []netip.Prefix{
	netip.MustParsePrefix("100.64.0.0/10"),
	netip.MustParsePrefix("192.0.0.0/24"),
	netip.MustParsePrefix("198.18.0.0/15"),
}

func providerVersion() string {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return "unknown"
	}
	for _, dependency := range info.Deps {
		if dependency.Path != providerModule {
			continue
		}
		if dependency.Replace != nil {
			dependency = dependency.Replace
		}
		return dependency.Version
	}
	return "unknown"
}

func sensitiveQueryKey(key string) bool {
	normalized := strings.ToLower(strings.ReplaceAll(key, "-", "_"))
	for _, fragment := range []string{"token", "secret", "signature", "credential", "password"} {
		if strings.Contains(normalized, fragment) {
			return true
		}
	}
	switch normalized {
	case "key", "api_key", "apikey", "auth", "authorization", "sig", "code":
		return true
	default:
		return false
	}
}

func redactedURL(raw string) string {
	parsed, err := url.Parse(raw)
	if err != nil {
		return "invalid-url"
	}
	parsed.User = nil
	parsed.Fragment = ""
	query := parsed.Query()
	for key := range query {
		if sensitiveQueryKey(key) {
			query.Set(key, "REDACTED")
		}
	}
	parsed.RawQuery = query.Encode()
	return parsed.String()
}

func validateTarget(target *url.URL) error {
	if target.Scheme != "http" && target.Scheme != "https" {
		return fmt.Errorf("only http and https URLs are supported")
	}
	if target.Hostname() == "" {
		return fmt.Errorf("URL host is required")
	}
	if target.User != nil {
		return fmt.Errorf("URL userinfo is not allowed")
	}
	return nil
}

func publicAddress(address netip.Addr) bool {
	address = address.Unmap()
	if !address.IsGlobalUnicast() || address.IsPrivate() || address.IsLoopback() || address.IsLinkLocalUnicast() {
		return false
	}
	for _, prefix := range blockedPrefixes {
		if prefix.Contains(address) {
			return false
		}
	}
	return true
}

func restrictedDialContext(allowPrivate bool) func(context.Context, string, string) (net.Conn, error) {
	dialer := &net.Dialer{Timeout: 10 * time.Second, KeepAlive: 30 * time.Second}
	return func(ctx context.Context, network, address string) (net.Conn, error) {
		if allowPrivate {
			return dialer.DialContext(ctx, network, address)
		}
		host, port, err := net.SplitHostPort(address)
		if err != nil {
			return nil, fmt.Errorf("parse network address: %w", err)
		}
		addresses, err := net.DefaultResolver.LookupNetIP(ctx, "ip", host)
		if err != nil {
			return nil, err
		}
		var lastErr error
		for _, resolved := range addresses {
			if !publicAddress(resolved) {
				continue
			}
			connection, dialErr := dialer.DialContext(ctx, network, net.JoinHostPort(resolved.String(), port))
			if dialErr == nil {
				return connection, nil
			}
			lastErr = dialErr
		}
		if lastErr != nil {
			return nil, lastErr
		}
		return nil, fmt.Errorf("target resolves only to non-public addresses; use -allow-private for a trusted local target")
	}
}

func httpClient(timeout time.Duration, allowPrivate bool) *http.Client {
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.Proxy = nil
	transport.DialContext = restrictedDialContext(allowPrivate)
	return &http.Client{
		Timeout:   timeout,
		Transport: transport,
		CheckRedirect: func(request *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return fmt.Errorf("stopped after 10 redirects")
			}
			return validateTarget(request.URL)
		},
	}
}

func requestError(err error) string {
	if urlError, ok := err.(*url.Error); ok {
		return fmt.Sprintf("%s request failed: %v", urlError.Op, urlError.Err)
	}
	return err.Error()
}

type issue struct {
	Scope   string `json:"scope"`
	URL     string `json:"url,omitempty"`
	Error   string `json:"error,omitempty"`
	Message string `json:"message,omitempty"`
}

type report struct {
	SchemaVersion    string       `json:"schema_version"`
	DetectorVersion  string       `json:"detector_version"`
	Provider         string       `json:"provider"`
	ProviderVersion  string       `json:"provider_version"`
	GeneratedAt      string       `json:"generated_at"`
	CollectionStatus string       `json:"collection_status"`
	Pages            []pageResult `json:"pages"`
	Errors           []issue      `json:"errors"`
	Warnings         []issue      `json:"warnings"`
}

func splitTechnologyVersion(value string) (string, string) {
	index := strings.LastIndex(value, ":")
	if index <= 0 || index == len(value)-1 {
		return value, ""
	}
	return value[:index], value[index+1:]
}

func normalizeTechnologies(apps map[string]wappalyzer.AppInfo) []technology {
	items := make([]technology, 0, len(apps))
	for key, info := range apps {
		name, version := splitTechnologyVersion(key)
		categories := append([]string(nil), info.Categories...)
		sort.Strings(categories)
		items = append(items, technology{
			Name:        name,
			Version:     version,
			Categories:  categories,
			Description: info.Description,
			Website:     info.Website,
			CPE:         info.CPE,
			Icon:        info.Icon,
		})
	}
	sort.Slice(items, func(i, j int) bool {
		if items[i].Name == items[j].Name {
			return items[i].Version < items[j].Version
		}
		return items[i].Name < items[j].Name
	})
	return items
}

func detectTechnologies(detector *wappalyzer.Wappalyze, headers http.Header, body []byte) []technology {
	return normalizeTechnologies(detector.FingerprintWithInfo(headers, body))
}

func collectPage(client *http.Client, detector *wappalyzer.Wappalyze, target string) (pageResult, []issue) {
	publicTarget := redactedURL(target)
	result := pageResult{URL: publicTarget, Technologies: []technology{}}
	request, err := http.NewRequest(http.MethodGet, target, nil)
	if err != nil {
		result.Error = "invalid URL"
		return result, nil
	}
	if err := validateTarget(request.URL); err != nil {
		result.Error = err.Error()
		return result, nil
	}
	request.Header.Set("User-Agent", userAgent)

	response, err := client.Do(request)
	if err != nil {
		result.Error = requestError(err)
		return result, nil
	}
	defer response.Body.Close()

	body, err := io.ReadAll(io.LimitReader(response.Body, maxBodyBytes+1))
	if err != nil {
		result.Error = err.Error()
		return result, nil
	}
	warnings := []issue{}
	if len(body) > maxBodyBytes {
		body = body[:maxBodyBytes]
		warnings = append(warnings, issue{
			Scope:   "technology",
			URL:     publicTarget,
			Message: "response body exceeded 10 MiB and was truncated before fingerprinting",
		})
	}

	result.FinalURL = redactedURL(response.Request.URL.String())
	result.StatusCode = response.StatusCode
	result.ContentType = response.Header.Get("Content-Type")
	result.BodyBytes = len(body)
	result.FingerprintInputs = []string{"response_headers", "set_cookie", "raw_html"}
	result.Technologies = detectTechnologies(detector, response.Header, body)
	if response.StatusCode < 200 || response.StatusCode >= 400 {
		warnings = append(warnings, issue{
			Scope:   "technology",
			URL:     publicTarget,
			Message: fmt.Sprintf("technology fingerprinting used HTTP status %d", response.StatusCode),
		})
	}
	return result, warnings
}

func run(targets []string, timeout time.Duration, allowPrivate bool) (report, error) {
	if timeout <= 0 {
		return report{}, fmt.Errorf("timeout must be greater than zero")
	}
	detector, err := wappalyzer.New()
	if err != nil {
		return report{}, fmt.Errorf("load technology fingerprints: %w", err)
	}
	client := httpClient(timeout, allowPrivate)
	output := report{
		SchemaVersion:    "1.0",
		DetectorVersion:  detectorVersion,
		Provider:         "projectdiscovery/wappalyzergo",
		ProviderVersion:  providerVersion(),
		GeneratedAt:      time.Now().UTC().Format(time.RFC3339Nano),
		CollectionStatus: "ok",
		Pages:            make([]pageResult, 0, len(targets)),
		Errors:           []issue{},
		Warnings:         []issue{},
	}
	type collectionResult struct {
		page     pageResult
		warnings []issue
	}
	results := make([]collectionResult, len(targets))
	jobs := make(chan int)
	workers := min(maxConcurrency, len(targets))
	var waitGroup sync.WaitGroup
	for range workers {
		waitGroup.Add(1)
		go func() {
			defer waitGroup.Done()
			for index := range jobs {
				page, warnings := collectPage(client, detector, targets[index])
				results[index] = collectionResult{page: page, warnings: warnings}
			}
		}()
	}
	for index := range targets {
		jobs <- index
	}
	close(jobs)
	waitGroup.Wait()

	successful := 0
	for index, result := range results {
		output.Pages = append(output.Pages, result.page)
		output.Warnings = append(output.Warnings, result.warnings...)
		page := result.page
		if page.Error != "" {
			output.Errors = append(output.Errors, issue{Scope: "technology", URL: redactedURL(targets[index]), Error: page.Error})
			continue
		}
		successful++
	}
	if successful == 0 {
		output.CollectionStatus = "failed"
	} else if len(output.Errors) > 0 {
		output.CollectionStatus = "partial"
	}
	return output, nil
}

func main() {
	var targets urlList
	var timeout time.Duration
	var allowPrivate bool
	flag.Var(&targets, "url", "URL to inspect; repeat for additional pages")
	flag.DurationVar(&timeout, "timeout", 20*time.Second, "per-request timeout")
	flag.BoolVar(&allowPrivate, "allow-private", false, "allow trusted private, loopback, and link-local targets")
	flag.Parse()
	if len(targets) == 0 {
		fmt.Fprintln(os.Stderr, "at least one -url is required")
		os.Exit(2)
	}

	output, err := run(targets, timeout, allowPrivate)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
