#!/bin/bash
# 原生版打包：不依赖网页、不依赖网络，全部逻辑在 dex 里
set -e
export JAVA_HOME=/home/user/jdk/jdk-11.0.33+10
export PATH=$JAVA_HOME/bin:$PATH

SDK=/home/user/android-sdk
BT=$SDK/build-tools/34.0.0
AJ=$SDK/platforms/android-34/android.jar
PASS=aistats2026app

cd "$(dirname "$0")"
KS="../android-webview/keystore.jks"
OUT="${APK_OUT:-app-release-ntv.apk}"
VER_NAME="${APP_VER_NAME:-1.0}"
VER_CODE="${APP_VER_CODE:-1}"

sed -i "s|android:versionCode=\"[0-9]*\"|android:versionCode=\"$VER_CODE\"|" AndroidManifest.xml
sed -i "s|android:versionName=\"[^\"]*\"|android:versionName=\"$VER_NAME\"|" AndroidManifest.xml

echo "原生版 $VER_NAME($VER_CODE) → $OUT"
rm -rf build && mkdir -p build/gen build/classes build/dex

echo "[1/6] aapt2 compile"
$BT/aapt2 compile --dir res -o build/res.zip
echo "[2/6] aapt2 link"
$BT/aapt2 link -o build/unsigned.apk -I "$AJ" --manifest AndroidManifest.xml \
  -R build/res.zip --java build/gen --auto-add-overlay

echo "[3/6] javac"
javac -source 8 -target 8 -encoding UTF-8 -cp "$AJ" -d build/classes \
  $(find src build/gen -name "*.java") 2>&1 | grep -v "bootstrap\|deprecat" || true

echo "[4/6] d8"
$BT/d8 --lib "$AJ" --min-api 21 --output build/dex $(find build/classes -name "*.class")

echo "[5/6] zip + zipalign"
(cd build && zip -q -j unsigned.apk dex/classes.dex)
$BT/zipalign -f 4 build/unsigned.apk build/aligned.apk

echo "[6/6] sign"
$BT/apksigner sign --ks "$KS" --ks-key-alias aistats --ks-pass "pass:$PASS" \
  --key-pass "pass:$PASS" --out "$OUT" build/aligned.apk
$BT/apksigner verify --print-certs "$OUT" | head -4
ls -la "$OUT"
