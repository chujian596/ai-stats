#!/bin/bash
# 打包在线 WebView 版 APK（指向 Cloudflare Pages）
set -e
export JAVA_HOME=/home/user/jdk/jdk-11.0.33+10
export PATH=$JAVA_HOME/bin:$PATH

SDK=/home/user/android-sdk
BT=$SDK/build-tools/34.0.0
AJ=$SDK/platforms/android-34/android.jar
PASS=aistats2026app
KS=$PWD/keystore.jks

cd "$(dirname "$0")"
rm -rf build && mkdir -p build/gen build/classes build/dex

echo "[1/6] aapt2 compile"
$BT/aapt2 compile --dir res -o build/res.zip

echo "[2/6] aapt2 link"
$BT/aapt2 link -o build/unsigned.apk -I "$AJ" --manifest AndroidManifest.xml \
  -R build/res.zip --java build/gen --auto-add-overlay

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
  --key-pass "pass:$PASS" --out app-release-webview.apk build/aligned.apk

$BT/apksigner verify --print-certs app-release-webview.apk | head -5
ls -la app-release-webview.apk
