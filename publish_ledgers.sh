#!/bin/bash
# 由最新站点快照重建 九肖 / 杀三肖 台账，有变化则提交推送
cd "$(dirname "$0")" || exit 1
python3 build_sites_current.py || exit 1
python3 build_kill3_ledger.py || exit 1
python3 build_site_registry.py || exit 1
python3 build_current_recommend.py || exit 1
python3 build_position_stats.py || exit 1
python3 build_kill_rank_stats.py || exit 1
python3 build_extra_ledgers.py || exit 1
python3 build_quality_check.py || exit 1
git add data/sites-current.json data/kill3-ledger.json data/max-zodiac-ledger.json data/site-registry.json data/current-recommend.json data/zodiac-position-stats.json data/kill-rank-stats.json data/pingte-ledger.json data/wave-ledger.json data/tail-ledger.json data/head-ledger.json data/quality-report.json 2>/dev/null
if ! git diff --cached --quiet; then
  git -c user.name=bot -c user.email=bot@local commit -q -m "台账自动重建：$(date '+%Y-%m-%d %H:%M')"
  git push -q origin main && echo "PUSHED $(date '+%F %T')"
else
  echo "NO_CHANGE $(date '+%F %T')"
fi
