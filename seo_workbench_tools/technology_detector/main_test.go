package main

import (
	"net/http"
	"net/netip"
	"strings"
	"testing"
	"time"

	wappalyzer "github.com/projectdiscovery/wappalyzergo"
)

func TestSplitTechnologyVersion(t *testing.T) {
	name, version := splitTechnologyVersion("PHP:8.3.1")
	if name != "PHP" || version != "8.3.1" {
		t.Fatalf("unexpected split: %q %q", name, version)
	}
	name, version = splitTechnologyVersion("WordPress")
	if name != "WordPress" || version != "" {
		t.Fatalf("unexpected unversioned split: %q %q", name, version)
	}
}

func TestCollectPageDetectsKnownTechnologies(t *testing.T) {
	detector, err := wappalyzer.New()
	if err != nil {
		t.Fatal(err)
	}
	headers := http.Header{
		"Content-Type": {"text/html; charset=utf-8"},
		"X-Powered-By": {"PHP/8.3.1"},
	}
	items := detectTechnologies(detector, headers, []byte(`<!doctype html><meta name="generator" content="WordPress 6.5"><script src="/wp-includes/js/jquery/jquery.min.js"></script>`))
	found := map[string]bool{}
	for _, item := range items {
		found[item.Name] = true
	}
	if !found["PHP"] || !found["WordPress"] {
		t.Fatalf("expected PHP and WordPress, got %#v", items)
	}
}

func TestRunKeepsStructuredFailure(t *testing.T) {
	output, err := run([]string{"http://127.0.0.1:1"}, 50*time.Millisecond, true)
	if err != nil {
		t.Fatal(err)
	}
	if output.CollectionStatus != "failed" || len(output.Errors) != 1 {
		t.Fatalf("unexpected output: %#v", output)
	}
}

func TestRunRejectsNonPositiveTimeout(t *testing.T) {
	if _, err := run([]string{"https://example.com"}, 0, false); err == nil {
		t.Fatal("expected non-positive timeout to fail")
	}
}

func TestPrivateAddressesAreBlockedByDefault(t *testing.T) {
	for _, raw := range []string{"127.0.0.1", "10.0.0.1", "169.254.169.254", "100.64.0.1", "::1", "fc00::1"} {
		address, err := netip.ParseAddr(raw)
		if err != nil {
			t.Fatal(err)
		}
		if publicAddress(address) {
			t.Fatalf("expected %s to be blocked", raw)
		}
	}
}

func TestProxyFakeIPRangeIsAllowedByDefault(t *testing.T) {
	address := netip.MustParseAddr("198.18.0.26")
	if !publicAddress(address) {
		t.Fatal("expected transparent-proxy fake IP range to be allowed")
	}
}

func TestReportURLsRedactSecrets(t *testing.T) {
	redacted := redactedURL("https://user:pass@example.com/path?utm_source=test&access_token=secret&X-Amz-Signature=signed#fragment")
	if strings.Contains(redacted, "user") || strings.Contains(redacted, "secret") || strings.Contains(redacted, "signed") || strings.Contains(redacted, "fragment") {
		t.Fatalf("URL was not redacted: %s", redacted)
	}
}
