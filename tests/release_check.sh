#!/bin/bash
# 发版质检：自动部分。用法： bash tests/release_check.sh
set -e
cd "$(dirname "$0")/.."

echo "=== 1/3 语法门禁 ==="
python3 - << 'PY'
import re, pathlib
s = pathlib.Path('app-pro.html').read_text()
open('/tmp/_chk.js','w').write("\n;\n".join(re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)))
print('已抽取脚本 ->', '/tmp/_chk.js')
PY
/opt/nodejs/22/bin/node --check /tmp/_chk.js && echo "语法 OK"

echo "=== 2/3 回归 38 项 ==="
python3 tests/coverage_check.py app-pro.html > /dev/null
/opt/nodejs/22/bin/node /tmp/_cov.js | tail -1

echo "=== 3/3 关键项自检（金额断言） ==="
FAIL=$(/opt/nodejs/22/bin/node /tmp/_cov.js | grep -c "❌" || true)
if [ "$FAIL" != "0" ]; then echo "有失败项，禁止发版"; exit 1; fi

echo
echo "自动部分通过。别忘了跑人工项："
echo "  见 tests/RELEASE_CHECKLIST.md 第二段（该弹/不该弹/多选合并/明细合并/其他功能）"
