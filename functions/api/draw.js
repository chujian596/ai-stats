// Cloudflare Pages Function：/api/draw
// 让 pages.dev 自己抓开奖，不依赖本地电脑、不依赖 GitHub、不依赖定时任务。
// 每次请求实时抓源，边缘缓存 60 秒，避免打爆源站。

const API =
  'https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044/api/v1/about/home-cache';

function shDay(offsetDays) {
  const t = new Date(Date.now() + 8 * 3600 * 1000 + (offsetDays || 0) * 86400000);
  return t.toISOString().slice(0, 10);
}

function build(raw) {
  const latest = (raw && raw.latest) || {};
  const out = {
    updated: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    source: 'home-cache',
    today: shDay(0),
  };
  for (const key of ['macao', 'hongkong']) {
    const item = latest[key];
    if (item && item.winner_numbers && item.winner_numbers.length) {
      const day = String(item.drawn_at || '').slice(0, 10);
      out[key] = {
        draw: item.draw,
        year: item.year,
        numbers: item.winner_numbers,
        drawn_at: item.drawn_at,
        day,
        stale: !!day && day !== out.today, // 源头卡住：给的还是往日数据
      };
    }
  }
  const nxt = (raw && raw.next) || {};
  out.next = {};
  for (const key of ['macao', 'hongkong']) {
    if (nxt[key]) {
      out.next[key] = { draw: nxt[key].draw, draw_at: nxt[key].draw_at };
    }
  }
  return out;
}

export async function onRequest(context) {
  const headers = {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': '*',
    'cache-control': 'public, max-age=60',
  };

  try {
    const upstream = await fetch(API, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; ai-stats/1.0)',
        Accept: 'application/json',
      },
      cf: { cacheTtl: 30, cacheEverything: true },
    });

    if (!upstream.ok) {
      return new Response(
        JSON.stringify({ error: 'upstream ' + upstream.status }),
        { status: 502, headers }
      );
    }

    const raw = await upstream.json();
    const data = build(raw);

    if (!data.macao && !data.hongkong) {
      return new Response(
        JSON.stringify({ error: 'no numbers' }),
        { status: 502, headers }
      );
    }

    return new Response(JSON.stringify(data), { status: 200, headers });
  } catch (e) {
    return new Response(
      JSON.stringify({ error: String(e && e.message ? e.message : e) }),
      { status: 502, headers }
    );
  }
}
