#!/bin/bash
# 开奖快照刷新（crontab：21:33 起 sleep 30 秒 → 21:33:30 开抓）
# 只在开奖号码真正变化时才 commit/push，避免每次刷新都触发整站重建
set -u
REPO="$(cd "$(dirname "$0")" && pwd)"
LOG="/tmp/draw_refresh.log"

cd "$REPO" || { echo "$(date '+%F %T') 找不到仓库" >> "$LOG"; exit 1; }

KEY() { python3 -c "import json;d=json.load(open('draw-latest.json'));m=d.get('macao',{});h=d.get('hongkong',{});print(m.get('draw'),m.get('numbers'),h.get('draw'),h.get('numbers'))" 2>/dev/null; }

BEFORE=$(KEY)

python3 fetch_draw.py >> "$LOG" 2>&1 || { echo "$(date '+%F %T') 抓取失败" >> "$LOG"; exit 1; }

AFTER=$(KEY)

if [ "$BEFORE" = "$AFTER" ]; then
  git checkout -- draw-latest.json 2>/dev/null
  echo "$(date '+%F %T') 号码未变化，跳过推送" >> "$LOG"
  exit 0
fi

git add draw-latest.json
if git diff --staged --quiet; then
  echo "$(date '+%F %T') 无暂存变化，跳过" >> "$LOG"
  exit 0
fi

git commit -q -m "chore: 更新开奖快照 $(date -u '+%F %H:%M UTC')"
if git push -q origin main 2>>"$LOG"; then
  echo "$(date '+%F %T') 已推送 $(python3 -c 'import json;d=json.load(open("draw-latest.json"));print(d.get("macao",{}).get("draw"))') 期" >> "$LOG"
else
  echo "$(date '+%F %T') 推送失败" >> "$LOG"
fi

# 同步到备用地址 chujian596/ai-luandan（云端 CI 里跳过，本地才推）
if [ -z "${CI:-}" ]; then
  bash "$REPO/push_client_mirror.sh"
fi

# 同步到 Cloudflare Pages 备用入口
bash "$REPO/push_cloudflare.sh"
