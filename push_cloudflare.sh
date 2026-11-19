#!/bin/bash
# 把客户版同步到 Cloudflare Pages（国内可达的备用地址）
# Token 存在 /home/user/.cf-token（权限 600，不进仓库）
# 手动执行：bash push_cloudflare.sh
set -u
SRC="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="/tmp/pages-aistats"
ACCOUNT="db28f8e7b0551554aebbb08ec0d64b7b"
PROJECT="aistats"
LOG="/tmp/draw_refresh.log"

TOKEN=$(cat /home/user/.cf-token 2>/dev/null | tr -d '\n')
[ -z "$TOKEN" ] && TOKEN="${CF_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "$(date '+%F %T') Cloudflare 跳过：未找到 token" >> "$LOG"
  exit 0
fi

# ===== 版本一致性闸门：页面 APP_VER 与 version.txt 必须一致，否则不部署 =====
VER_PAGE=$(grep -o "v[0-9]+\.v[0-9]+-Pro" /dev/null 2>/dev/null)
VER_PAGE=$(grep -oE "v[0-9]+\.[0-9]+(\.[0-9]+)?-Pro" app-pro.html 2>/dev/null | head -1)
VER_TXT=$(cat version.txt 2>/dev/null | tr -d '\n\r ')
if [ -n "$VER_PAGE" ] && [ "$VER_PAGE" != "$VER_TXT" ]; then
  echo "版本不一致：app-pro.html=$VER_PAGE  version.txt=$VER_TXT  已中止部署" >&2
  echo "修正：printf '%s' '$VER_PAGE' > version.txt" >&2
  exit 2
fi

# 客户版同样过闸门，避免页面版本低于 version-client.txt 造成回退提示
VER_CLIENT_PAGE=$(grep -oE "var APP_VER = 'v[0-9]+\.[0-9]+'" app.html 2>/dev/null | grep -oE "v[0-9]+\.[0-9]+" | head -1)
VER_CLIENT_TXT=$(cat version-client.txt 2>/dev/null | tr -d '\n\r ')
if [ -n "$VER_CLIENT_PAGE" ] && [ "$VER_CLIENT_PAGE" != "$VER_CLIENT_TXT" ]; then
  echo "客户版版本不一致：app.html=$VER_CLIENT_PAGE  version-client.txt=$VER_CLIENT_TXT  已中止部署" >&2
  echo "修正：printf '%s' '$VER_CLIENT_PAGE' > version-client.txt" >&2
  exit 2
fi

mkdir -p "$DEPLOY"
cd "$SRC" || exit 1
cp -f admin.html admin58.html
for f in index.html app.html app-pro.html admin.html admin58.html portal.html manifest.json sw.js icon-512.png apple-touch-icon.png draw-latest.json stats.html forum-picks.html members.json whitelist.json version.txt version-client.txt system-guide.html 0491.html ai-analysis.html shengxiao.html update-tool.html zhengpiao.html ziliao.html apps.html lab.html issues.html manage.html; do
  [ -f "$f" ] && cp -f "$f" "$DEPLOY/"
done

# 0491 数据（data/ 子目录）；img-snap 是本地读图快照，7MB 不上公网
if [ -d "$SRC/data" ]; then
  mkdir -p "$DEPLOY/data"
  (cd "$SRC/data" && find . -maxdepth 1 -mindepth 1 ! -name 'img-snap' -exec cp -rf {} "$DEPLOY/data/" \;)
fi

# Pages Functions（/api/draw 让 Cloudflare 自己抓开奖）
rm -rf "$DEPLOY/versions"
[ -d "$SRC/versions" ] && cp -rf "$SRC/versions" "$DEPLOY/"

rm -rf "$DEPLOY/functions"
[ -d "$SRC/functions" ] && cp -rf "$SRC/functions" "$DEPLOY/"

export CLOUDFLARE_API_TOKEN="$TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT"
export WRANGLER_SEND_METRICS=false

if OUT=$(cd "$DEPLOY" && timeout 180 npx --yes wrangler@3.114.0 pages deploy "$DEPLOY" --project-name="$PROJECT" --branch=main --commit-dirty=true 2>&1); then
  echo "$(date '+%F %T') Cloudflare 已同步 $(python3 -c 'import json;d=json.load(open("draw-latest.json"));print(d.get("macao",{}).get("draw"))' 2>/dev/null) 期" >> "$LOG"
else
  echo "$(date '+%F %T') Cloudflare 同步失败: $(echo "$OUT" | tail -3 | tr '\n' ' ')" >> "$LOG"
  exit 1
fi

# ===== 同步 GitHub Pages =====
# APK 的 HOME_URL 指向 chujian596.github.io/ai-stats/app-pro.html，
# 只推 Cloudflare 的话，安卓端一直看到旧代码。这里补上同步。
if git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1; then
  cd "$SRC" || exit 1
  if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A >/dev/null 2>&1
    git commit -q -m "sync: $(date '+%F %T') 推送同步" >/dev/null 2>&1
  fi
  if git push -q origin HEAD 2>>"$LOG"; then
    echo "$(date '+%F %T') GitHub Pages 已同步" >> "$LOG"
  else
    echo "$(date '+%F %T') GitHub Pages 同步失败" >> "$LOG"
  fi
fi
