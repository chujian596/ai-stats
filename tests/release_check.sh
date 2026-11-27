#!/bin/bash
# 发版质检：自动部分。用法： bash tests/release_check.sh
set -e
cd "$(dirname "$0")/.."

echo "=== 1/5 语法门禁 ==="
python3 - << 'PY'
import re, pathlib
s = pathlib.Path('app-pro.html').read_text()
open('/tmp/_chk.js','w').write("\n;\n".join(re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)))
print('已抽取脚本 ->', '/tmp/_chk.js')
PY
/opt/nodejs/22/bin/node --check /tmp/_chk.js && echo "语法 OK"

echo "=== 2/5 回归：专业版 + 客户版 107 项金额矩阵 ==="
for f in app-pro.html app.html; do
  python3 tests/coverage_check.py "$f" > /dev/null
  OUT=$(/opt/nodejs/22/bin/node /tmp/_cov.js)
  echo "--- $f ---"
  echo "$OUT" | tail -1
  FAIL=$(echo "$OUT" | grep -c "❌" || true)
  if [ "$FAIL" != "0" ]; then echo "$f 有失败项，禁止发版"; echo "$OUT" | grep "❌"; exit 1; fi
done

echo "=== 3/5 发版硬校验（版本三处一致 + 关键元素不丢） ==="
python3 tests/verify_release.py || { echo "硬校验失败，禁止发版"; exit 1; }

echo "=== 4/5 关键项自检（金额断言） ==="
echo "107 项矩阵已在第 2 步逐项断言，失败即中止"
python3 tests/client_three_book_qa.py || { echo "客户版三层账自检失败，禁止发版"; exit 1; }

echo "=== 5/5 浏览器端到端（QA 116 + 词库 154 + 混搭 4 + 选择对账 55 + 录入金额 38） ==="
python3 tests/browser_gate.py || { echo "浏览器门禁失败，禁止发版"; exit 1; }

echo
echo "自动部分通过。别忘了跑人工项："
echo "  见 tests/RELEASE_CHECKLIST.md 第二段（该弹/不该弹/多选合并/明细合并/其他功能）
  混搭命中/赔付：浏览器执行 tests/settle_mixed.js，要求 4/4 PASS"
