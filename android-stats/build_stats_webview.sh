#!/bin/bash
# 打包在线 WebView 版 APK（指向自定义域主入口）
set -e
export JAVA_HOME=/home/user/jdk/jdk-11.0.33+10
export PATH=$JAVA_HOME/bin:$PATH

SDK=/home/user/android-sdk
BT=$SDK/build-tools/34.0.0
AJ=$SDK/platforms/android-34/android.jar
PASS=aistats2026app

cd "$(dirname "$0")"
# 签名必须用脚本自己目录里的这份 keystore（手机已装版本同签名，才能覆盖升级不丢数据）
KS="$(pwd)/keystore.jks"

# 可用环境变量打不同版本：
#   APP_HOME_URL   起始地址（客户版 /app，管理版 /app-pro）
#   APP_VER_NAME   显示版本号（如 58.74 / 58.74-Pro）
#   APP_VER_CODE   版本代码
#   APK_OUT        输出文件名
HOME_URL="${APP_HOME_URL:-https://www.chujian596.dpdns.org/dashboard.html}"
VER_NAME="${APP_VER_NAME:-1.1}"
VER_CODE="${APP_VER_CODE:-2}"
OUT="${APK_OUT:-ai-stats-dashboard-v1.1.apk}"

MAIN=src/io/github/chujian596/aistats/MainActivity.java
cp "$MAIN" /tmp/_MainActivity_orig.java
cp AndroidManifest.xml /tmp/_AndroidManifest_orig.xml
trap 'cp /tmp/_MainActivity_orig.java "$MAIN"; cp /tmp/_AndroidManifest_orig.xml AndroidManifest.xml' EXIT

sed -i "s|HOME_URL = \"[^\"]*\"|HOME_URL = \"$HOME_URL\"|" "$MAIN"
sed -i "s|android:versionCode=\"[0-9]*\"|android:versionCode=\"$VER_CODE\"|" AndroidManifest.xml
sed -i "s|android:versionName=\"[^\"]*\"|android:versionName=\"$VER_NAME\"|" AndroidManifest.xml

echo "打包配置：$HOME_URL  版本 $VER_NAME($VER_CODE) → $OUT"

rm -rf build && mkdir -p build/gen build/classes build/dex

# 内置页面副本：断网时用这一份顶上（管理版放 app-pro，客户版放 app）
rm -rf assets && mkdir -p assets
cp ../dashboard.html assets/shell.html
echo "内置页面：dashboard.html（资料统计入口）"
ls -la assets/shell.html

echo "[1/6] aapt2 compile"
$BT/aapt2 compile --dir res -o build/res.zip

echo "[2/6] aapt2 link"
$BT/aapt2 link -o build/unsigned.apk -I "$AJ" --manifest AndroidManifest.xml \
  -R build/res.zip --java build/gen --auto-add-overlay -A assets

echo "[3/6] javac"
/home/user/jdk/jdk-11.0.33+10/bin/javac -source 8 -target 8 -encoding UTF-8 -cp "$AJ" -d build/classes \
  $(find src build/gen -name "*.java") 2>&1 | grep -v "deprecat" || true

echo "[4/6] d8"
$BT/d8 --lib "$AJ" --min-api 21 --output build/dex $(find build/classes -name "*.class")

echo "[5/6] zip + zipalign"
(cd build && zip -q -j unsigned.apk dex/classes.dex)
$BT/zipalign -f 4 build/unsigned.apk build/aligned.apk

echo "[6/6] sign"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -alias aistats -keyalg RSA -keysize 2048 \
    -validity 10000 -storepass "$PASS" -keypass "$PASS" \
    -dname "CN=AIStats, OU=App, O=AIStats, L=Guangzhou, C=CN"
fi
$BT/apksigner sign --ks "$KS" --ks-key-alias aistats --ks-pass "pass:$PASS" \
  --key-pass "pass:$PASS" --out "$OUT" build/aligned.apk

$BT/apksigner verify --print-certs "$OUT" | head -5
ls -la "$OUT"
