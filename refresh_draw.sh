#!/bin/bash
# 每 30 分钟刷新开奖快照并推送（由 crontab 调用）
set -u
REPO="/home/user/Doubao/chats/36344898080638210/ai-stats"
LOG="/tmp/draw_refresh.log"

cd "$REPO" || { echo "$(date '+%F %T') 找不到仓库" >> "$LOG"; exit 1; }

python3 fetch_draw.py >> "$LOG" 2>&1 || { echo "$(date '+%F %T') 抓取失败" >> "$LOG"; exit 1; }

git add draw-latest.json
if git diff --staged --quiet; then
  echo "$(date '+%F %T') 号码未变化，跳过提交" >> "$LOG"
  exit 0
fi

git commit -q -m "chore: 更新开奖快照 $(date -u '+%F %H:%M UTC')"
if git push -q origin main 2>>"$LOG"; then
  echo "$(date '+%F %T') 已推送 $(python3 -c 'import json;d=json.load(open("draw-latest.json"));print(d.get("macao",{}).get("draw"))') 期" >> "$LOG"
else
  echo "$(date '+%F %T') 推送失败" >> "$LOG"
fi
