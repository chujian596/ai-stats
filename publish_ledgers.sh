#!/bin/bash
# 由最新站点快照重建 九肖 / 杀三肖 台账，有实质变化才提交推送
# 「实质变化」= 稳定序列化后内容不同（剔除 updated_at/generated_at 等时间戳、字典键序不影响）
cd "$(dirname "$0")" || exit 1

python3 build_sites_current.py || exit 1
python3 build_kill3_ledger.py || exit 1
python3 build_site_registry.py || exit 1
python3 build_site_directory.py || exit 1
python3 build_current_recommend.py || exit 1
# 站方核心杀口径（可选；没有快照/校准文件时跳过，不影响主台账）
python3 tools/build_core_view.py >/dev/null 2>&1 && echo "CORE_OK" || echo "CORE_SKIP"
python3 build_position_stats.py || exit 1
python3 build_kill_rank_stats.py || exit 1
python3 build_extra_ledgers.py || exit 1
# 全维度改料跟踪台账（父目录 change_ledger.py；去重追加 + 开奖后补结算，不回填历史）
python3 ../change_ledger.py || exit 1
python3 build_draws_recent.py || exit 1
python3 build_quality_check.py || exit 1
python3 enrich_site_names.py || exit 1
# 来源名单（站点 81 + 论坛池；保留人工改名/启停/主池标记）
python3 tools/build_source_registry.py >/dev/null 2>&1 && echo "SOURCES_OK" || echo "SOURCES_SKIP"
# 316 后站点成绩（只统计有快照的台账）
python3 tools/build_site_performance.py >/dev/null 2>&1 && echo "PERF_OK" || echo "PERF_SKIP"
# 研判引擎：316 后拥挤度审计（只做统计分级，不生成方向）
python3 tools/build_engine.py >/dev/null 2>&1 && echo "ENGINE_OK" || echo "ENGINE_SKIP"
# 独立模板审计与权重影子账：18:00-21:29 冻结，开奖后补分
python3 tools/build_independence.py >/dev/null 2>&1 && echo "INDEPENDENCE_OK" || echo "INDEPENDENCE_SKIP"
python3 tools/weight_shadow.py update >/dev/null 2>&1 && echo "WEIGHT_OK" || echo "WEIGHT_SKIP"
# 群众走向验证：18:00-21:29 开奖前冻结；开奖后（22:30链）打分
HH=$(date +%H); MM=$(date +%M)
if { [ "$HH" -ge 18 ] && [ "$HH" -lt 21 ]; } || { [ "$HH" -eq 21 ] && [ "$MM" -lt 30 ]; }; then
  python3 tools/crowd_validation.py freeze
else
  echo "CROWD_FREEZE_SKIP $(date '+%H:%M')"
fi
python3 tools/crowd_validation.py score

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
data/quality-report.json
data/source-registry.json
data/site-performance.json
data/engine.json
data/independence.json
data/independence-summary.json
data/weight-shadow.json
data/weight-validation.json
$(ls data/weight-preview-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/weight-freeze-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/weight-score-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/engine-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/core-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/crowd-freeze-*.json 2>/dev/null | tr '\n' ' ')
$(ls data/crowd-score-*.json 2>/dev/null | tr '\n' ' ')
data/crowd-validation.json"

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
