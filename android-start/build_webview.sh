#!/bin/bash
# 打包“起始页”在线 WebView APK（页面远程加载，改页面不用重打）
set -e
export JAVA_HOME=/home/user/jdk/jdk-11.0.33+10
export PATH=$JAVA_HOME/bin:$PATH

SDK=/home/user/android-sdk
BT=$SDK/build-tools/34.0.0
AJ=$SDK/platforms/android-34/android.jar
PASS=aistats2026app

cd "$(dirname "$0")"
KS="$(pwd)/keystore.jks"
HOME_URL="${APP_HOME_URL:-https://www.chujian596.dpdns.org/start.html}"
VER_NAME="${APP_VER_NAME:-1.0}"
VER_CODE="${APP_VER_CODE:-100}"
OUT="${APK_OUT:-ai-stats-start-v1.0.apk}"

MAIN=src/com/chujian596/start/MainActivity.java
cp "$MAIN" /tmp/_MainActivity_start_orig.java
cp AndroidManifest.xml /tmp/_AndroidManifest_start_orig.xml
trap 'cp /tmp/_MainActivity_start_orig.java "$MAIN"; cp /tmp/_AndroidManifest_start_orig.xml AndroidManifest.xml' EXIT

sed -i "s|HOME_URL = \"[^\"]*\"|HOME_URL = \"$HOME_URL\"|" "$MAIN"
sed -i "s|android:versionCode=\"[0-9]*\"|android:versionCode=\"$VER_CODE\"|" AndroidManifest.xml
sed -i "s|android:versionName=\"[^\"]*\"|android:versionName=\"$VER_NAME\"|" AndroidManifest.xml

echo "打包配置：$HOME_URL  版本 $VER_NAME($VER_CODE) → $OUT"

rm -rf build && mkdir -p build/gen build/classes build/dex
rm -rf assets && mkdir -p assets
cp -f ../start.html assets/shell.html
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
