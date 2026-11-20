// Cloudflare Pages Function：/api/diag
// 录入失败诊断通道：POST 上报整批失败，GET 读取；数据存私有 GitHub 仓库，不经过飞书。
// 环境变量（Pages secrets）：
//   GITHUB_DIAG_TOKEN / GITHUB_DIAG_REPO / GITHUB_DIAG_BRANCH
//   DIAG_INGEST_KEY / DIAG_READ_KEY
const MAX_BODY = 256 * 1024;
const MAX_FAILURES = 200;
const MAX_BATCHES_PER_DAY = 100;
const MAX_BATCHES_PER_DEVICE = 5;
const MAX_BATCHES_PER_IP = 10;
const KEEP_DAYS = 30;

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET,POST,OPTIONS',
  'access-control-allow-headers': 'content-type,x-diag-key,x-diag-read-key',
  'access-control-max-age': '86400',
};

function out(data, status, extra) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: Object.assign({ 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }, CORS, extra || {}),
  });
}

function shDay(offset) {
  const t = new Date(Date.now() + 8 * 3600 * 1000 + (offset || 0) * 86400000);
  return t.toISOString().slice(0, 10);
}

function quotaOut(error) {
  return out({ ok: false, error: error }, 429, { 'retry-after': '86400' });
}

async function hashIp(request, env) {
  try {
    const ip = String(request.headers.get('cf-connecting-ip') || '');
    const salt = String((env && env.DIAG_IP_SALT) || '');
    if (!ip || !salt || !crypto || !crypto.subtle) return '';
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(salt + '|' + ip));
    return Array.from(new Uint8Array(buf)).slice(0, 12).map(function (b) {
      return ('0' + b.toString(16)).slice(-2);
    }).join('');
  } catch (e) { return ''; }
}

