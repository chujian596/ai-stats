// Cloudflare Pages Function：/api/recent-draws?limit=30
// 读同站静态 official-history.json，按期号倒序返回最近 N 期，字段与录单页一致。
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const limit = Math.min(60, Math.max(1, parseInt(url.searchParams.get('limit') || '30', 10) || 30));
  const headers = {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': '*',
    'cache-control': 'public, max-age=300',
  };
  try {
    const r = await fetch(new URL('/official-history.json', url.origin).toString(), {
      headers: { Accept: 'application/json' },
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!r.ok) return new Response(JSON.stringify({ error: 'history ' + r.status }), { status: 502, headers });
    const raw = await r.json();
    const keys = Object.keys(raw || {}).filter((k) => /^\d+$/.test(k)).map(Number).sort((a, b) => b - a).slice(0, limit);
    const periods = keys.map((p) => {
      const v = raw[String(p)] || {};
      const all = Array.isArray(v.all) ? v.all.map(Number) : [];
      if (all.length < 7) return null;
      return {
        period: p,
        regularNums: all.slice(0, 6),
        specialNum: v.specialNum !== undefined ? Number(v.specialNum) : all[6],
        specialZod: v.specialZod || '',
      };
    }).filter(Boolean);
    return new Response(JSON.stringify({ updated: new Date().toISOString(), count: periods.length, periods }), { status: 200, headers });
  } catch (e) {
    return new Response(JSON.stringify({ error: String((e && e.message) || e) }), { status: 502, headers });
  }
}
