/* 离线缓存：有网时强制取最新（绕过浏览器强缓存），没网时用上一次缓存，保证断网也能打开 */
var CACHE_NAME = 'aistats-shell-v3';
var SHELL = ['/app', '/app.html', '/app-pro', '/app-pro.html', '/manifest.json', '/icon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function (c) {
      // 逐个缓存，某个地址 404 不影响其它
      return Promise.all(SHELL.map(function (u) {
        return c.add(new Request(u, { cache: 'reload' })).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); }).catch(function () {})
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE_NAME && k.indexOf('aistats-') === 0; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    fetch(req, { cache: 'reload' }).then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE_NAME).then(function (c) { c.put(req, copy); }).catch(function () {});
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        // 导航请求兜底回到主页面
        if (req.mode === 'navigate') return caches.match('/app').then(function (p) {
          return p || caches.match('/app.html');
        });
        return new Response('', { status: 504, statusText: 'offline' });
      });
    })
  );
});
