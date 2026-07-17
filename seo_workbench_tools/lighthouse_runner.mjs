import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {parseArgs} from 'node:util';

import {killAll, launch} from 'chrome-launcher';
import lighthouse from 'lighthouse';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';
import {computeMedianRun, filterToValidRuns} from 'lighthouse/core/lib/median-run.js';
import {ReportGenerator} from 'lighthouse/report/generator/report-generator.js';

const require = createRequire(import.meta.url);
const lighthousePackage = require('lighthouse/package.json');
const SCHEMA_VERSION = '1.0';
const RUNNER_VERSION = '0.1.0';
const METRICS = [
  'first-contentful-paint',
  'largest-contentful-paint',
  'speed-index',
  'total-blocking-time',
  'cumulative-layout-shift',
  'interactive',
];
let activeChrome = null;
let activeChromePidPath = null;
let shuttingDown = false;

async function stopForSignal(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  try {
    if (activeChrome) await activeChrome.kill();
  } finally {
    killAll();
    if (activeChromePidPath) await fs.rm(activeChromePidPath, {force: true});
    const exitCodes = {SIGINT: 130, SIGTERM: 143, SIGHUP: 129};
    process.exit(exitCodes[signal] || 1);
  }
}

for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
  process.on(signal, () => void stopForSignal(signal));
}

function parseOptions(argv) {
  const {values} = parseArgs({
    args: argv,
    strict: true,
    options: {
      url: {type: 'string'},
      'output-dir': {type: 'string'},
      runs: {type: 'string', default: '5'},
      'form-factor': {type: 'string', default: 'mobile'},
      'chrome-path': {type: 'string'},
      'proxy-server': {type: 'string'},
      'max-wait-for-load': {type: 'string', default: '45000'},
      'self-test': {type: 'boolean', default: false},
    },
  });
  if (values['self-test']) return {selfTest: true};
  if (!values.url || !values['output-dir'] || !values['chrome-path'] || !values['proxy-server']) {
    throw new Error('--url, --output-dir, --chrome-path, and --proxy-server are required');
  }
  const runs = Number.parseInt(values.runs, 10);
  const maxWaitForLoad = Number.parseInt(values['max-wait-for-load'], 10);
  if (!Number.isInteger(runs) || (runs !== 1 && (runs < 3 || runs > 9))) {
    throw new Error('--runs must be 1 for a smoke test or an integer between 3 and 9 for analysis');
  }
  if (!Number.isInteger(maxWaitForLoad) || maxWaitForLoad < 1000 || maxWaitForLoad > 180000) {
    throw new Error('--max-wait-for-load must be between 1000 and 180000 milliseconds');
  }
  if (!['mobile', 'desktop'].includes(values['form-factor'])) {
    throw new Error('--form-factor must be mobile or desktop');
  }
  const target = validateURL(values.url);
  const proxyServer = new URL(values['proxy-server']);
  if (proxyServer.protocol !== 'http:' || proxyServer.hostname !== '127.0.0.1' || !proxyServer.port) {
    throw new Error('--proxy-server must be an HTTP proxy bound to 127.0.0.1');
  }
  return {
    selfTest: false,
    url: target.toString(),
    outputDir: path.resolve(values['output-dir']),
    runs,
    formFactor: values['form-factor'],
    chromePath: path.resolve(values['chrome-path']),
    proxyServer: proxyServer.origin,
    maxWaitForLoad,
  };
}

function redactURL(raw) {
  try {
    const target = new URL(raw);
    if (!['http:', 'https:'].includes(target.protocol)) return raw;
    target.username = '';
    target.password = '';
    for (const key of [...target.searchParams.keys()]) {
      if (sensitiveQueryKey(key)) target.searchParams.set(key, '[REDACTED]');
    }
    return target.toString();
  } catch {
    return raw;
  }
}

function redactString(value) {
  const urlsRedacted = /^https?:\/\/\S+$/i.test(value)
    ? redactURL(value)
    : value.replace(/https?:\/\/[^\s"'<>]+/gi, match => redactURL(match));
  return urlsRedacted.replace(/([?&])([^?&=#\s"'<>]+)=([^&#\s"'<>\])}]*)/gi, (match, separator, rawKey) => {
    let key = rawKey;
    try {
      key = decodeURIComponent(rawKey);
    } catch {
      // Keep the raw key when percent-decoding is invalid.
    }
    return sensitiveQueryKey(key) ? `${separator}${rawKey}=[REDACTED]` : match;
  });
}

function redactValue(value) {
  if (typeof value === 'string') return redactString(value);
  if (Array.isArray(value)) return value.map(redactValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, redactValue(child)]));
  }
  return value;
}

function browserVersion(chromePath) {
  try {
    return execFileSync(chromePath, ['--version'], {encoding: 'utf8', timeout: 5000}).trim();
  } catch {
    return '';
  }
}

async function writePrivate(filePath, content) {
  await fs.writeFile(filePath, content, {mode: 0o600});
}

