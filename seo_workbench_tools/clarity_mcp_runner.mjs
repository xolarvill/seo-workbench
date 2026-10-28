// Fixed Clarity MCP client. No arbitrary commands, endpoints or tool names.
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tools = ['query-analytics-dashboard', 'list-session-recordings', 'query-documentation-resources'];
const expected = '2.0.1';
let transport;
let client;
let timer;
let ending = false;
async function close() {
  if (ending) return;
  ending = true;
  clearTimeout(timer);
  try { await client?.close(); } catch { /* Parent also cleans the process group. */ }
  try { await transport?.close(); } catch { /* Parent also cleans the process group. */ }
}
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => { void close().finally(() => process.exit(1)); });

async function main() {
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk;
    if (Buffer.byteLength(input) > 32768) throw new Error('invalid_request');
  }
  const request = JSON.parse(input || '{}');
  if (!['discover', ...tools].includes(request.tool)) throw new Error('invalid_request');
  const pkg = JSON.parse(readFileSync(path.join(root, 'node_modules/@microsoft/clarity-mcp-server/package.json')));
  if (pkg.version !== expected) throw new Error('version_mismatch');
  const environment = { PATH: path.dirname(process.execPath), TZ: request.timezone || 'UTC' };
  if (request.token) environment.CLARITY_API_TOKEN = request.token;
  transport = new StdioClientTransport({
    command: process.execPath,
    args: [path.join(root, 'node_modules/@microsoft/clarity-mcp-server/dist/index.js')],
    env: environment,
    stderr: 'pipe',
  });
  client = new Client({ name: 'seo-workbench-clarity', version: '1.0.0' });
  let stderrBytes = 0;
  let httpStatus = null;
  // Never forward provider logs. Only extract an HTTP status, if actually present.
  function attachStderr() {
    transport.stderr?.on('data', chunk => {
      stderrBytes += chunk.length;
      const match = String(chunk).match(/status:.*\s(400|401|403|429|5\d\d)\b/);
      if (match) httpStatus = Number(match[1]);
      if (stderrBytes > 65536) void close();
    });
  }
  timer = setTimeout(() => { void close().finally(() => process.exit(2)); }, 55000);
  await client.connect(transport);
  attachStderr();
  if (client.getServerVersion()?.version !== expected) throw new Error('version_mismatch');
  const discovered = await client.listTools();
  for (const name of tools) {
    const tool = discovered.tools.find(item => item.name === name);
    if (!tool || tool.inputSchema?.type !== 'object') throw new Error('schema_mismatch');
    const required = name === 'list-session-recordings' ? ['filters', 'count', 'sortBy'] : ['query'];
    if (!required.every(key => key in (tool.inputSchema.properties || {}))) throw new Error('schema_mismatch');
  }
  const result = request.tool === 'discover'
    ? { tools: discovered.tools, server_version: expected }
    : await client.callTool({ name: request.tool, arguments: request.arguments || {} });
  const output = JSON.stringify({ ok: true, result, http_status: httpStatus, server_version: expected });
  if (Buffer.byteLength(output) > 8 * 1024 * 1024) throw new Error('response_too_large');
  process.stdout.write(output + '\n');
}

try { await main(); }
catch (error) {
  const known = ['invalid_request', 'version_mismatch', 'schema_mismatch', 'response_too_large'];
  process.stdout.write(JSON.stringify({ ok: false, reason_code: known.includes(error.message) ? error.message : 'mcp_error' }) + '\n');
  process.exitCode = 1;
} finally { await close(); }
