import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';

import {launch} from 'chrome-launcher';
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
      'max-wait-for-load': {type: 'string', default: '45000'},
      'self-test': {type: 'boolean', default: false},
    },
  });
  if (values['self-test']) return {selfTest: true};
  if (!values.url || !values['output-dir'] || !values['chrome-path']) {
    throw new Error('--url, --output-dir, and --chrome-path are required');
  }
  const runs = Number.parseInt(values.runs, 10);
  const maxWaitForLoad = Number.parseInt(values['max-wait-for-load'], 10);
  if (!Number.isInteger(runs) || runs < 1 || runs > 9) {
    throw new Error('--runs must be an integer between 1 and 9');
  }
  if (!Number.isInteger(maxWaitForLoad) || maxWaitForLoad < 1000 || maxWaitForLoad > 180000) {
    throw new Error('--max-wait-for-load must be between 1000 and 180000 milliseconds');
  }
  if (!['mobile', 'desktop'].includes(values['form-factor'])) {
    throw new Error('--form-factor must be mobile or desktop');
  }
  const target = validateURL(values.url);
  return {
    selfTest: false,
    url: target.toString(),
    outputDir: path.resolve(values['output-dir']),
    runs,
    formFactor: values['form-factor'],
    chromePath: path.resolve(values['chrome-path']),
    maxWaitForLoad,
  };
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
  const highMetricVariance = Object.values(metrics).some(metric => metric?.range_percent !== null && metric?.range_percent > 30);
  return {
    performance_score: scoreStats,
    metrics,
    high_variance: Boolean((scoreStats?.range || 0) >= 10 || highMetricVariance),
  };
}

async function runLighthouse(options) {
  const chrome = await launch({
    chromePath: options.chromePath,
    chromeFlags: ['--headless=new', '--disable-extensions', '--no-first-run', '--no-default-browser-check'],
    logLevel: 'silent',
  });
  try {
    const flags = {
      port: chrome.port,
      logLevel: 'error',
      output: 'json',
      onlyCategories: ['performance'],
      maxWaitForLoad: options.maxWaitForLoad,
      enableErrorReporting: false,
    };
    const config = options.formFactor === 'desktop' ? desktopConfig : undefined;
    const result = await lighthouse(options.url, flags, config);
    if (!result?.lhr) throw new Error('Lighthouse did not return an LHR');
    return result.lhr;
  } finally {
    await chrome.kill();
  }
}

async function execute(options) {
  await fs.mkdir(options.outputDir, {recursive: true});
  const successfulRuns = [];
  const errors = [];
  for (let index = 0; index < options.runs; index += 1) {
    try {
      const lhr = await runLighthouse(options);
      successfulRuns.push({index: index + 1, lhr});
      await fs.writeFile(
        path.join(options.outputDir, `run-${String(index + 1).padStart(2, '0')}.json`),
        `${JSON.stringify(lhr, null, 2)}\n`,
      );
    } catch (error) {
      errors.push({run: index + 1, error: error instanceof Error ? error.message : String(error)});
    }
  }

  const minimumSuccessfulRuns = options.runs === 1 ? 1 : Math.min(3, options.runs);
  const validRuns = filterToValidRuns(successfulRuns.map(item => item.lhr));
  const enoughRuns = validRuns.length >= minimumSuccessfulRuns;
  let representative = null;
  let representativeRun = null;
  if (enoughRuns) {
    representative = computeMedianRun(validRuns);
    representativeRun = successfulRuns.find(item => item.lhr === representative)?.index || null;
    await fs.writeFile(path.join(options.outputDir, 'representative.json'), `${JSON.stringify(representative, null, 2)}\n`);
    await fs.writeFile(path.join(options.outputDir, 'report.html'), ReportGenerator.generateReportHtml(representative));
  }

  const collectionStatus = enoughRuns ? (successfulRuns.length === options.runs ? 'ok' : 'partial') : 'failed';
  const aggregate = summarizeRuns(validRuns);
  const summary = {
    schema_version: SCHEMA_VERSION,
    runner_version: RUNNER_VERSION,
    lighthouse_version: lighthousePackage.version,
    generated_at: new Date().toISOString(),
    collection_status: collectionStatus,
    url: options.url,
    form_factor: options.formFactor,
    runs_requested: options.runs,
    runs_succeeded: successfulRuns.length,
    valid_runs: validRuns.length,
    minimum_successful_runs: minimumSuccessfulRuns,
    representative_run: representativeRun,
    aggregate,
    environment: {
      node_version: process.version,
      chrome_path: options.chromePath,
      user_agent: representative?.environment?.hostUserAgent || '',
      benchmark_index: representative?.environment?.benchmarkIndex ?? null,
    },
    errors,
    warnings: aggregate.high_variance
      ? [{scope: 'performance', message: 'high variance detected; compare this result cautiously'}]
      : [],
    artifacts: {
      output_dir: options.outputDir,
      representative_json: representative ? path.join(options.outputDir, 'representative.json') : '',
      report_html: representative ? path.join(options.outputDir, 'report.html') : '',
      summary_json: path.join(options.outputDir, 'summary.json'),
    },
  };
  await fs.writeFile(path.join(options.outputDir, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`);
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
  if (computeMedianRun(runs) !== runs[2]) throw new Error('median run self-test failed');
  validateURL('https://example.com/path?utm_source=test');
  let rejected = false;
  try {
    validateURL('https://example.com/?access_token=secret');
  } catch {
    rejected = true;
  }
  if (!rejected) throw new Error('sensitive URL self-test failed');
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