function sensitiveQueryKey(key) {
  const normalized = key.toLowerCase().replaceAll('-', '_');
  if (['key', 'api_key', 'apikey', 'auth', 'authorization', 'sig', 'code'].includes(normalized)) return true;
  return ['token', 'secret', 'signature', 'credential', 'password'].some(fragment => normalized.includes(fragment));
}

function validateURL(raw) {
  const target = new URL(raw);
  if (!['http:', 'https:'].includes(target.protocol)) throw new Error('only http and https URLs are supported');
  if (target.username || target.password) throw new Error('URL userinfo is not allowed');
  for (const key of target.searchParams.keys()) {
    if (sensitiveQueryKey(key)) throw new Error(`sensitive query parameter is not allowed in performance reports: ${key}`);
  }
  target.hash = '';
  return target;
}

function median(values) {
  const sorted = values.slice().sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function stats(values) {
  if (!values.length) return null;
  const middle = median(values);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  return {
    min: minimum,
    median: middle,
    max: maximum,
    range: maximum - minimum,
    range_percent: middle === 0 ? null : Math.round(((maximum - minimum) / middle) * 1000) / 10,
  };
}

function summarizeRuns(runs) {
  const performanceScores = runs
    .map(run => run.categories?.performance?.score)
    .filter(Number.isFinite)
    .map(score => Math.round(score * 1000) / 10);
  const metrics = {};
  for (const auditId of METRICS) {
    const values = runs.map(run => run.audits?.[auditId]?.numericValue).filter(Number.isFinite);
    metrics[auditId] = {
      ...stats(values),
      unit: runs.find(run => run.audits?.[auditId])?.audits[auditId].numericUnit || '',
      display_value: runs.find(run => run.audits?.[auditId])?.audits[auditId].displayValue || '',
    };
  }
  const scoreStats = stats(performanceScores);
  const varianceReasons = [];
  if ((scoreStats?.range || 0) >= 10) {
    varianceReasons.push(`performance score range is ${scoreStats.range} points`);
  }
  for (const [auditId, metric] of Object.entries(metrics)) {
    if (metric?.range_percent !== null && metric?.range_percent > 30) {
      varianceReasons.push(`${auditId} range is ${metric.range_percent}% of its median`);
    }
  }
  return {
    performance_score: scoreStats,
    metrics,
    high_variance: varianceReasons.length > 0,
    variance_reasons: varianceReasons,
  };
}

async function runLighthouse(options) {
  let chrome;
  try {
    chrome = await launch({
      chromePath: options.chromePath,
      chromeFlags: [
        '--headless=new',
        '--disable-extensions',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-quic',
        '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
        `--proxy-server=${options.proxyServer}`,
        '--proxy-bypass-list=<-loopback>',
      ],
      logLevel: 'silent',
    });
  } catch (error) {
    killAll();
    throw error;
  }
  activeChrome = chrome;
  const chromePidPath = path.join(options.outputDir, '.chrome.pid');
  activeChromePidPath = chromePidPath;
  let timer;
  try {
    await writePrivate(chromePidPath, `${chrome.pid}\n`);
    const flags = {
      port: chrome.port,
      logLevel: 'error',
      output: 'json',
      onlyCategories: ['performance'],
      maxWaitForLoad: options.maxWaitForLoad,
      enableErrorReporting: false,
    };
    const config = options.formFactor === 'desktop' ? desktopConfig : undefined;
    const result = await Promise.race([
      lighthouse(options.url, flags, config),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Lighthouse run exceeded its hard timeout')), options.maxWaitForLoad + 30000);
      }),
    ]);
    if (!result?.lhr) throw new Error('Lighthouse did not return an LHR');
    return redactValue(result.lhr);
  } finally {
    clearTimeout(timer);
    try {
      await chrome.kill();
    } finally {
      killAll();
      await fs.rm(chromePidPath, {force: true});
      if (activeChrome === chrome) activeChrome = null;
      activeChromePidPath = null;
    }
  }
}

