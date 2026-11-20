#!/bin/bash
# 由最新站点快照重建 九肖 / 杀三肖 台账，有实质变化才提交推送
# 「实质变化」= 稳定序列化后内容不同（剔除 updated_at/generated_at 等时间戳、字典键序不影响）
cd "$(dirname "$0")" || exit 1

python3 build_sites_current.py || exit 1
python3 build_kill3_ledger.py || exit 1
python3 build_site_registry.py || exit 1
python3 build_site_directory.py || exit 1
python3 build_current_recommend.py || exit 1
python3 build_position_stats.py || exit 1
python3 build_kill_rank_stats.py || exit 1
python3 build_extra_ledgers.py || exit 1
python3 build_draws_recent.py || exit 1
python3 build_quality_check.py || exit 1
python3 enrich_site_names.py || exit 1

FILES="data/sites-current.json
data/kill3-ledger.json
data/max-zodiac-ledger.json
data/site-registry.json
data/site-directory.json
data/site-aliases.json
data/current-recommend.json
data/zodiac-position-stats.json
data/kill-rank-stats.json
data/pingte-ledger.json
data/wave-ledger.json
data/tail-ledger.json
data/head-ledger.json
data/size-ledger.json
data/parity-ledger.json
data/draws-recent.json
data/quality-report.json"

git add $FILES 2>/dev/null

CHANGED=$(python3 data_changed.py $FILES)
if [ -n "$CHANGED" ]; then
  echo "变化文件：$(echo $CHANGED | tr '\n' ' ')"
  git -c user.name=bot -c user.email=bot@local commit -q -m "台账自动重建：$(date '+%Y-%m-%d %H:%M')"
  if git push -q origin main; then
    echo "PUSHED $(date '+%F %T')"
  else
    echo "PUSH_FAILED $(date '+%F %T')"
    exit 1
  fi
else
  # 只有时间戳/键序抖动：仅撤掉暂存，不提交、不推送，也不动工作区文件
  # （这些文件每轮都会被脚本重写，回滚工作区在并行任务运行时有覆盖风险）
  git reset -q >/dev/null 2>&1
  echo "NO_CHANGE $(date '+%F %T')"
fi
