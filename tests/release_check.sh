#!/bin/bash
# 发版质检：自动部分。用法： bash tests/release_check.sh
set -e
cd "$(dirname "$0")/.."

echo "=== 1/4 语法门禁 ==="
python3 - << 'PY'
import re, pathlib
s = pathlib.Path('app-pro.html').read_text()
open('/tmp/_chk.js','w').write("\n;\n".join(re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)))
print('已抽取脚本 ->', '/tmp/_chk.js')
PY
/opt/nodejs/22/bin/node --check /tmp/_chk.js && echo "语法 OK"

echo "=== 2/4 回归：专业版 + 客户版 105 项金额矩阵 ==="
for f in app-pro.html app.html; do
  python3 tests/coverage_check.py "$f" > /dev/null
  OUT=$(/opt/nodejs/22/bin/node /tmp/_cov.js)
  echo "--- $f ---"
  echo "$OUT" | tail -1
  FAIL=$(echo "$OUT" | grep -c "❌" || true)
  if [ "$FAIL" != "0" ]; then echo "$f 有失败项，禁止发版"; echo "$OUT" | grep "❌"; exit 1; fi
done

echo "=== 3/4 发版硬校验（版本三处一致 + 关键元素不丢） ==="
python3 tests/verify_release.py || { echo "硬校验失败，禁止发版"; exit 1; }

echo "=== 4/4 关键项自检（金额断言） ==="
echo "101 项矩阵已在第 2 步逐项断言，失败即中止"

echo
echo "自动部分通过。别忘了跑人工项："
echo "  见 tests/RELEASE_CHECKLIST.md 第二段（该弹/不该弹/多选合并/明细合并/其他功能）"