async function execute(options) {
  await fs.mkdir(options.outputDir, {recursive: true, mode: 0o700});
  const successfulRuns = [];
  const errors = [];
  for (let index = 0; index < options.runs; index += 1) {
    try {
      const lhr = await runLighthouse(options);
      successfulRuns.push({index: index + 1, lhr});
      await writePrivate(
        path.join(options.outputDir, `run-${String(index + 1).padStart(2, '0')}.json`),
        `${JSON.stringify(lhr, null, 2)}\n`,
      );
    } catch (error) {
      errors.push({run: index + 1, error: redactString(error instanceof Error ? error.message : String(error))});
    }
  }

  const minimumSuccessfulRuns = options.runs === 1 ? 1 : Math.min(3, options.runs);
  const validRuns = filterToValidRuns(successfulRuns.map(item => item.lhr));
  for (const item of successfulRuns) {
    if (!validRuns.includes(item.lhr)) {
      errors.push({run: item.index, error: 'Lighthouse result was missing FCP or TTI and cannot be aggregated'});
    }
  }
  const enoughRuns = validRuns.length >= minimumSuccessfulRuns;
  let representative = null;
  let representativeRun = null;
  if (enoughRuns) {
    representative = computeMedianRun(validRuns);
    representativeRun = successfulRuns.find(item => item.lhr === representative)?.index || null;
    await writePrivate(path.join(options.outputDir, 'representative.json'), `${JSON.stringify(representative, null, 2)}\n`);
    await writePrivate(path.join(options.outputDir, 'report.html'), ReportGenerator.generateReportHtml(representative));
  }

  const collectionStatus = enoughRuns ? (validRuns.length === options.runs ? 'ok' : 'partial') : 'failed';
  const aggregate = summarizeRuns(validRuns);
  const runFinalUrls = [...new Set(validRuns
    .map(run => run.finalUrl || run.finalDisplayedUrl || run.mainDocumentUrl || options.url)
    .filter(Boolean))];
  const finalUrl = representative?.finalUrl || representative?.finalDisplayedUrl || representative?.mainDocumentUrl || options.url;
  const mainDocumentUrl = representative?.mainDocumentUrl || finalUrl;
  const redirected = finalUrl !== options.url;
  const redirectConsistent = runFinalUrls.length <= 1;
  const warnings = aggregate.high_variance
    ? [{scope: 'performance', message: `high variance detected: ${aggregate.variance_reasons.join('; ')}`}]
    : [];
  if (redirected) {
    warnings.push({scope: 'navigation', message: `requested URL redirected to ${finalUrl}`});
  }
  if (!redirectConsistent) {
    warnings.push({scope: 'navigation', message: `Lighthouse runs ended on different URLs: ${runFinalUrls.join(', ')}`});
  }
  const summary = {
    schema_version: SCHEMA_VERSION,
    runner_version: RUNNER_VERSION,
    lighthouse_version: lighthousePackage.version,
    generated_at: new Date().toISOString(),
    collection_status: collectionStatus,
    url: options.url,
    requested_url: options.url,
    final_url: finalUrl,
    main_document_url: mainDocumentUrl,
    redirected,
    run_final_urls: runFinalUrls,
    redirect_consistent: redirectConsistent,
    form_factor: options.formFactor,
    runs_requested: options.runs,
    runs_succeeded: validRuns.length,
    valid_runs: validRuns.length,
    minimum_successful_runs: minimumSuccessfulRuns,
    representative_run: representativeRun,
    aggregate,
    environment: {
      node_version: process.version,
      chrome_path: options.chromePath,
      browser_version: browserVersion(options.chromePath),
      user_agent: representative?.environment?.hostUserAgent || '',
      benchmark_index: representative?.environment?.benchmarkIndex ?? null,
    },
    errors,
    warnings,
    artifacts: {
      output_dir: options.outputDir,
      representative_json: representative ? path.join(options.outputDir, 'representative.json') : '',
      report_html: representative ? path.join(options.outputDir, 'report.html') : '',
      summary_json: path.join(options.outputDir, 'summary.json'),
    },
  };
  await writePrivate(path.join(options.outputDir, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`);
  return summary;
}

function selfTest() {
  const fixture = value => ({
    categories: {performance: {score: value / 100}},
    audits: Object.fromEntries(METRICS.map(metric => [metric, {numericValue: value, numericUnit: 'millisecond'}])),
  });
  const runs = [fixture(80), fixture(100), fixture(90)];
  const aggregate = summarizeRuns(runs);
  if (aggregate.performance_score.median !== 90 || aggregate.performance_score.range !== 20) {
    throw new Error('aggregate self-test failed');
  }
  if (!aggregate.high_variance || !aggregate.variance_reasons.length) {
    throw new Error('variance self-test failed');
  }
  if (computeMedianRun(runs) !== runs[2]) throw new Error('median run self-test failed');
  validateURL('https://example.com/path?utm_source=test');
  let rejected = false;
  try {
    validateURL('https://example.com/?access_token=secret');
  } catch {
    rejected = true;
  }
  if (!rejected) throw new Error('sensitive URL self-test failed');
  const redacted = redactURL('https://user:password@example.com/path?access_token=secret&utm_source=test');
  if (redacted.includes('password') || redacted.includes('secret') || !redacted.includes('%5BREDACTED%5D')) {
    throw new Error('URL redaction self-test failed');
  }
  const relativeRedacted = redactString('<img src="//cdn.example/x?access_token=secret"><a href="/x?signature=secret">');
  if (relativeRedacted.includes('secret')) throw new Error('relative URL redaction self-test failed');
  return {ok: true, lighthouse_version: lighthousePackage.version, runner_version: RUNNER_VERSION};
}

try {
  const options = parseOptions(process.argv.slice(2));
  const result = options.selfTest ? selfTest() : await execute(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (!options.selfTest && result.collection_status === 'failed') process.exitCode = 1;
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}
