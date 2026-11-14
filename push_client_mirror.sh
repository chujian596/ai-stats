#!/bin/bash
# 把客户版镜像同步到备用仓库 chujian596/ai-luandan
# 由 refresh_draw.sh 在快照更新后调用，也可手动执行：bash push_client_mirror.sh
set -u
SRC="/home/user/Doubao/chats/36344898080638210/ai-stats"
MIRROR="/home/user/.mirror-luandan"
LOG="/tmp/draw_refresh.log"
TOKEN=$(git -C "$SRC" remote get-url origin | sed -E 's|https://([^:]*):([^@]*)@.*|\2|')

cd "$SRC" || exit 1

if [ ! -d "$MIRROR/.git" ]; then
  git clone -q "https://chujian596:$TOKEN@github.com/chujian596/ai-luandan.git" "$MIRROR" 2>>"$LOG" || {
    echo "$(date '+%F %T') 备用仓库克隆失败" >> "$LOG"; exit 1; }
fi

cp app.html "$MIRROR/app.html"
cp manifest.json "$MIRROR/manifest.json" 2>/dev/null
cp icon-512.png "$MIRROR/icon-512.png" 2>/dev/null
cp icon-512.png "$MIRROR/apple-touch-icon.png" 2>/dev/null
cp draw-latest.json "$MIRROR/draw-latest.json"

git -C "$MIRROR" add -A
if git -C "$MIRROR" diff --staged --quiet; then
  echo "$(date '+%F %T') 备用镜像无变化" >> "$LOG"
  exit 0
fi

git -C "$MIRROR" -c user.email="bot@local" -c user.name="ai-stats-bot" commit -q -m "sync: 客户版镜像 $(date '+%F %H:%M')"
if git -C "$MIRROR" push -q origin main 2>>"$LOG"; then
  echo "$(date '+%F %T') 备用镜像已同步 https://chujian596.github.io/ai-luandan/app.html" >> "$LOG"
else
  echo "$(date '+%F %T') 备用镜像推送失败" >> "$LOG"
fi
