#!/bin/bash
# 每次改版后运行：把当前 app-pro.html 存一份到 versions/
# 用法：bash versions/snapshot.sh v58.59-Pro "本次改动说明"
set -e
cd "$(dirname "$0")/.."
VER="$1"; DESC="$2"
if [ -z "$VER" ]; then echo "用法: bash versions/snapshot.sh v58.59-Pro 说明"; exit 1; fi
DEST="versions/app-pro-$VER.html"
python3 - "$DEST" "$VER" "$DESC" << 'PY'
import sys, pathlib, re
dest, ver, desc = sys.argv[1], sys.argv[2], sys.argv[3]
s = pathlib.Path('app-pro.html').read_text()
if '历史版本' not in s:
    s = s.replace('<body>', '<body>\n<div style="background:#333;color:#fff;font-size:12px;text-align:center;padding:4px 8px;letter-spacing:1px">历史版本 %s · %s</div>' % (ver, desc), 1)
m = re.search(r"// 版本锁定：[\s\S]*?\}\)\(\);", s)
if m: s = s[:m.start()] + "// 历史版本页：不参与版本锁定、不跳转\n" + s[m.end():]
lines = s.split('\n'); out=[]; i=0
while i < len(lines):
    if "fetch('version.txt?t=" in lines[i]:
        j=i
        while j < len(lines) and '.catch' not in lines[j]: j+=1
        if j < len(lines):
            out.append('void 0; // 历史版本页：不检查线上版本'); i=j+1; continue
    out.append(lines[i]); i+=1
s = '\n'.join(out)
pathlib.Path(dest).write_text(s)
print('已生成', dest)
PY
