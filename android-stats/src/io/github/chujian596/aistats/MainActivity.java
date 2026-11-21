package io.github.chujian596.aistats;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;
import android.graphics.Rect;
import android.view.WindowManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {

    private static final String HOME_URL = "https://www.chujian596.dpdns.org/dashboard.html";
    private static final int REQ_FILE = 1001;

    private WebView web;
    private ProgressBar bar;
    private FrameLayout root;
    private View errorView;
    private ValueCallback<Uri[]> fileCallback;
    private long lastBackPress = 0L;
    // 离线兜底：加载失败时改用包里内置的页面副本，URL 不变，本地数据不搬家
    private boolean offlineMode = false;
    private boolean triedOffline = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyLightBars();
        buildUi();
        // 启动直接用包里内置的页面顶上（URL 仍是线上地址，localStorage 同源，历史数据不搬家）
        // 这样网络被墙/断网也能秒开，绝不会卡在白屏或报错页
        loadLocalFirst(HOME_URL);
    }

    /** 状态栏、导航栏统一白底黑字，跟页面白底对齐 */
    private void applyLightBars() {
        try {
            android.view.Window w = getWindow();
            if (Build.VERSION.SDK_INT >= 21) {
                w.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
                w.setStatusBarColor(0xFFFFFFFF);
                w.setNavigationBarColor(0xFFFFFFFF);
            }
            if (Build.VERSION.SDK_INT >= 26) {
                w.getDecorView().setSystemUiVisibility(
                        View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
            } else if (Build.VERSION.SDK_INT >= 23) {
                w.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
            }
        } catch (Exception ignored) {
        }
    }

    private void buildUi() {
        root = new FrameLayout(this);

        web = new WebView(this);
        web.setBackgroundColor(0xFFFFFFFF);
        FrameLayout.LayoutParams wlp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        root.addView(web, wlp);

        bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        FrameLayout.LayoutParams blp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 6);
        blp.gravity = Gravity.TOP;
        root.addView(bar, blp);
        bar.setMax(100);

        setContentView(root);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        if (Build.VERSION.SDK_INT >= 21) {
            s.setMediaPlaybackRequiresUserGesture(false);
        }
        // 移动端标识，避免页面按桌面版排版
        s.setUserAgentString(s.getUserAgentString());

        web.addJavascriptInterface(new Bridge(), "AndroidAi");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                String scheme = u.getScheme() == null ? "" : u.getScheme();
                if (scheme.startsWith("http")) {
                    return false; // 站内、跨站都在本 WebView 打开
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (Exception ignored) {
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                hideError();
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (offlineMode) {
                    String u = request.getUrl().toString();
                    if (isMainDoc(u)) {
                        try {
                            InputStream is = getAssets().open("shell.html");
                            return new WebResourceResponse("text/html", "UTF-8", is);
                        } catch (IOException e) {
                            return null;
                        }
                    }
                }
                return null;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    onMainFrameFail();
                }
            }

            @SuppressWarnings("deprecation")
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                // API 23 以下没有 isForMainFrame，用失败地址判断是不是主文档
                if (Build.VERSION.SDK_INT < 23 && failingUrl != null && isMainDoc(failingUrl)) {
                    onMainFrameFail();
                }
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int progress) {
                bar.setProgress(progress);
                bar.setVisibility(progress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> cb,
                                             FileChooserParams params) {
                if (fileCallback != null) {
                    fileCallback.onReceiveValue(null);
                }
                fileCallback = cb;
                try {
                    Intent intent = params.createIntent();
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    startActivityForResult(Intent.createChooser(intent, "选择备份文件"), REQ_FILE);
                    return true;
                } catch (Exception e) {
                    fileCallback = null;
                    Toast.makeText(MainActivity.this, "打不开文件选择", Toast.LENGTH_SHORT).show();
                    return false;
                }
            }
        });

        web.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition,
                                        String mimetype, long contentLength) {
                if (url != null && url.startsWith("blob:")) {
                    return; // blob 由 JS 桥处理
                }
                try {
                    Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(i);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "下载失败", Toast.LENGTH_SHORT).show();
                }
            }
        });

        // 键盘高度桥：安卓 WebView 不会随键盘缩小自身视口，页面无法靠 CSS 感知，
        // 由原生量好键盘高度推给页面，页面把弹层顶到键盘上方
        root.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            private int lastKb = -1;
            @Override
            public void onGlobalLayout() {
                try {
                    Rect r = new Rect();
                    root.getWindowVisibleDisplayFrame(r);
                    int screenH = root.getRootView().getHeight();
                    int kb = screenH - r.bottom;
                    if (kb < screenH / 6) kb = 0;   // 小于 1/6 算状态栏误差，不算键盘
                    if (kb != lastKb) {
                        lastKb = kb;
                        web.evaluateJavascript("try{window.__kbFix&&window.__kbFix(" + kb + ")}catch(e){}", null);
                    }
                } catch (Exception ignored) {
                }
            }
        });
    }

    /** 直接读包内页面交给 WebView 渲染：不走网络，也就不会白屏、不会报连接错误。
     *  baseUrl 用线上地址，保证 localStorage 同源，历史订单数据不搬家。 */
    private void loadLocalFirst(String url) {
        offlineMode = true;
        triedOffline = false;
        hideError();
        try {
            InputStream is = getAssets().open("shell.html");
            java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
            is.close();
            String html = new String(bos.toByteArray(), "UTF-8");
            if (html == null || html.length() < 1000) throw new IOException("empty shell");
            web.loadDataWithBaseURL(url, html, "text/html", "UTF-8", null);
        } catch (Exception e) {
            // 读包内页面失败才退回网络地址
            try { web.loadUrl(url); } catch (Exception ignored) {}
        }
    }

    private void load(String url) {
        offlineMode = false;
        triedOffline = false;
        hideError();
        web.loadUrl(url);
    }

    /** 主文档打不开：先用包里内置的页面副本顶上，还不行才显示错误页 */
    private void onMainFrameFail() {
        if (!triedOffline) {
            triedOffline = true;
            offlineMode = true;
            hideError();
            web.loadUrl(HOME_URL);
            Toast.makeText(this, "网络不稳，已用内置页面打开", Toast.LENGTH_SHORT).show();
        } else {
            showError("网络连不上，检查一下网络再点重试");
        }
    }

    /** 判断是不是主页面请求（忽略查询参数） */
    private boolean isMainDoc(String url) {
        if (url == null) return false;
        String p = url;
        int q = p.indexOf('?');
        if (q >= 0) p = p.substring(0, q);
        int h = p.indexOf("://");
        if (h >= 0) {
            int slash = p.indexOf('/', h + 3);
            p = slash >= 0 ? p.substring(slash) : "/";
        }
        return "/".equals(p) || "/dashboard".equals(p) || "/dashboard.html".equals(p)
                || "/app".equals(p) || "/app.html".equals(p) || "/app-pro".equals(p) || "/app-pro.html".equals(p);
    }

    private void showError(String msg) {
        hideError();
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setBackgroundColor(0xFFFFFFFF);
        box.setPadding(48, 0, 48, 0);

        TextView t = new TextView(this);
        t.setText(msg);
        t.setTextSize(16);
        t.setTextColor(0xFF333333);
        t.setGravity(Gravity.CENTER);
        box.addView(t);

        TextView btn = new TextView(this);
        btn.setText("重试");
        btn.setTextSize(16);
        btn.setTextColor(0xFF1A1A1A);
        btn.setGravity(Gravity.CENTER);
        btn.setPadding(0, 44, 0, 44);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(420, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = 36;
        btn.setLayoutParams(lp);
        btn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                load(HOME_URL);
            }
        });
        box.addView(btn);

        FrameLayout.LayoutParams flp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        root.addView(box, flp);
        errorView = box;
    }

    private void hideError() {
        if (errorView != null) {
            root.removeView(errorView);
            errorView = null;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQ_FILE) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null) {
                if (data.getClipData() != null) {
                    int n = data.getClipData().getItemCount();
                    result = new Uri[n];
                    for (int i = 0; i < n; i++) {
                        result[i] = data.getClipData().getItemAt(i).getUri();
                    }
                } else if (data.getData() != null) {
                    result = new Uri[]{data.getData()};
                }
            }
            if (fileCallback != null) {
                fileCallback.onReceiveValue(result);
                fileCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (web != null && web.canGoBack()) {
                web.goBack();
                return true;
            }
            // 页面里有弹层（历史账单、设置、提示框等）时，先关弹层，不退出
            if (web != null) {
                web.evaluateJavascript(
                        "(window.__closeTopOverlay ? window.__closeTopOverlay() : 'none')",
                        new ValueCallback<String>() {
                            @Override
                            public void onReceiveValue(String value) {
                                if (value != null && value.indexOf("closed") >= 0) return;
                                handleExit();
                            }
                        });
                return true;
            }
            handleExit();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    private void handleExit() {
        long now = System.currentTimeMillis();
        if (now - lastBackPress < 2000) {
            finish();
            return;
        }
        lastBackPress = now;
        Toast.makeText(this, "再按一次退出", Toast.LENGTH_SHORT).show();
    }

    /** 页面调用：导出备份等文件落地到手机 Download/AI统计/ */
    public class Bridge {
        @JavascriptInterface
        public void saveFile(String filename, String content) {
            final String name = safeName(filename);
            final String body = content == null ? "" : content;
            try {
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues v = new ContentValues();
                    v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                    v.put(MediaStore.MediaColumns.MIME_TYPE, "application/json");
                    v.put(MediaStore.MediaColumns.RELATIVE_PATH, "Download/AI统计");
                    Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                    if (uri == null) throw new RuntimeException("insert failed");
                    OutputStream os = getContentResolver().openOutputStream(uri);
                    os.write(body.getBytes("UTF-8"));
                    os.flush();
                    os.close();
                } else {
                    File dir = new File(Environment.getExternalStoragePublicDirectory(
                            Environment.DIRECTORY_DOWNLOADS), "AI统计");
                    if (!dir.exists()) dir.mkdirs();
                    FileOutputStream fos = new FileOutputStream(new File(dir, name));
                    fos.write(body.getBytes("UTF-8"));
                    fos.flush();
                    fos.close();
                }
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(MainActivity.this,
                                "已保存到 下载/AI统计/" + name, Toast.LENGTH_LONG).show();
                    }
                });
            } catch (final Exception e) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(MainActivity.this,
                                "保存失败：" + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            }
        }
    }

    private String safeName(String raw) {
        String s = raw == null ? "" : raw;
        s = s.replace("/", "_").replace("\\", "_").replace(":", "_");
        if (s.length() == 0) s = "备份.json";
        return s;
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            root.removeView(web);
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
