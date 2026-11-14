#!/bin/bash
# 把客户版同步到 Cloudflare Pages（国内可达的备用地址）
# Token 存在 /home/user/.cf-token（权限 600，不进仓库）
# 手动执行：bash push_cloudflare.sh
set -u
SRC="/home/user/Doubao/chats/36344898080638210/ai-stats"
DEPLOY="/tmp/pages-aistats"
ACCOUNT="db28f8e7b0551554aebbb08ec0d64b7b"
PROJECT="aistats"
LOG="/tmp/draw_refresh.log"

TOKEN=$(cat /home/user/.cf-token 2>/dev/null | tr -d '\n')
if [ -z "$TOKEN" ]; then
  echo "$(date '+%F %T') Cloudflare 跳过：未找到 token" >> "$LOG"
  exit 0
fi

mkdir -p "$DEPLOY"
cd "$SRC" || exit 1
for f in app.html manifest.json icon-512.png apple-touch-icon.png draw-latest.json stats.html forum-picks.html; do
  [ -f "$f" ] && cp -f "$f" "$DEPLOY/"
done

export CLOUDFLARE_API_TOKEN="$TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT"
export WRANGLER_SEND_METRICS=false

if OUT=$(cd "$DEPLOY" && timeout 180 npx --yes wrangler@3.114.0 pages deploy "$DEPLOY" --project-name="$PROJECT" --branch=main --commit-dirty=true 2>&1); then
  echo "$(date '+%F %T') Cloudflare 已同步 $(python3 -c 'import json;d=json.load(open("draw-latest.json"));print(d.get("macao",{}).get("draw"))' 2>/dev/null) 期" >> "$LOG"
else
  echo "$(date '+%F %T') Cloudflare 同步失败: $(echo "$OUT" | tail -3 | tr '\n' ' ')" >> "$LOG"
  exit 1
fi
