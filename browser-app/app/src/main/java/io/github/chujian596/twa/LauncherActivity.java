package io.github.chujian596.twa;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 我的浏览器 v3：多标签 + 常用站点 + 设置菜单。
 * 全部界面自绘（黑白灰），不依赖主题/XML 布局。
 */
public class LauncherActivity extends Activity {

    private static final int C_TXT = 0xFF222222;
    private static final int C_SUB = 0xFF999999;
    private static final int C_LINE = 0xFFE5E5E5;
    private static final int C_BG = 0xFFF5F6F7;

    private static class Tab {
        WebView web;
        String title = "新标签";
        TextView chip;
        FrameLayout holder;
    }

    private final List<Tab> tabs = new ArrayList<>();
    private Tab cur;
    private FrameLayout pages;
    private LinearLayout tabStrip;
    private HorizontalScrollView tabScroll;
    private EditText addr;
    private SharedPreferences sp;
    private ValueCallback<Uri[]> filePathCallback;

    @Override
    protected void onCreate(Bundle b) {
        // 强制浅色界面：系统深色模式会把对话框刷成黑底，灰字看不清
        try {
            Configuration cfg = getResources().getConfiguration();
            cfg.uiMode = (cfg.uiMode & ~Configuration.UI_MODE_NIGHT_MASK) | Configuration.UI_MODE_NIGHT_NO;
            getResources().updateConfiguration(cfg, getResources().getDisplayMetrics());
        } catch (Exception ignored) {}
        setTheme(android.R.style.Theme_DeviceDefault_Light_NoActionBar);
        super.onCreate(b);
        sp = getSharedPreferences("browser", MODE_PRIVATE);

        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        w.setStatusBarColor(0xFFF7F7F7);
        try {
            View dv = w.getDecorView();
            int f = dv.getSystemUiVisibility();
            if (Build.VERSION.SDK_INT >= 23) f |= 0x00002000;
            if (Build.VERSION.SDK_INT >= 26) f |= 0x00000010;
            dv.setSystemUiVisibility(f);
        } catch (Exception ignored) {}

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(C_BG);

        root.addView(buildTabStrip(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40)));
        root.addView(buildAddressBar(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));

        pages = new FrameLayout(this);
        root.addView(pages, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        root.addView(buildBottomBar(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(50)));
        setContentView(root);

        newTab(startPage(), true);
    }

    private int dp(float v) { return (int) (v * getResources().getDisplayMetrics().density + 0.5f); }

    // ---------------- 标签栏 ----------------

    private View buildTabStrip() {
        LinearLayout wrap = new LinearLayout(this);
        wrap.setOrientation(LinearLayout.HORIZONTAL);
        wrap.setBackgroundColor(0xFFFFFFFF);
        wrap.setPadding(dp(6), dp(4), dp(6), dp(4));
        wrap.setGravity(Gravity.CENTER_VERTICAL);

        tabScroll = new HorizontalScrollView(this);
        tabScroll.setHorizontalScrollBarEnabled(false);
        tabStrip = new LinearLayout(this);
        tabStrip.setOrientation(LinearLayout.HORIZONTAL);
        tabScroll.addView(tabStrip, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.MATCH_PARENT));
        wrap.addView(tabScroll, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        TextView plus = new TextView(this);
        plus.setText("＋");
        plus.setTextSize(18);
        plus.setTextColor(C_TXT);
        plus.setGravity(Gravity.CENTER);
        plus.setPadding(dp(10), 0, dp(10), 0);
        plus.setOnClickListener(v -> newTab(startPage(), true));
        wrap.addView(plus, new LinearLayout.LayoutParams(dp(40), ViewGroup.LayoutParams.MATCH_PARENT));
        return wrap;
    }

    private static boolean isInternal(String u) {
        return u == null || u.startsWith("file://") || u.startsWith("data:") || u.startsWith("about:");
    }

    private static String showUrl(String u) {
        return isInternal(u) ? "" : u;
    }

    private String tabLabel(Tab t) {
        String title = t.title == null ? "" : t.title.trim();
        if (title.startsWith("data:") || title.startsWith("about:")) title = "";
        if (!title.isEmpty()) return title;
        String u = t.web.getUrl();
        if (isInternal(u)) return "起始页";
        try { String h = Uri.parse(u).getHost(); return h == null ? "网页" : h; } catch (Exception e) { return "网页"; }
    }

