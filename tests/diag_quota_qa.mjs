// 诊断接口配额回归：用内存模拟 GitHub Contents API，验证设备/IP 上限、去重和 Retry-After。
import assert from 'node:assert/strict';

const docs = new Map();
const calls = [];

function keyOf(url) {
  const u = new URL(url);
  return u.pathname.replace('/repos/x/y/contents/', '');
}

globalThis.fetch = async function (url, opts) {
  const method = (opts && opts.method) || 'GET';
  const key = keyOf(url);
  calls.push(method + ' ' + key);
  if (method === 'GET') {
    const doc = docs.get(key);
    if (!doc) return new Response(JSON.stringify({ message: 'Not Found' }), { status: 404 });
    return new Response(JSON.stringify({
      sha: 'sha-' + key,
      content: Buffer.from(JSON.stringify(doc)).toString('base64'),
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  }
  if (method === 'PUT') {
    const body = JSON.parse(opts.body);
    docs.set(key, JSON.parse(Buffer.from(body.content, 'base64').toString('utf8')));
    return new Response(JSON.stringify({ content: { sha: 'sha-' + key } }), { status: 200 });
  }
  return new Response('{}', { status: 500 });
};

const mod = await import('../functions/api/diag.js');
const env = {
  DIAG_INGEST_KEY: 'ingest-key',
  DIAG_READ_KEY: 'read-key',
  GITHUB_DIAG_TOKEN: 'token',
  GITHUB_DIAG_REPO: 'x/y',
  GITHUB_DIAG_BRANCH: 'main',
  DIAG_IP_SALT: 'salt',
};

function req(batchId, deviceHash, ip) {
  return new Request('https://example.test/api/diag', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-diag-key': 'ingest-key',
      'cf-connecting-ip': ip,
    },
    body: JSON.stringify({
      batchId,
      day: '2026-11-20',
      appVersion: 'v59.63-Pro',
      deviceHash,
      failures: [{ lineNo: 1, raw: '特0X 100', msg: '无法识别' }],
    }),
  });
}

async function post(batchId, deviceHash, ip) {
  const res = await mod.onRequest({ request: req(batchId, deviceHash, ip), env });
  return { status: res.status, body: await res.json(), retry: res.headers.get('retry-after') };
}

const results = [];
let r = await post('batch-0001', 'dev-a', '1.1.1.1');
results.push(['首批发', r]);
assert.equal(r.status, 200);

r = await post('batch-0002', 'dev-a', '1.1.1.1');
r = await post('batch-0003', 'dev-a', '1.1.1.1');
r = await post('batch-0004', 'dev-a', '1.1.1.1');
r = await post('batch-0005', 'dev-a', '1.1.1.1');
results.push(['同设备第5批', r]);
assert.equal(r.status, 200);

r = await post('batch-0006', 'dev-a', '1.1.1.1');
results.push(['同设备第6批', r]);
assert.equal(r.status, 429);
assert.equal(r.body.error, 'device quota reached');
assert.equal(r.retry, '86400');

// 换设备、同 IP：前 5 批已占同 IP 名额；再发 5 批到 10，第 11 批应被 IP 上限拒绝。
for (let i = 0; i < 5; i++) {
  r = await post('batch-b00' + i, 'dev-b' + i, '1.1.1.1');
  assert.equal(r.status, 200, 'ip fill ' + i);
}
r = await post('batch-b010', 'dev-b10', '1.1.1.1');
results.push(['同 IP 第11批', r]);
assert.equal(r.status, 429);
assert.equal(r.body.error, 'ip quota reached');
assert.equal(r.retry, '86400');

// 同 batchId 再传：应返回 duplicate，不占额度。
const before = docs.get('diag/2026-11-20.json').batches.length;
r = await post('batch-0001', 'dev-c', '2.2.2.2');
results.push(['重复批次', r]);
assert.equal(r.status, 200);
assert.equal(r.body.duplicate, true);
assert.equal(docs.get('diag/2026-11-20.json').batches.length, before);

// 不同 IP / 不同设备仍可写入（全局未满）。
r = await post('batch-c001', 'dev-c', '2.2.2.2');
results.push(['换 IP 换设备', r]);
assert.equal(r.status, 200);

console.log(JSON.stringify({
  pass: results.length,
  total: results.length,
  fail: 0,
  checks: results.map(function (x) { return { name: x[0], status: x[1].status, error: x[1].body.error || '' }; }),
}, null, 2));
