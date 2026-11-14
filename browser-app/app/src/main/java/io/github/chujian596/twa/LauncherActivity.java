package io.github.chujian596.twa;

import android.app.Activity;
import android.content.res.Configuration;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;

public class LauncherActivity extends Activity {

    private WebView webView;
    private EditText addressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 设置状态栏颜色
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(Color.parseColor("#ffffff"));
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }

        // 创建根布局（垂直）
        LinearLayout rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setBackgroundColor(Color.parseColor("#ffffff"));

        // ===== 顶部地址栏 =====
        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setPadding(12, 12, 12, 12);
        topBar.setBackgroundColor(Color.parseColor("#f5f5f5"));
        topBar.setGravity(android.view.Gravity.CENTER_VERTICAL);

        // 地址输入框（圆角）
        addressBar = new EditText(this);
        addressBar.setHint("输入网址或搜索...");
        addressBar.setBackgroundColor(Color.parseColor("#ffffff"));
        addressBar.setPadding(20, 10, 20, 10);
        addressBar.setSingleLine(true);
        addressBar.setTextSize(14);
        LinearLayout.LayoutParams addressParams = new LinearLayout.LayoutParams(0, 40, 1);
        topBar.addView(addressBar, addressParams);

        // 访问按钮
        Button btnGo = new Button(this);
        btnGo.setText("前往");
        btnGo.setBackgroundColor(Color.parseColor("#2196F3"));
        btnGo.setTextColor(Color.parseColor("#ffffff"));
        btnGo.setAllCaps(false);
        btnGo.setTextSize(13);
        LinearLayout.LayoutParams goParams = new LinearLayout.LayoutParams(80, 40);
        goParams.setMargins(10, 0, 0, 0);
        btnGo.setOnClickListener(v -> {
            String url = addressBar.getText().toString().trim();
            if(!url.startsWith("http://") && !url.startsWith("https://")){
                url = "https://" + url;
            }
            webView.loadUrl(url);
        });
        topBar.addView(btnGo, goParams);

        rootLayout.addView(topBar, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        // ===== WebView =====
        webView = new WebView(this);
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webSettings.setAllowFileAccessFromFileURLs(true);
        webSettings.setAllowUniversalAccessFromFileURLs(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setBuiltInZoomControls(true);
        webSettings.setDisplayZoomControls(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                view.loadUrl(url);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                addressBar.setText(url);
                // 注入广告屏蔽JS
                String adBlockJS = "javascript:" +
                    "(function(){" +
                    "var ads = document.querySelectorAll('[id*=\"ad\"],[class*=\"ad\"],[class*=\"banner\"],[id*=\"banner\"]);" +
                    "ads.forEach(function(el){ el.style.display='none'; });" +
                    "})()";
                view.evaluateJavascript(adBlockJS, null);
            }
        });

        rootLayout.addView(webView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        // ===== 底部工具栏 =====
        LinearLayout bottomBar = new LinearLayout(this);
        bottomBar.setOrientation(LinearLayout.HORIZONTAL);
        bottomBar.setBackgroundColor(Color.parseColor("#f5f5f5"));
        bottomBar.setPadding(0, 8, 0, 8);
        bottomBar.setGravity(android.view.Gravity.CENTER);

        // 后退按钮
        Button btnBack = new Button(this);
        btnBack.setText("◀");
        btnBack.setBackgroundColor(Color.parseColor("#f5f5f5"));
        btnBack.setTextSize(20);
        LinearLayout.LayoutParams backParams = new LinearLayout.LayoutParams(0, 50, 1);
        btnBack.setOnClickListener(v -> {
            if(webView.canGoBack()) webView.goBack();
        });
        bottomBar.addView(btnBack, backParams);

        // 首页按钮
        Button btnHome = new Button(this);
        btnHome.setText("🏠");
        btnHome.setBackgroundColor(Color.parseColor("#f5f5f5"));
        btnHome.setTextSize(20);
        LinearLayout.LayoutParams homeParams = new LinearLayout.LayoutParams(0, 50, 1);
        btnHome.setOnClickListener(v -> webView.loadUrl("file:///android_asset/home.html"));
        bottomBar.addView(btnHome, homeParams);

        // 刷新按钮
        Button btnRefresh = new Button(this);
        btnRefresh.setText("🔄");
        btnRefresh.setBackgroundColor(Color.parseColor("#f5f5f5"));
        btnRefresh.setTextSize(20);
        LinearLayout.LayoutParams refreshParams = new LinearLayout.LayoutParams(0, 50, 1);
        btnRefresh.setOnClickListener(v -> webView.reload());
        bottomBar.addView(btnRefresh, refreshParams);

        // 前进按钮
        Button btnForward = new Button(this);
        btnForward.setText("▶");
        btnForward.setBackgroundColor(Color.parseColor("#f5f5f5"));
        btnForward.setTextSize(20);
        LinearLayout.LayoutParams forwardParams = new LinearLayout.LayoutParams(0, 50, 1);
        btnForward.setOnClickListener(v -> {
            if(webView.canGoForward()) webView.goForward();
        });
        bottomBar.addView(btnForward, forwardParams);

        rootLayout.addView(bottomBar, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        setContentView(rootLayout);

        // 默认打开我们的导航首页
        webView.loadUrl("file:///android_asset/home.html");
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