function isDay(s) { return /^\d{4}-\d{2}-\d{2}$/.test(String(s || '')); }
function isId(s) { return /^[A-Za-z0-9_-]{8,64}$/.test(String(s || '')); }
function clean(s, n) { return String(s == null ? '' : s).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').slice(0, n); }
function b64(s) { return btoa(unescape(encodeURIComponent(s))); }
function unb64(s) { return decodeURIComponent(escape(atob(String(s || '').replace(/\s/g, '')))); }

function getToken(env) { return env && env.GITHUB_DIAG_TOKEN ? String(env.GITHUB_DIAG_TOKEN) : ''; }
function getRepo(env) { return env && env.GITHUB_DIAG_REPO ? String(env.GITHUB_DIAG_REPO) : ''; }
function getBranch(env) { return env && env.GITHUB_DIAG_BRANCH ? String(env.GITHUB_DIAG_BRANCH) : 'main'; }

async function gh(env, method, path, body) {
  const token = getToken(env);
  if (!token) throw new Error('diag storage not configured');
  const url = 'https://api.github.com/repos/' + getRepo(env) + path;
  const res = await fetch(url, {
    method,
    headers: {
      authorization: 'Bearer ' + token,
      accept: 'application/vnd.github+json',
      'user-agent': 'ai-stats-diag/1.0',
      'content-type': 'application/json',
    },
    body: body == null ? undefined : JSON.stringify(body),
  });
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  return { status: res.status, data };
}

async function readDay(env, day) {
  const path = '/contents/diag/' + day + '.json?ref=' + encodeURIComponent(getBranch(env));
  const r = await gh(env, 'GET', path);
  if (r.status === 404) return { sha: null, doc: { date: day, updatedAt: '', batches: [] } };
  if (r.status !== 200 || !r.data) throw new Error('read ' + r.status);
  let doc = { date: day, updatedAt: '', batches: [] };
  try {
    doc = JSON.parse(unb64(r.data.content));
    if (!Array.isArray(doc.batches)) doc.batches = [];
  } catch (e) {
    doc = { date: day, updatedAt: '', batches: [] };
  }
  return { sha: r.data.sha, doc };
}

async function writeDay(env, day, doc, sha, message) {
  const path = '/contents/diag/' + day + '.json';
  const body = {
    message: message || ('diag ' + day),
    content: b64(JSON.stringify(doc, null, 2)),
    branch: getBranch(env),
  };
  if (sha) body.sha = sha;
  return gh(env, 'PUT', path, body);
}

function normalize(payload, ipHash) {
  const day = isDay(payload.day) ? payload.day : shDay(0);
  const batchId = isId(payload.batchId) ? payload.batchId : '';
  if (!batchId) throw new Error('batchId invalid');
  const fails = Array.isArray(payload.failures) ? payload.failures.slice(0, MAX_FAILURES) : [];
  if (!fails.length) throw new Error('failures empty');
  return {
    batchId,
    ts: new Date().toISOString(),
    appVersion: clean(payload.appVersion, 40),
    shop: clean(payload.shop, 12),
    day,
    deviceHash: clean(payload.deviceHash, 40),
    ipHash: clean(ipHash, 24),
    inputMode: clean(payload.inputMode, 40),
    totalLines: Math.max(0, Math.min(10000, Number(payload.totalLines) || 0)),
    failCount: Math.max(fails.length, Math.min(10000, Number(payload.failCount) || 0)),
    rawInput: clean(payload.rawInput, 2000),
    failures: fails.map(function (f) {
      return {
        lineNo: Math.max(0, Math.min(10000, Number(f && f.lineNo) || 0)),
        raw: clean(f && f.raw, 500),
        msg: clean(f && f.msg, 300),
      };
    }),
  };
}

export async function onRequest(context) {
  const { request, env } = context;
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

  const url = new URL(request.url);
  if (url.searchParams.get('health') === '1') {
    return out({ ok: true, service: 'ai-stats-diag', configured: !!(getToken(env) && getRepo(env)) }, 200);
  }

  try {
    if (request.method === 'POST') {
      if (!env.DIAG_INGEST_KEY || request.headers.get('x-diag-key') !== env.DIAG_INGEST_KEY) {
        return out({ ok: false, error: 'unauthorized' }, 401);
      }
      const len = Number(request.headers.get('content-length') || 0);
      if (len > MAX_BODY) return out({ ok: false, error: 'too large' }, 413);
      const text = await request.text();
      if (text.length > MAX_BODY) return out({ ok: false, error: 'too large' }, 413);
      let payload;
      try { payload = JSON.parse(text); } catch (e) { return out({ ok: false, error: 'bad json' }, 400); }
      const rec = normalize(payload, await hashIp(request, env));

      for (let attempt = 0; attempt < 3; attempt++) {
        const cur = await readDay(env, rec.day);
        if (cur.doc.batches.some(function (x) { return x && x.batchId === rec.batchId; })) {
          return out({ ok: true, duplicate: true, day: rec.day, batchId: rec.batchId }, 200);
        }
        if (cur.doc.batches.length >= MAX_BATCHES_PER_DAY) {
          return quotaOut('day quota reached');
        }
        if (rec.deviceHash) {
          const devCount = cur.doc.batches.filter(function (x) { return x && x.deviceHash === rec.deviceHash; }).length;
          if (devCount >= MAX_BATCHES_PER_DEVICE) return quotaOut('device quota reached');
        }
        if (rec.ipHash) {
          const ipCount = cur.doc.batches.filter(function (x) { return x && x.ipHash === rec.ipHash; }).length;
          if (ipCount >= MAX_BATCHES_PER_IP) return quotaOut('ip quota reached');
        }
        cur.doc.date = rec.day;
        cur.doc.updatedAt = new Date().toISOString();
        cur.doc.batches.push(rec);
        const w = await writeDay(env, rec.day, cur.doc, cur.sha, 'diag: ' + rec.batchId);
        if (w.status === 200 || w.status === 201) {
          return out({ ok: true, day: rec.day, batchId: rec.batchId, stored: rec.failures.length }, 200);
        }
        if (w.status === 409) continue; // 并发写冲突，重读再试
        return out({ ok: false, error: 'storage ' + w.status }, 502);
      }
      return out({ ok: false, error: 'busy, retry later' }, 409);
    }

    if (request.method === 'GET') {
      if (!env.DIAG_READ_KEY || request.headers.get('x-diag-read-key') !== env.DIAG_READ_KEY) {
        return out({ ok: false, error: 'unauthorized' }, 401);
      }
      if (url.searchParams.get('list') === '1') {
        const r = await gh(env, 'GET', '/contents/diag?ref=' + encodeURIComponent(getBranch(env)));
        if (r.status === 404) return out({ ok: true, dates: [] }, 200);
        if (r.status !== 200 || !Array.isArray(r.data)) return out({ ok: false, error: 'storage ' + r.status }, 502);
        const dates = r.data.filter(function (x) { return x && /^\d{4}-\d{2}-\d{2}\.json$/.test(x.name); })
          .map(function (x) { return x.name.replace(/\.json$/, ''); }).sort().reverse().slice(0, KEEP_DAYS);
        return out({ ok: true, dates }, 200);
      }
      const day = isDay(url.searchParams.get('date')) ? url.searchParams.get('date') : shDay(0);
      const cur = await readDay(env, day);
      const limit = Math.max(1, Math.min(100, Number(url.searchParams.get('limit')) || 30));
      return out({
        ok: true,
        date: day,
        updatedAt: cur.doc.updatedAt || '',
        total: cur.doc.batches.length,
        batches: cur.doc.batches.slice(-limit).reverse(),
      }, 200);
    }

    return out({ ok: false, error: 'method not allowed' }, 405);
  } catch (e) {
    return out({ ok: false, error: String((e && e.message) || e).slice(0, 120) }, 500);
  }
}