    private void refreshChips() {
        if (tabStrip == null) return;
        tabStrip.removeAllViews();
        for (final Tab t : tabs) {
            TextView chip = new TextView(this);
            String s = tabLabel(t);
            if (s.length() > 8) s = s.substring(0, 8) + "…";
            chip.setText(s);
            chip.setTextSize(12);
            chip.setSingleLine(true);
            chip.setGravity(Gravity.CENTER);
            chip.setPadding(dp(10), dp(4), dp(10), dp(4));
            if (t == cur) {
                chip.setBackground(box(0xFF222222, 0xFF222222, 14));
                chip.setTextColor(0xFFFFFFFF);
            } else {
                chip.setBackground(box(0xFFFFFFFF, C_LINE, 14));
                chip.setTextColor(0xFF555555);
            }
            chip.setOnClickListener(v -> switchTab(t));
            chip.setOnLongClickListener(v -> { closeTab(t); return true; });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.MATCH_PARENT);
            lp.rightMargin = dp(4);
            tabStrip.addView(chip, lp);
            t.chip = chip;
        }
    }

    private android.graphics.drawable.GradientDrawable box(int fill, int stroke, int radiusDp) {
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(radiusDp));
        g.setStroke(dp(1), stroke);
        return g;
    }

    private void switchTab(Tab t) {
        if (t == null || t == cur) return;
        cur = t;
        pages.removeAllViews();
        pages.addView(t.holder, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        addr.setText(showUrl(t.web.getUrl()));
        refreshChips();
    }

    private void closeTab(Tab t) {
        if (tabs.size() <= 1) { toast("只剩一个标签，不能关"); return; }
        tabs.remove(t);
        pages.removeView(t.holder);
        try { t.web.destroy(); } catch (Exception ignored) {}
        if (cur == t) {
            cur = null;
            switchTab(tabs.get(tabs.size() - 1));
        } else {
            refreshChips();
        }
    }

    private Tab newTab(String url, boolean activate) {
        Tab t = new Tab();
        t.holder = new FrameLayout(this);
        t.web = buildWebView();
        t.holder.addView(t.web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        tabs.add(t);
        t.web.loadUrl(url);
        if (activate) {
            pages.removeAllViews();
            cur = t;
            pages.addView(t.holder, new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
            addr.setText(showUrl(url));
        }
        refreshChips();
        return t;
    }

    // ---------------- 地址栏 ----------------

    private View buildAddressBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(0xFFFFFFFF);
        bar.setPadding(dp(8), dp(6), dp(8), dp(6));

        addr = new EditText(this);
        addr.setHint("输入网址或搜索…");
        addr.setSingleLine(true);
        addr.setTextSize(13);
        addr.setTextColor(C_TXT);
        addr.setHintTextColor(0xFFBBBBBB);
        addr.setBackground(box(0xFFF7F7F7, C_LINE, 8));
        addr.setPadding(dp(10), dp(4), dp(10), dp(4));
        addr.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        addr.setOnEditorActionListener((v, actionId, ev) -> { go(); return true; });
        bar.addView(addr, new LinearLayout.LayoutParams(0, dp(38), 1f));

        TextView go = tbtnSmall("前往");
        go.setOnClickListener(v -> go());
        LinearLayout.LayoutParams g1 = new LinearLayout.LayoutParams(dp(52), dp(36));
        g1.leftMargin = dp(6);
        bar.addView(go, g1);

        TextView re = tbtnSmall("刷新");
        re.setOnClickListener(v -> { if (cur != null) cur.web.reload(); });
        LinearLayout.LayoutParams g2 = new LinearLayout.LayoutParams(dp(52), dp(36));
        g2.leftMargin = dp(6);
        bar.addView(re, g2);
        return bar;
    }

    private TextView tbtnSmall(String s) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(12);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setTextColor(0xFF1F2329);
        t.setBackground(box(0xFFFFFFFF, 0xFFD9DDE3, 6));
        t.setGravity(Gravity.CENTER);
        return t;
    }

    private void go() {
        String raw = addr.getText().toString().trim();
        if (raw.isEmpty()) return;
        String url = raw;
        if (!raw.startsWith("http://") && !raw.startsWith("https://") && !raw.startsWith("file://")) {
            boolean looksUrl = raw.contains(".com") || raw.contains(".cn") || raw.contains(".net")
                    || raw.contains(".org") || raw.contains(".io") || raw.contains(".html")
                    || raw.matches("[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}(/.*)?");
            url = looksUrl ? "https://" + raw
                    : "https://www.baidu.com/s?wd=" + Uri.encode(raw);
        }
        if (cur == null) newTab(url, true);
        else cur.web.loadUrl(url);
    }

    // ---------------- WebView ----------------

    private WebView buildWebView() {
        WebView web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setTextZoom(sp.getInt("zoom", 100));
        if (Build.VERSION.SDK_INT >= 29) {
            s.setForceDark(sp.getBoolean("night", false)
                    ? WebSettings.FORCE_DARK_ON : WebSettings.FORCE_DARK_OFF);
        }
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("http:") || url.startsWith("https:") || url.startsWith("file:")) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) {}
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (cur != null && view == cur.web) addr.setText(showUrl(url));
                String t = view.getTitle();
                for (Tab tab : tabs) {
                    if (tab.web == view) {
                        if (t != null && (t.startsWith("data:") || t.startsWith("about:"))) t = "起始页";
                        if (t == null || t.isEmpty()) {
                            if (isInternal(url)) t = "起始页";
                            else { try { t = Uri.parse(url).getHost(); } catch (Exception ignored) {} }
                        }
                        tab.title = t;
                        break;
                    }
                }
                refreshChips();
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> cb,
                                             FileChooserParams params) {
                if (filePathCallback != null) filePathCallback.onReceiveValue(null);
                filePathCallback = cb;
                try {
                    Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                    i.addCategory(Intent.CATEGORY_OPENABLE);
                    i.setType("*/*");
                    startActivityForResult(Intent.createChooser(i, "选择文件"), 4321);
                    return true;
                } catch (Exception e) {
                    filePathCallback = null;
                    return false;
                }
            }
        });

        web.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String ua, String cd, String mime, long len) {
                try {
                    DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
                    r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,
                            Uri.parse(url).getLastPathSegment());
                    ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(r);
                    toast("开始下载");
                } catch (Exception e) { toast("下载失败：" + e.getMessage()); }
            }
        });
        return web;
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        if (req == 4321) {
            if (filePathCallback != null) {
                Uri[] out = null;
                if (res == RESULT_OK && data != null && data.getData() != null) out = new Uri[]{data.getData()};
                filePathCallback.onReceiveValue(out);
                filePathCallback = null;
            }
            return;
        }
        super.onActivityResult(req, res, data);
    }

    // ---------------- 底部工具栏 ----------------

    private View buildBottomBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setBackgroundColor(0xFFFFFFFF);
        bar.setGravity(Gravity.CENTER_VERTICAL);

        bar.addView(barItem("◀", v -> {
            if (cur != null && cur.web.canGoBack()) cur.web.goBack();
            else toast("没有上一页");
        }));
        bar.addView(barItem("▶", v -> {
            if (cur != null && cur.web.canGoForward()) cur.web.goForward();
            else toast("没有下一页");
        }));
        bar.addView(barItem("⌂", v -> { if (cur != null) cur.web.loadUrl(startPage()); }));
        bar.addView(barItem("★", v -> openBookmarks()));
        bar.addView(barItem("☆", v -> addBookmark()));
        bar.addView(barItem("☰", v -> openSettings()));
        return bar;
    }

    private View barItem(String label, View.OnClickListener click) {
        TextView t = new TextView(this);
        t.setText(label);
        t.setTextSize(18);
        t.setTextColor(C_TXT);
        t.setGravity(Gravity.CENTER);
        t.setOnClickListener(click);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f);
        t.setLayoutParams(lp);
        return t;
    }

    // ---------------- 常用站点 ----------------

    private Map<String, String> bookmarks() {
        Map<String, String> m = new LinkedHashMap<>();
        String raw = sp.getString("marks", "");
        if (raw == null || raw.isEmpty()) return m;
        for (String line : raw.split("\n")) {
            String[] p = line.split("\\|", 2);
            if (p.length == 2 && p[0].startsWith("http")) m.put(p[0], p[1]);
        }
        return m;
    }

    private void saveBookmarks(Map<String, String> m) {
        StringBuilder b = new StringBuilder();
        for (Map.Entry<String, String> e : m.entrySet()) {
            if (b.length() > 0) b.append("\n");
            b.append(e.getKey()).append("|").append(e.getValue());
        }
        sp.edit().putString("marks", b.toString()).apply();
    }

    private void addBookmark() {
        if (cur == null) return;
        String url = cur.web.getUrl();
        if (url == null || url.startsWith("file://")) { toast("先打开一个网页再加常用"); return; }
        Map<String, String> m = bookmarks();
        if (m.containsKey(url)) { toast("已经在常用里了"); return; }
        final String u = url;
        EditText et = new EditText(this);
        et.setText(cur.title == null ? Uri.parse(u).getHost() : cur.title);
        et.setTextSize(14);
        et.setSingleLine(true);
        et.setPadding(dp(12), dp(8), dp(12), dp(8));
        new AlertDialog.Builder(this)
                .setTitle("加入常用站点")
                .setMessage(u)
                .setView(et)
                .setPositiveButton("加入", (d, w) -> {
                    String name = et.getText().toString().trim();
                    if (name.isEmpty()) name = Uri.parse(u).getHost();
                    Map<String, String> mm = bookmarks();
                    mm.put(u, name);
                    saveBookmarks(mm);
                    toast("已加入常用：" + name);
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private String startPage() {
        StringBuilder cards = new StringBuilder();
        Map<String, String> marks = bookmarks();
        for (Map.Entry<String, String> e : marks.entrySet()) cards.append(card(e.getValue(), e.getKey()));
        String quick = card("录单（专业版）", "https://chujian596.github.io/ai-stats/app-pro.html")
                + card("录单（客户版）", "https://chujian596.github.io/ai-stats/app.html")
                + card("资料统计", "https://chujian596.github.io/ai-stats/stats.html")
                + card("资料系统总管理", "https://chujian596.github.io/ai-stats/manage.html")
                + card("导航页", "https://chujian596.github.io/ai-stats/portal.html")
                + card("问题本", "https://chujian596.github.io/ai-stats/issues.html");
        return "data:text/html;charset=utf-8," + Uri.encode(
                "<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
                        + "<style>body{margin:0;background:#f5f6f7;font-family:-apple-system,sans-serif;padding:14px}"
                        + "h2{font-size:15px;color:#222;margin:6px 0 10px}"
                        + "a{display:block;text-decoration:none;background:#fff;border:1px solid #e5e5e5;border-radius:10px;"
                        + "padding:12px 14px;margin-bottom:8px;color:#222;font-size:14px;font-weight:600}"
                        + "small{display:block;color:#999;font-weight:400;font-size:11px;margin-top:3px;word-break:break-all}"
                        + "p{color:#999;font-size:12px}</style></head><body><h2>常用站点</h2>"
                        + (cards.length() == 0 ? "<p>还没有常用：打开网页点底部 ☆ 添加。</p>" : cards)
                        + "<h2>系统入口</h2>" + quick
                        + "</body></html>");
    }

    private String card(String title, String url) {
        return "<a href='" + url + "'>" + esc(title) + "<small>" + esc(url) + "</small></a>";
    }

    private String esc(String s) {
        return s == null ? "" : s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;");
    }

    // ---------------- 设置菜单 ----------------

    private void openSettings() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setBackgroundColor(0xFFFFFFFF);
        box.setPadding(dp(16), dp(12), dp(16), dp(12));

        CheckBox night = new CheckBox(this);
        night.setText("夜间模式（网页自动变暗）");
        night.setTextSize(13);
        night.setTextColor(C_TXT);
        night.setChecked(sp.getBoolean("night", false));
        night.setOnCheckedChangeListener((v, on) -> {
            sp.edit().putBoolean("night", on).apply();
            for (Tab t : tabs) applyNight(t.web, on);
        });
        box.addView(night);

        TextView zoomLbl = tv("网页字号", 13, C_SUB);
        zoomLbl.setPadding(0, dp(8), 0, dp(2));
        box.addView(zoomLbl);
        LinearLayout zoomRow = new LinearLayout(this);
        zoomRow.setOrientation(LinearLayout.HORIZONTAL);
        String[] names = {"小", "标准", "大"};
        int[] vals = {90, 100, 115};
        for (int i = 0; i < 3; i++) {
            final int v = vals[i];
            final String nm = names[i];
            TextView b = tbtnSmall(nm);
            b.setPadding(dp(12), dp(6), dp(12), dp(6));
            b.setOnClickListener(x -> {
                sp.edit().putInt("zoom", v).apply();
                for (Tab t : tabs) t.web.getSettings().setTextZoom(v);
                toast("字号：" + nm);
            });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            lp.rightMargin = dp(6);
            zoomRow.addView(b, lp);
        }
        box.addView(zoomRow);

        TextView clear = tv("清除网页缓存（不影响登录和数据）", 13, C_TXT);
        clear.setPadding(0, dp(14), 0, dp(8));
        clear.setOnClickListener(v -> {
            WebView dummy = new WebView(this);
            dummy.clearCache(true);
            dummy.destroy();
            CookieManager.getInstance().flush();
            toast("缓存已清除");
        });
        box.addView(clear);

        TextView marksMgr = tv("管理常用站点（" + bookmarks().size() + " 个）", 13, C_TXT);
        marksMgr.setPadding(0, dp(6), 0, dp(8));
        marksMgr.setOnClickListener(v -> manageMarks());
        box.addView(marksMgr);

        box.addView(tv("我的浏览器 v3　多标签 / 常用站点 / 设置", 12, C_SUB));

        ScrollView sc = new ScrollView(this);
        sc.addView(box);
        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("设置")
                .setView(sc)
                .setPositiveButton("完成", null)
                .create();
        d.setOnShowListener(x -> lightDialog(d));
        d.show();
    }

    /** 把对话框刷成白底黑字，避免跟随系统深色变成黑底灰字 */
    private void lightDialog(AlertDialog d) {
        try {
            android.graphics.drawable.Drawable bg = d.getWindow().getDecorView().getBackground();
            if (bg != null) bg.setColorFilter(0xFFFFFFFF, android.graphics.PorterDuff.Mode.SRC_IN);
            d.getWindow().setBackgroundDrawableResource(android.R.color.white);
            d.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(C_TXT);
            d.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(C_TXT);
            android.widget.TextView t = d.findViewById(getResources().getIdentifier("alertTitle", "id", "android"));
            if (t != null) t.setTextColor(C_TXT);
        } catch (Exception ignored) {}
    }

    private void applyNight(WebView web, boolean on) {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                web.getSettings().setForceDark(on ? WebSettings.FORCE_DARK_ON : WebSettings.FORCE_DARK_OFF);
            } else {
                web.evaluateJavascript(on
                        ? "(function(){var s=document.createElement('style');s.id='ntvnight';s.textContent='html{filter:invert(1) hue-rotate(180deg);background:#111!important}img,iframe,canvas{filter:invert(1) hue-rotate(180deg)}';document.documentElement.appendChild(s)})()"
                        : "var x=document.getElementById('ntvnight');if(x)x.remove();", null);
            }
        } catch (Exception ignored) {}
    }

    private void openBookmarks() {
        final Map<String, String> m = bookmarks();
        LinearLayout list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        list.setBackgroundColor(0xFFFFFFFF);
        list.setPadding(dp(8), dp(8), dp(8), dp(8));
        if (m.isEmpty()) {
            TextView empty = tv("收藏夹还是空的：打开网页点底部 ☆ 加入。", 13, C_SUB);
            empty.setPadding(dp(12), dp(16), dp(12), dp(16));
            list.addView(empty);
        }
        for (final Map.Entry<String, String> e : m.entrySet()) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(dp(12), dp(12), dp(12), dp(12));
            row.setBackground(box(0xFFFFFFFF, C_LINE, 8));
            TextView name = tv(e.getValue(), 14, C_TXT);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            TextView url = tv(e.getKey(), 11, C_SUB);
            url.setSingleLine(true);
            url.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE);
            row.addView(name);
            row.addView(url);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.bottomMargin = dp(8);
            row.setOnClickListener(v -> {
                if (cur != null) cur.web.loadUrl(e.getKey());
            });
            row.setOnLongClickListener(v -> {
                Toast.makeText(this, "长按删除「" + e.getValue() + "」", Toast.LENGTH_SHORT).show();
                Map<String, String> mm = bookmarks();
                mm.remove(e.getKey());
                saveBookmarks(mm);
                toast("已删除：" + e.getValue());
                return true;
            });
            list.addView(row, lp);
        }
        ScrollView sc = new ScrollView(this);
        sc.setBackgroundColor(0xFFFFFFFF);
        sc.addView(list);
        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("收藏夹（" + m.size() + " 个）· 点开，长按删")
                .setView(sc)
                .setPositiveButton("关闭", null)
                .create();
        d.setOnShowListener(x -> lightDialog(d));
        d.show();
    }

    private void manageMarks() {
        final Map<String, String> m = bookmarks();
        if (m.isEmpty()) { toast("常用站点还是空的：打开网页点底部 ☆"); return; }
        final List<String> urls = new ArrayList<>(m.keySet());
        String[] items = new String[urls.size()];
        for (int i = 0; i < urls.size(); i++) items[i] = m.get(urls.get(i));
        new AlertDialog.Builder(this)
                .setTitle("点一个删除")
                .setItems(items, (d, which) -> {
                    Map<String, String> mm = bookmarks();
                    mm.remove(urls.get(which));
                    saveBookmarks(mm);
                    toast("已删除");
                })
                .setNegativeButton("关闭", null)
                .show();
    }

    private TextView tv(String s, int size, int color) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setTextColor(color);
        return t;
    }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }

    // ---------------- 返回键 ----------------

    @Override
    public void onBackPressed() {
        if (cur != null && cur.web.canGoBack()) { cur.web.goBack(); return; }
        if (tabs.size() > 1) { closeTab(cur); return; }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        for (Tab t : tabs) {
            try { t.web.destroy(); } catch (Exception ignored) {}
        }
        tabs.clear();
        super.onDestroy();
    }
}
