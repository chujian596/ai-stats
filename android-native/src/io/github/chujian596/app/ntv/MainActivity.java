package io.github.chujian596.app.ntv;

import android.app.AlertDialog;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * 原生录单系统：录单、结算、对账、复制全部本地完成，不依赖网页也不依赖网络。
 * 界面全部程序化生成，黑白灰，跟网页版视觉一致。
 */
public class MainActivity extends Activity {

    private Store store;
    private LinearLayout root;
    private ScrollView sv;
    private EditText inputBox;
    private TextView drawBox;
    private LinearLayout orderList;
    private TextView saveMsg;
    private TextView hkBar;
    private boolean hkBarShown;   // 本次点过获取就显示，不靠 24 小时判断
    private TextView orderCum2;
    private LinearLayout resultBox;
    private LinearLayout panelBox, panelRank, panelAi, panelFly, panelProfit, panelHist, panelPte;
    private LinearLayout copyBox, pteBox;
    private TextView simToggle;
    private Button bRank, bOrders;
    private String curPanel = "rank";
    private TextView summary;
    private TextView custPick;
    private TextView clockTxt;
    private TextView shopTxt;
    private TextView orderCum;
    private LinearLayout ballRow;
    private String curShop = "澳";   // 澳 / 港，保存后重启仍生效
    // custBox 已由顶部客户下拉替代
    private EditText capBox;
    private LinearLayout rankBox;
    private LinearLayout numBoxL;
    private LinearLayout numBoxR;
    private TextView boardSum;
    private LinearLayout splitBox;
    private LinearLayout simBox;
    private LinearLayout archBox;
    private Archive archive;
    private LinearLayout upBox;
    private LinearLayout riskBox;
    private LinearLayout custRow;
    private LinearLayout payListBox;
    private TextView payTotalTxt;

    private final int C_BG = 0xFFF7F7F7;
    private final int C_CARD = 0xFFFFFFFF;
    private final int C_LINE = 0xFFEEEEEE;
    private final int C_TXT = 0xFF222222;
    private final int C_SUB = 0xFF999999;
    private final int C_GREEN = 0xFF16A34A;
    private final int C_RED = 0xFFCF1322;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        store = new Store(this);
        curShop = store.shop();
        archive = new Archive(this);
        splitOldOrders();
        getWindow().setStatusBarColor(0xFFF7F7F7);
        // 状态栏/导航栏是浅底，必须把图标切成深色，否则时间电量白字看不见
        try {
            android.view.View dv = getWindow().getDecorView();
            int flags = dv.getSystemUiVisibility();
            if (android.os.Build.VERSION.SDK_INT >= 23) flags |= 0x00002000;      // LIGHT_STATUS_BAR
            if (android.os.Build.VERSION.SDK_INT >= 26) flags |= 0x00000010;      // LIGHT_NAVIGATION_BAR
            dv.setSystemUiVisibility(flags);
        } catch (Exception ignored) {}
        buildUI();
        refresh();
    }

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private TextView tv(String text, float size, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(size);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        return t;
    }

    private LinearLayout card() { return card(null); }

    private LinearLayout card(String tag) {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable cbg = new GradientDrawable();
        cbg.setColor(C_CARD);
        cbg.setCornerRadius(dp(8));
        l.setBackground(cbg);
        l.setPadding(dp(10), dp(8), dp(10), dp(8));
        l.setElevation(dp(1));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, 0, 0, dp(4));
        l.setLayoutParams(lp);
        if (tag != null) l.setTag(tag);
        return l;
    }

    private LinearLayout panel() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setVisibility(View.GONE);
        return l;
    }

    /** 只显示一个面板，其余收起 */
    private void setPanel(String key) {
        curPanel = key;
        if (panelBox != null) panelBox.setVisibility(View.VISIBLE);
        if (panelRank == null) return;
        panelRank.setVisibility(key.equals("rank") ? View.VISIBLE : View.GONE);
        panelAi.setVisibility(key.equals("ai") ? View.VISIBLE : View.GONE);
        panelFly.setVisibility(key.equals("fly") ? View.VISIBLE : View.GONE);
        panelProfit.setVisibility(key.equals("profit") ? View.VISIBLE : View.GONE);
        panelHist.setVisibility(key.equals("hist") ? View.VISIBLE : View.GONE);
        panelPte.setVisibility(key.equals("pte") ? View.VISIBLE : View.GONE);
        syncTabs(false);
    }

    /** 两个大按钮的选中态（专业版 .tab.active：黑底白字） */
    private void syncTabs(boolean ordersOpen) {
        styleTab(bRank, !ordersOpen);
        styleTab(bOrders, ordersOpen);
    }

    private void styleTab(Button b, boolean on) {
        if (b == null) return;
        GradientDrawable g = new GradientDrawable();
        // 专业版截图口径：选中＝浅灰底 + 深一点的边，不是黑底
        g.setColor(on ? 0xFFEFEFEF : 0xFFFFFFFF);
        g.setCornerRadius(dp(8));
        g.setStroke(dp(1), on ? 0xFFBBBBBB : 0xFFDDDDDD);
        b.setBackground(g);
        b.setTextColor(on ? 0xFF111111 : 0xFF666666);
    }

    /** 再点同一个按钮就收起（专业版那四个统计按钮本来就是开/关切换） */
    private void togglePanel(String key) {
        if (key.equals(curPanel) && panelBox != null && panelBox.getVisibility() == View.VISIBLE) {
            panelBox.setVisibility(View.GONE);
            curPanel = "";
            syncTabs(false);
            styleTab(bRank, false);
            return;
        }
        if (panelBox != null) panelBox.setVisibility(View.VISIBLE);
        setPanel(key);
    }

    /** 顶部两个大按钮：排行榜 / 订单记录，与专业版两个 tab 一致 */
    private void switchPanel(String key) {
        View ord = root == null ? null : root.findViewWithTag("orders");
        if (key.equals("orders")) {
            if (ord != null) {
                boolean show = ord.getVisibility() != View.VISIBLE;
                ord.setVisibility(show ? View.VISIBLE : View.GONE);
                syncTabs(show);
                if (show) scrollToTag("orders");
                else toast("订单记录已收起");
            }
            return;
        }
        if (ord != null) ord.setVisibility(View.GONE);
        syncTabs(false);
        if ("rank".equals(curPanel) && panelBox != null && panelBox.getVisibility() == View.VISIBLE) {
            panelBox.setVisibility(View.GONE);
            curPanel = "";
            toast("排行榜已收起");
            return;
        }
        setPanel("rank");
        refresh();
        scrollToTag("rankcard");
    }

    /** 阈值输入框：宽度按权重撑满、高度 42、白底圆角细边（专业版输入框同款） */
    /** 底部「功能设置 ▼」折叠条（专业版同位置同项） */
    private void buildFuncBar(LinearLayout root) {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.VERTICAL);
        bar.setPadding(0, dp(10), 0, dp(10));
        final TextView head = tv("功能设置 ▼", 11, C_SUB, false);
        head.setGravity(Gravity.CENTER);
        head.setTag("funcbar");
        final LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setVisibility(View.GONE);
        head.setOnClickListener(v -> {
            boolean show = body.getVisibility() != View.VISIBLE;
            body.setVisibility(show ? View.VISIBLE : View.GONE);
            head.setText(show ? "功能设置 ▲" : "功能设置 ▼");
        });
        bar.addView(head);

        String[][] rows = {{"导出统计CSV", "备份JSON", "导入备份"}, {"粘贴导入", "一键恢复上次备份"}, {"清空全部数据", "⚙ 设置"}};
        for (String[] r : rows) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(4), 0, 0);
            for (String label : r) {
                int fg = "一键恢复上次备份".equals(label) ? 0xFF16A34A
                        : "清空全部数据".equals(label) ? 0xFFCF1322 : 0xFF1F2329;
                Button b = tbtn(label, 13, 0xFFFFFFFF, 0xFFD9DDE3, fg, 8, true);
                b.setOnClickListener(v -> onFunc(label));
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(36), 1);
                lp.leftMargin = dp(3); lp.rightMargin = dp(3);
                b.setLayoutParams(lp);
                row.addView(b);
            }
            body.addView(row);
        }
        bar.addView(body);
        root.addView(bar);
    }

    private void onFunc(String label) {
        switch (label) {
            case "导出统计CSV": exportCsv(); break;
            case "备份JSON": backupJson(); break;
            case "导入备份": importDialog("导入备份"); break;
            case "粘贴导入": importDialog("粘贴导入备份"); break;
            case "一键恢复上次备份": restoreLastBackup(); break;
            case "清空全部数据": confirmClearAll(); break;
            case "⚙ 设置": openSettings(); break;
            default: break;
        }
    }

    private void exportCsv() {
        StringBuilder b = new StringBuilder("\ufeff序号,时间,客户,店铺,产品,金额\n");
        List<Order> list = store.todayOrders(curShop);
        int i = 1;
        double sum = 0;
        for (Order o : list) {
            String t = new java.text.SimpleDateFormat("HH:mm", java.util.Locale.CHINA).format(new java.util.Date(o.ts));
            b.append(i++).append(",").append(t).append(",").append(o.customer).append(",")
                    .append(o.shop).append(",\"").append(String.join(" ", o.codes)).append("\",")
                    .append(String.format("%.2f", o.amount())).append("\n");
            sum += o.amount();
        }
        b.append("合计,,,,,").append(String.format("%.2f", sum)).append("\n");
        String path = saveTextFile("统计" + dateStr() + ".csv", b.toString());
        copyText(b.toString());
        toast("CSV 已保存" + (path == null ? "" : "：" + path) + "\n内容也复制到剪贴板了");
    }

    private String dateStr() {
        return new java.text.SimpleDateFormat("yyyyMMdd_HHmm", java.util.Locale.CHINA).format(new java.util.Date());
    }

    /** 写到应用外部目录，返回路径；失败返回 null */
    private String saveTextFile(String name, String text) {
        try {
            java.io.File dir = getExternalFilesDir(null);
            if (dir == null) return null;
            java.io.File f = new java.io.File(dir, name);
            java.io.FileOutputStream fo = new java.io.FileOutputStream(f);
            fo.write(text.getBytes("UTF-8"));
            fo.close();
            return f.getAbsolutePath();
        } catch (Exception e) { return null; }
    }

    private void backupJson() {
        String data = store.backupText();
        store.sp().edit().putString("last_backup", data)
                .putString("last_backup_at", dateStr()).apply();
        saveTextFile("订单备份" + dateStr() + ".json", data);
        copyText(data);
        android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
        ad.setTitle("数据备份（共 " + store.todayOrders(curShop).size() + " 单）");
        ad.setMessage("已存到 app 内部（以后点绿色「一键恢复上次备份」直接找回），内容也复制到剪贴板了。");
        ad.setPositiveButton("知道了", null);
        ad.show();
    }

    private void importDialog(String title) {
        android.widget.EditText et = new android.widget.EditText(this);
        et.setTextSize(12);
        et.setMinLines(5);
        et.setGravity(Gravity.TOP);
        et.setHint("把备份内容粘进来（以 NTV-BACKUP 或 { 开头）");
        et.setBackgroundColor(0xFFF5F5F5);
        et.setPadding(dp(8), dp(8), dp(8), dp(8));
        android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
        ad.setTitle(title);
        ad.setView(et);
        ad.setPositiveButton("导入", (d, w) -> {
            String t = et.getText().toString();
            int n = store.restoreFromText(t);
            if (n < 0) { toast("导入失败：内容不是有效备份"); return; }
            refresh();
            toast("导入成功，共 " + n + " 单");
        });
        ad.setNegativeButton("取消", null);
        ad.show();
    }

    private void restoreLastBackup() {
        String raw = store.sp().getString("last_backup", "");
        if (raw == null || raw.isEmpty()) { toast("还没有可恢复的内部备份"); return; }
        String at = store.sp().getString("last_backup_at", "");
        android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
        ad.setMessage("将恢复最近一次「备份JSON」时存到 app 内部的备份" + (at.isEmpty() ? "" : "（" + at + "）") + "，继续？");
        ad.setPositiveButton("恢复", (d, w) -> {
            int n = store.restoreFromText(raw);
            if (n < 0) { toast("恢复失败：备份内容不完整"); return; }
            refresh();
            toast("已恢复 " + n + " 单");
        });
        ad.setNegativeButton("取消", null);
        ad.show();
    }

    private void confirmClearAll() {
        android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
        ad.setMessage("确定清空全部数据？不可恢复。建议先点「备份JSON」。");
        ad.setPositiveButton("全部清空", (d, w) -> {
            dismissCurDlg();
            store.sp().edit().clear().apply();
            if (saveMsg != null) { saveMsg.setText(""); saveMsg.setVisibility(View.GONE); }
            if (inputBox != null) inputBox.setText("");
            curShop = "澳";
            if (shopTxt != null) shopTxt.setText("澳门🇲🇴 ▾");
            refresh();
            toast("全部数据已清空");
        });
        ad.setNegativeButton("取消", null);
        ad.show();
    }

    private void openSettings() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(18), dp(6), dp(18), dp(6));
        box.addView(tv("版本 " + versionName(), 13, C_TXT, false));
        box.addView(tv("特码 47｜二中二 60｜三中二 20｜三中三 600", 12, C_SUB, false));
        box.addView(tv("连肖 二连4／三连10／四连30（含马减0.5）", 12, C_SUB, false));
        box.addView(tv("平特单肖倍数 " + Calc.fmt(store.pingteMult()), 12, C_SUB, false));
        TextView reset = tv("恢复默认阈值（特号100／平特0／连肖0）", 13, 0xFF1677FF, false);
        reset.setPadding(0, dp(12), 0, dp(6));
        final android.app.AlertDialog[] h = new android.app.AlertDialog[1];
        reset.setOnClickListener(v -> {
            store.setCap(100); store.setCapPte(0); store.setCapLx(0);
            refresh();
            if (h[0] != null) h[0].dismiss();
            toast("阈值已恢复默认");
        });
        box.addView(reset);
        TextView stats = tv("资料统计（9 个页签：杀肖/冷热/来源…）", 13, 0xFF1677FF, false);
        stats.setPadding(0, dp(6), 0, dp(6));
        stats.setOnClickListener(v -> {
            if (h[0] != null) h[0].dismiss();
            startActivity(new android.content.Intent(this, StatsActivity.class));
        });
        box.addView(stats);
        h[0] = new android.app.AlertDialog.Builder(this)
                .setTitle("设置")
                .setView(box)
                .setPositiveButton("完成", null)
                .create();
        curDlg = h[0];
        h[0].show();
    }

    private String versionName() {
        String v = null;
        try { v = getPackageManager().getPackageInfo(getPackageName(), 0).versionName; }
        catch (Exception ignored) {}
        return (v == null || v.trim().isEmpty()) ? "1.0" : v;
    }

    /** 递归关掉所有输入框的自动填充 */
    private void disableAutofill(View v) {
        if (v == null) return;
        if (v instanceof android.widget.EditText && android.os.Build.VERSION.SDK_INT >= 26) {
            ((android.widget.EditText) v).setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        }
        if (v instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) disableAutofill(g.getChildAt(i));
        }
    }

    private android.widget.EditText capInput(double v) {
        android.widget.EditText e = new android.widget.EditText(this);
        e.setText(v > 0 ? Calc.fmt(v) : "0");
        e.setTextSize(15);
        e.setSingleLine(true);
        e.setGravity(Gravity.CENTER_VERTICAL);
        e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(android.graphics.Color.WHITE);
        bg.setStroke(dp(1), 0xFFD9DDE3);
        bg.setCornerRadius(dp(6));
        e.setBackground(bg);
        e.setPadding(dp(8), 0, dp(8), 0);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(42), 1);
        lp.rightMargin = dp(10);
        e.setLayoutParams(lp);
        return e;
    }

    private LinearLayout labeled(String name, android.widget.EditText e) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        box.setLayoutParams(lp);
        box.addView(tv(name, 10, C_SUB, false));
        box.addView(e);
        return box;
    }

    private double parseNum(String s, double def) {
        try { return Double.parseDouble(s.trim()); } catch (Exception e) { return def; }
    }

    private Button btn(String text, View.OnClickListener cb) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(14);
        b.setTextColor(C_TXT);
        b.setAllCaps(false);
        b.setBackgroundColor(0xFFF2F2F2);
        b.setOnClickListener(cb);
        return b;
    }

    /** 专业版 .tab / .rank-btn 同款：白底或灰底、1px 细边、圆角、指定字号字重 */
    private Button tbtn(String text, float size, int bg, int border, int fg, float radius, boolean bold) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(size);
        b.setTextColor(fg);
        b.setAllCaps(false);
        if (bold) b.setTypeface(Typeface.DEFAULT_BOLD);
        GradientDrawable g = new GradientDrawable();
        g.setColor(bg);
        g.setCornerRadius(dp(radius));
        if (border != 0) g.setStroke(dp(1), border);
        b.setBackground(g);
        b.setPadding(0, 0, 0, 0);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        return b;
    }

    private void buildUI() {
        sv = new ScrollView(this);
        sv.setTag("scroll");
        sv.setBackgroundColor(C_BG);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(12), dp(12), dp(12), dp(24));
        sv.addView(root);
        setContentView(sv);
        // 关掉输入框的自动填充：有些机型/测试环境里 autofill 服务没起来会抛 NPE，
        // 表现就是点「清除订单」「保存」这类按钮没反应。
        disableAutofill(sv);

        // ---- 顶部汇总 ----
        LinearLayout head = card();
        LinearLayout hrow = new LinearLayout(this);
        hrow.setOrientation(LinearLayout.HORIZONTAL);
        hrow.setGravity(Gravity.CENTER_VERTICAL);
        summary = tv("", 12, C_TXT, false);
        summary.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        hrow.addView(summary);
        TextView ver = tv("v" + versionName(), 11, 0xFFBBBBBB, false);
        ver.setPadding(dp(8), dp(4), dp(4), dp(4));
        hrow.addView(ver);
        head.addView(hrow);
        root.addView(head);

        // ---- 客户 / 时钟 / 店铺 ----
        LinearLayout cust = card();
        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        row1.setGravity(Gravity.CENTER_VERTICAL);
        custPick = tv("客户：散客 ▾", 14, 0xFF333333, true);
        GradientDrawable cbg1 = new GradientDrawable();
        cbg1.setColor(0xFFF7F7F7);
        cbg1.setCornerRadius(dp(6));
        cbg1.setStroke(dp(1), 0xFFDDDDDD);
        custPick.setBackground(cbg1);
        custPick.setPadding(dp(12), dp(6), dp(12), dp(6));
        LinearLayout.LayoutParams clp0 = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        clp0.rightMargin = dp(6);
        custPick.setLayoutParams(clp0);
        custPick.setOnClickListener(v -> pickCustomer());
        row1.addView(custPick);
        clockTxt = tv("", 16, C_TXT, true);
        clockTxt.setGravity(Gravity.CENTER);
        clockTxt.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row1.addView(clockTxt);
        shopTxt = tv("澳门🇲🇴 ▾", 14, 0xFF333333, true);
        shopTxt.setTag("shop");
        GradientDrawable sbg0 = new GradientDrawable();
        sbg0.setColor(0xFFF7F7F7);
        sbg0.setCornerRadius(dp(6));
        sbg0.setStroke(dp(1), 0xFFDDDDDD);
        shopTxt.setBackground(sbg0);
        shopTxt.setPadding(dp(12), dp(6), dp(12), dp(6));
        shopTxt.setGravity(Gravity.END);
        shopTxt.setOnClickListener(v -> switchShop());
        row1.addView(shopTxt);
        cust.addView(row1);
        custRow = new LinearLayout(this);
        custRow.setOrientation(LinearLayout.HORIZONTAL);
        custRow.setPadding(0, dp(8), 0, 0);
        custRow.setVisibility(View.GONE);   // 专业版默认不显示，点客户才出名单
        cust.addView(custRow);
        root.addView(cust);


        // ---- 订单输入 ----
        LinearLayout in = card();
        LinearLayout itop = new LinearLayout(this);
        itop.setOrientation(LinearLayout.HORIZONTAL);
        itop.setGravity(Gravity.CENTER_VERTICAL);
        TextView it1 = tv("订单输入区", 12, 0xFF666666, false);
        itop.addView(it1);
        orderCum = tv("", 11, C_SUB, false);
        orderCum.setGravity(Gravity.END);
        orderCum.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        itop.addView(orderCum);
        in.addView(itop);

        ballRow = new LinearLayout(this);
        ballRow.setOrientation(LinearLayout.HORIZONTAL);
        ballRow.setGravity(Gravity.CENTER);
        ballRow.setPadding(0, dp(10), 0, dp(10));
        in.addView(ballRow);

        inputBox = new EditText(this);
        inputBox.setTag("input");
        inputBox.setHint("输入订单");
        inputBox.setTextSize(14);
        inputBox.setGravity(Gravity.TOP);
        GradientDrawable inbg = new GradientDrawable();
        inbg.setColor(0xFFFFFFFF);
        inbg.setCornerRadius(dp(6));
        inbg.setStroke(dp(1), 0xFFE0E0E0);
        inputBox.setBackground(inbg);
        inputBox.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        inputBox.setPadding(dp(10), dp(8), dp(10), dp(8));
        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(100));
        ilp.topMargin = dp(2);
        inputBox.setLayoutParams(ilp);
        in.addView(inputBox);

        // 开奖行
        LinearLayout drawRow = new LinearLayout(this);
        drawRow.setOrientation(LinearLayout.HORIZONTAL);
        drawRow.setGravity(Gravity.CENTER_VERTICAL);
        drawRow.setPadding(0, dp(8), 0, 0);
        drawBox = tv("", 11, C_SUB, false);
        drawBox.setTag("draw");
        Draw d = store.draw(curShop);
        drawBox.setText(d.period > 0 ? drawLine(d) : "未获取开奖数据");
        drawBox.setPadding(dp(6), 0, dp(6), 0);
        drawBox.setGravity(Gravity.CENTER_VERTICAL);
        drawBox.setLayoutParams(new LinearLayout.LayoutParams(0, dp(40), 1));
        drawBox.setOnClickListener(v -> doDraw());
        drawRow.addView(drawBox);
        Button drRefresh = btn("刷新", v -> autoFetch());
        drRefresh.setTextSize(12);
        drRefresh.setPadding(dp(6), 0, dp(6), 0);
        drRefresh.setMinWidth(0);
        drRefresh.setMinimumWidth(0);
        drRefresh.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40)));
        LinearLayout.LayoutParams rflp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        rflp.leftMargin = dp(6);
        drawRow.addView(drRefresh, rflp);
        Button drAuto = btn("自动获取开奖", v -> autoFetch());
        drAuto.setTextSize(12);
        drAuto.setPadding(dp(6), 0, dp(6), 0);
        drAuto.setMinWidth(0);
        drAuto.setMinimumWidth(0);
        drAuto.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40)));
        drawRow.addView(drAuto);
        in.addView(drawRow);

        // 香港开奖条（专业版 hkDrawBar：只有香港单才出现，浅黄底橙字 11px）
        hkBar = new TextView(this);
        hkBar.setTag("hkdraw");
        hkBar.setTextSize(11);
        hkBar.setTextColor(0xFFB45309);
        hkBar.setLineSpacing(0, 1.5f);
        hkBar.setPadding(dp(6), dp(4), dp(6), dp(4));
        GradientDrawable hkbg = new GradientDrawable();
        hkbg.setColor(0xFFFFFBE6);
        hkbg.setCornerRadius(dp(6));
        hkbg.setStroke(dp(1), 0xFFF0C36D);
        hkBar.setBackground(hkbg);
        LinearLayout.LayoutParams hklp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hklp.topMargin = dp(4);
        hkBar.setLayoutParams(hklp);
        hkBar.setVisibility(View.GONE);
        in.addView(hkBar);

        LinearLayout brow = new LinearLayout(this);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, dp(8), 0, 0);
        Button save = tbtn("保存", 12, 0xFFFFFFFF, 0xFFD9DDE3, 0xFF1F2329, 8, true);
        save.setOnClickListener(v -> doSave());
        Button manual = tbtn("手动录入", 12, 0xFFFFFFFF, 0xFF1A1A1A, 0xFF1A1A1A, 8, true);
        manual.setOnClickListener(v -> doDraw());
        Button clear = tbtn("清空", 12, 0xFFFFFFFF, 0xFFD9DDE3, 0xFF1F2329, 8, true);
        clear.setOnClickListener(v -> {
            inputBox.setText("");
            // 与专业版 clearInput 一致：输入框和「本次已保存」一起清
            if (saveMsg != null) { saveMsg.setText(""); saveMsg.setVisibility(View.GONE); }
        });
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(0, dp(32), 1);
        blp.rightMargin = dp(6);
        save.setLayoutParams(blp);
        manual.setLayoutParams(blp);
        clear.setLayoutParams(new LinearLayout.LayoutParams(0, dp(32), 1));
        brow.addView(save);
        brow.addView(manual);
        brow.addView(clear);
        in.addView(brow);

        // 保存结果（专业版 saveMsg：本次已保存哪几笔 + 合计）
        saveMsg = tv("", 15, C_TXT, false);
        saveMsg.setTag("savemsg");
        saveMsg.setPadding(0, dp(8), 0, 0);
        saveMsg.setVisibility(View.GONE);
        in.addView(saveMsg);
        root.addView(in);

        // ---- 已录入（紧贴输入区下方，与专业版一致）----
        LinearLayout ol = card("orders");
        LinearLayout olTop = new LinearLayout(this);
        olTop.setOrientation(LinearLayout.HORIZONTAL);
        olTop.setGravity(Gravity.CENTER_VERTICAL);
        olTop.addView(tv("已录入", 15, C_TXT, true));
        orderCum2 = tv("", 12, C_SUB, false);
        orderCum2.setGravity(Gravity.END);
        orderCum2.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        olTop.addView(orderCum2);
        ol.addView(olTop);
        orderList = new LinearLayout(this);
        orderList.setOrientation(LinearLayout.VERTICAL);
        orderList.setPadding(0, dp(6), 0, 0);
        ol.addView(orderList);
        LinearLayout olAct = new LinearLayout(this);
        olAct.setOrientation(LinearLayout.HORIZONTAL);
        olAct.setPadding(0, dp(8), 0, 0);
        Button undoLast = btn("撤销上一单", v -> undoLastOrder());
        Button archBtn = btn("归档并清空", v -> doArchive());
        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        alp.rightMargin = dp(6);
        undoLast.setLayoutParams(alp);
        archBtn.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        olAct.addView(undoLast);
        olAct.addView(archBtn);
        ol.addView(olAct);
        root.addView(ol);

        // ---- 两个大按钮（对应专业版 ↑ 排行榜 / 订单记录 两个 tab）----
        LinearLayout bigRow = new LinearLayout(this);
        bigRow.setOrientation(LinearLayout.HORIZONTAL);
        bigRow.setPadding(0, 0, 0, dp(10));
        LinearLayout.LayoutParams bigLp = new LinearLayout.LayoutParams(0, dp(52), 1);
        bigLp.rightMargin = dp(6);
        bRank = tbtn("排行榜", 13, 0xFF333333, 0xFF333333, 0xFFFFFFFF, 8, true);
        bRank.setOnClickListener(v -> switchPanel("rank"));
        bRank.setLayoutParams(bigLp);
        bOrders = tbtn("订单记录", 13, 0xFFF5F5F5, 0xFFDDDDDD, 0xFF666666, 8, true);
        bOrders.setOnClickListener(v -> switchPanel("orders"));
        bOrders.setLayoutParams(new LinearLayout.LayoutParams(0, dp(52), 1));
        bigRow.addView(bRank);
        bigRow.addView(bOrders);
        root.addView(bigRow);

        // ---- 排行榜卡：8 个按钮 + 内容都在这一张卡里（与专业版一致）----
        LinearLayout rankCard = card("rankcard");
        String[][] cells = {
                {"排行榜", "rank"}, {"今日归档", "arch"}, {"历史订单", "hist"}, {"清除订单", "clear"},
                {"AI统计", "ai"}, {"飞单统计", "fly"}, {"盈利统计", "profit"}, {"平特肖", "pte"}
        };
        for (int i = 0; i < cells.length; i += 4) {
            LinearLayout gr = new LinearLayout(this);
            gr.setOrientation(LinearLayout.HORIZONTAL);
            if (i > 0) gr.setPadding(0, dp(8), 0, 0);
            for (int j = i; j < i + 4; j++) {
                final String key = cells[j][1];
                Button gb = tbtn(cells[j][0], 13, 0xFFFFFFFF, 0xFFCCCCCC, 0xFF333333, 6, true);
                gb.setOnClickListener(v -> onGrid(key));
                LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(0, dp(46), 1);
                if (j < i + 3) glp.rightMargin = dp(6);
                gb.setLayoutParams(glp);
                gr.addView(gb);
            }
            rankCard.addView(gr);
        }

        // 内容容器：各面板叠在同一处，只显示一个
        panelBox = new LinearLayout(this);
        panelBox.setOrientation(LinearLayout.VERTICAL);
        panelBox.setPadding(0, dp(10), 0, 0);

        // 面板1 排行榜（49 号两列表）
        panelRank = panel();
        panelRank.setTag("panel-rank");
        LinearLayout capRow = new LinearLayout(this);
        capRow.setOrientation(LinearLayout.HORIZONTAL);
        capRow.setGravity(Gravity.CENTER_VERTICAL);
        capRow.addView(tv("每号最多自留", 13, C_SUB, false));
        capBox = new EditText(this);
        capBox.setSingleLine(true);
        capBox.setTextSize(14);
        capBox.setInputType(InputType.TYPE_CLASS_NUMBER);
        capBox.setText(String.valueOf((int) store.cap()));
        LinearLayout.LayoutParams cplp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        cplp.leftMargin = dp(8);
        capBox.setLayoutParams(cplp);
        capRow.addView(capBox);
        capRow.addView(btn("重算", v -> {
            try { store.setCap(Double.parseDouble(capBox.getText().toString().trim())); } catch (Exception ignored) {}
            refresh();
        }));
        panelRank.addView(capRow);

        boardSum = tv("", 12, C_TXT, true);
        boardSum.setPadding(0, dp(8), 0, dp(4));
        panelRank.addView(boardSum);

        LinearLayout twoCol = new LinearLayout(this);
        twoCol.setOrientation(LinearLayout.HORIZONTAL);
        twoCol.setPadding(0, dp(4), 0, 0);
        numBoxL = new LinearLayout(this);
        numBoxL.setOrientation(LinearLayout.VERTICAL);
        numBoxR = new LinearLayout(this);
        numBoxR.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams colLp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        colLp.rightMargin = dp(8);
        numBoxL.setLayoutParams(colLp);
        numBoxR.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        twoCol.addView(numBoxL);
        twoCol.addView(numBoxR);
        panelRank.addView(twoCol);
        rankBox = new LinearLayout(this);
        rankBox.setOrientation(LinearLayout.VERTICAL);

        // 面板2 AI统计（风控 + 补号模拟，补号模拟折叠在下面，与专业版一致）
        panelAi = panel();
        panelAi.setTag("panel-ai");
        riskBox = new LinearLayout(this);
        riskBox.setOrientation(LinearLayout.VERTICAL);
        panelAi.addView(riskBox);
        // 补号模拟由 renderSimBody 在 AI统计 里生成（与专业版一致）

        // 面板3 飞单统计
        panelFly = panel();
        panelFly.setTag("panel-fly");
        splitBox = new LinearLayout(this);
        splitBox.setOrientation(LinearLayout.VERTICAL);
        panelFly.addView(splitBox);
        upBox = new LinearLayout(this);
        upBox.setOrientation(LinearLayout.VERTICAL);
        upBox.setPadding(0, dp(10), 0, 0);
        panelFly.addView(upBox);
        copyBox = new LinearLayout(this);
        copyBox.setOrientation(LinearLayout.VERTICAL);
        copyBox.setPadding(0, dp(10), 0, 0);
        panelFly.addView(copyBox);

        // 面板4 盈利统计
        panelProfit = panel();
        panelProfit.setTag("panel-profit");
        resultBox = new LinearLayout(this);
        resultBox.setOrientation(LinearLayout.VERTICAL);
        panelProfit.addView(resultBox);

        // 面板5 历史订单
        panelHist = panel();
        panelHist.setTag("panel-hist");
        archBox = new LinearLayout(this);
        archBox.setOrientation(LinearLayout.VERTICAL);
        panelHist.addView(archBox);

        // 面板6 平特肖
        panelPte = panel();
        panelPte.setTag("panel-pte");
        pteBox = new LinearLayout(this);
        pteBox.setOrientation(LinearLayout.VERTICAL);
        panelPte.addView(pteBox);

        panelBox.addView(panelRank);
        panelBox.addView(panelAi);
        panelBox.addView(panelFly);
        panelBox.addView(panelProfit);
        panelBox.addView(panelHist);
        panelBox.addView(panelPte);
        rankCard.addView(panelBox);
        root.addView(rankCard);
        setPanel("rank");

        // ---- 设置 ----
        LinearLayout cfg = card("cfg");
        cfg.addView(tv("设置", 15, C_TXT, true));

        LinearLayout ptRow = new LinearLayout(this);
        ptRow.setOrientation(LinearLayout.HORIZONTAL);
        ptRow.setGravity(Gravity.CENTER_VERTICAL);
        ptRow.setPadding(0, dp(6), 0, 0);
        ptRow.addView(tv("平特单肖倍数", 13, C_SUB, false));
        EditText ptBox = new EditText(this);
        ptBox.setSingleLine(true);
        ptBox.setTextSize(14);
        ptBox.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        ptBox.setText(Calc.fmt(store.pingteMult()));
        LinearLayout.LayoutParams plp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        plp.leftMargin = dp(8);
        ptBox.setLayoutParams(plp);
        ptRow.addView(ptBox);
        ptRow.addView(btn("保存设置", v -> {
            try {
                double m = Double.parseDouble(ptBox.getText().toString().trim());
                if (m <= 0) { toast("倍数要大于 0"); return; }
                store.setPingteMult(m);
                refresh();
                toast("已改为 " + Calc.fmt(m));
            } catch (Exception e) { toast("填数字"); }
        }));
        cfg.addView(ptRow);
        cfg.addView(tv("特码固定 47，二中二 60，三中二 20，三中三 600，连肖 二连4/三连10/四连30（含马减0.5）", 11, C_SUB, false));

        LinearLayout cfgBtns = new LinearLayout(this);
        cfgBtns.setOrientation(LinearLayout.HORIZONTAL);
        cfgBtns.setPadding(0, dp(8), 0, 0);
        Button bClear = btn("清空今日", v -> {
            store.saveOrders(new ArrayList<Order>());
            refresh();
            toast("今日订单已清空");
        });
        Button bCum = btn("清空累计", v -> {
            store.clearUpCum();
            refresh();
            toast("上家累计已归零");
        });
        bClear.setLayoutParams(blp2());
        bCum.setLayoutParams(blp2());
        cfgBtns.addView(bClear);
        cfgBtns.addView(bCum);
        cfg.addView(cfgBtns);

        LinearLayout bakRow = new LinearLayout(this);
        bakRow.setOrientation(LinearLayout.HORIZONTAL);
        bakRow.setPadding(0, dp(8), 0, 0);
        Button bExp = btn("导出备份", v -> copyText(store.backupText()));
        Button bImp = btn("从剪贴板恢复", v -> doRestore());
        bExp.setLayoutParams(blp2());
        bImp.setLayoutParams(blp2());
        bakRow.addView(bExp);
        bakRow.addView(bImp);
        cfg.addView(bakRow);
        cfg.addView(tv("导出会把全部订单和设置变成一段文字放到剪贴板，存到微信收藏或备忘录即可", 11, C_SUB, false));

        LinearLayout undoRow = new LinearLayout(this);
        undoRow.setOrientation(LinearLayout.HORIZONTAL);
        undoRow.setPadding(0, dp(8), 0, 0);
        Button bUndoDraw = btn("撤销开奖记录", v -> {
            store.clearDraw(curShop);
            refresh();
            toast((curShop.equals("澳") ? "澳门" : "香港") + "开奖已撤销");
        });
        Button bHkCopy = btn("复制香港单", v -> copyText(hkText()));
        bUndoDraw.setLayoutParams(blp2());
        bHkCopy.setLayoutParams(blp2());
        undoRow.addView(bUndoDraw);
        undoRow.addView(bHkCopy);
        cfg.addView(undoRow);
        // 资料统计入口（专业版是独立 stats.html，这里直接打开同一页）
        Button bStats = btn("资料统计", v -> startActivity(new android.content.Intent(this, StatsActivity.class)));
        bStats.setLayoutParams(blp2());
        LinearLayout statsRow = new LinearLayout(this);
        statsRow.setOrientation(LinearLayout.HORIZONTAL);
        statsRow.setPadding(0, dp(8), 0, 0);
        statsRow.addView(bStats);
        cfg.addView(statsRow);
        root.addView(cfg);

        // ---- 赔付记录 ----
        LinearLayout payCard = card("pays");
        LinearLayout payHead = new LinearLayout(this);
        payHead.setOrientation(LinearLayout.HORIZONTAL);
        payHead.setGravity(Gravity.CENTER_VERTICAL);
        payHead.addView(tv("赔付记录", 15, C_TXT, true));
        payTotalTxt = tv("", 13, C_SUB, false);
        payTotalTxt.setGravity(Gravity.END);
        payTotalTxt.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        payHead.addView(payTotalTxt);
        payCard.addView(payHead);
        payListBox = new LinearLayout(this);
        payListBox.setOrientation(LinearLayout.VERTICAL);
        payListBox.setPadding(0, dp(6), 0, 0);
        payCard.addView(payListBox);
        payCard.addView(btn("清空赔付记录", v -> {
            store.clearPays();
            refresh();
            toast("赔付记录已清空");
        }));
        root.addView(payCard);

        // ---- 复制（并入订单记录卡，专业版就在这里放「复制汇总」）----
        LinearLayout cp = (LinearLayout) root.findViewWithTag("orders");
        if (cp == null) cp = card();
        LinearLayout cr = new LinearLayout(this);
        cr.setOrientation(LinearLayout.HORIZONTAL);
        cr.setPadding(0, dp(8), 0, 0);
        Button cc = tbtn("复制客户单", 12, 0xFFFFFFFF, 0xFFD9DDE3, 0xFF1F2329, 8, true);
        cc.setOnClickListener(v -> copyText(custText()));
        Button cu = tbtn("复制上家单", 12, 0xFFFFFFFF, 0xFFD9DDE3, 0xFF1F2329, 8, true);
        cu.setOnClickListener(v -> copyText(upText()));
        LinearLayout.LayoutParams cp1 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        cp1.rightMargin = dp(8);
        cc.setLayoutParams(cp1);
        cu.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        cr.addView(cc);
        cr.addView(cu);
        cp.addView(cr);

        // 面板默认收起，点按钮展开（与专业版一致）
        for (String t : new String[]{"orders", "cfg", "pays"}) {
            View v = root.findViewWithTag(t);
            if (v != null) v.setVisibility(View.GONE);
        }
        // 底部「功能设置」条（专业版固定在页面最下方）
        buildFuncBar(root);
    }

    private LinearLayout.LayoutParams blp2() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        lp.rightMargin = dp(8);
        return lp;
    }

    /** 跟专业版一致：期320 特20 14 17 32 34 24 46 20 */
    private String drawLine(Draw d) {
        StringBuilder b = new StringBuilder();
        b.append("期").append(d.period).append(" 特").append(String.format("%02d", d.special)).append(" ");
        for (int n : d.regular) b.append(String.format("%02d ", n));
        b.append(String.format("%02d", d.special));
        return b.toString();
    }

    // ---------- 动作 ----------

    private void doSave() {
        doSave(inputBox.getText().toString());
    }

    /** 属性玩法没写「各」时，照专业版弹窗问：总额摊号 还是 各号 */
    private void askWave(String line, String[] w, String allText) {
        String attr = w[0];
        double amt;
        try { amt = Double.parseDouble(w[1]); } catch (Exception e) { return; }
        int cnt = Parse.linkCount(attr);
        if (cnt <= 0) return;
        String perEach = String.format("%.1f", amt / cnt);
        String[] opts = new String[]{
                "总额" + Calc.fmt(amt) + "（摊到" + cnt + "号，每个" + perEach + "元）",
                "各号" + Calc.fmt(amt) + "（" + cnt + "号×" + Calc.fmt(amt) + "=" + Calc.fmt(amt * cnt) + "元）",
                "取消"
        };
        dismissCurDlg();
        curDlg = new AlertDialog.Builder(this)
                .setTitle("请选择注单方式")
                .setMessage(attr + " " + Calc.fmt(amt) + "元（" + cnt + "个号）")
                .setItems(opts, (d, i) -> {
                    if (i == 2) return;
                    String newLine = (i == 0)
                            ? attr + "各" + String.format("%.4f", amt / cnt)
                            : attr + "各" + w[1];
                    String replaced = allText.replace(line, newLine);
                    doSave(replaced);
                })
                .create();
        curDlg.show();
    }

    private void dismissCurDlg() {
        try { if (curDlg != null && curDlg.isShowing()) curDlg.dismiss(); } catch (Exception ignored) {}
        curDlg = null;
    }

    /** 多项歧义：一个框里每项二选一（共X / 每号X），全选完点确定 —— 对应专业版 showMultiDlg */
    private void askMulti(java.util.List<String[]> items, final String all) {
        final int[] pick = new int[items.size()];
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(18), dp(4), dp(18), dp(4));
        box.addView(tv("这个订单有 " + items.size() + " 项要选", 15, C_TXT, true));
        box.addView(tv("每项选一个，全选完点确定", 12, C_SUB, false));
        for (int i = 0; i < items.size(); i++) {
            String attr = items.get(i)[1];
            double amt = 0;
            try { amt = Double.parseDouble(items.get(i)[2]); } catch (Exception ignored) {}
            int cnt = Parse.linkCount(attr);
            if (cnt <= 0) continue;
            LinearLayout blk = new LinearLayout(this);
            blk.setOrientation(LinearLayout.VERTICAL);
            blk.setPadding(0, dp(10), 0, dp(2));
            blk.addView(tv(attr + " " + Calc.fmt(amt) + "元（" + cnt + "个号）", 12, C_SUB, false));
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            final int idx = i;
            final Button ba = btn("共" + Calc.fmt(amt) + "（每号" + String.format("%.1f", amt / cnt) + "）", v -> {
                pick[idx] = 1;
                ((Button) v).setText("✓ " + ((Button) v).getText().toString().replace("✓ ", ""));
            });
            final Button bb = btn("每号" + Calc.fmt(amt) + "（共" + Calc.fmt(amt * cnt) + "）", v -> {
                pick[idx] = 2;
                ((Button) v).setText("✓ " + ((Button) v).getText().toString().replace("✓ ", ""));
            });
            LinearLayout.LayoutParams lp1 = new LinearLayout.LayoutParams(0, dp(44), 1);
            lp1.rightMargin = dp(6);
            ba.setLayoutParams(lp1);
            bb.setLayoutParams(new LinearLayout.LayoutParams(0, dp(44), 1));
            ba.setTextSize(12);
            bb.setTextSize(12);
            row.addView(ba);
            row.addView(bb);
            blk.addView(row);
            box.addView(blk);
        }
        ScrollView sc = new ScrollView(this);
        sc.addView(box);
        final AlertDialog dlg = new AlertDialog.Builder(this)
                .setView(sc)
                .setPositiveButton("确定", null)
                .setNegativeButton("取消", null)
                .create();
        dlg.setOnShowListener(x -> dlg.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            for (int i = 0; i < items.size(); i++) if (pick[i] == 0) { toast("还有项没选"); return; }
            String text = all;
            for (int i = 0; i < items.size(); i++) {
                String[] it = items.get(i);
                int cnt = Parse.linkCount(it[1]);
                double amt = 0;
                try { amt = Double.parseDouble(it[2]); } catch (Exception ignored) {}
                String newLine = pick[i] == 1
                        ? it[1] + "各" + String.format("%.4f", amt / cnt)
                        : it[1] + "各" + it[2];
                text = text.replace(it[0], newLine);
            }
            dlg.dismiss();
            curDlg = null;
            doSave(text);
        }));
        curDlg = dlg;
        dlg.show();
    }

    private void doSave(String all) {
        // 客户名由顶部客户下拉维护，这里不再读输入框
        if (all.trim().isEmpty()) { toast("先输入订单"); return; }
        all = autoFixBareZodiac(all);
        java.util.List<String[]> amb = new java.util.ArrayList<>();
        for (String line : splitLines(all)) {
            String[] w = Parse.detectWave(line);
            if (w != null) amb.add(new String[]{line, w[0], w[1]});
        }
        // 一项：三选项单框；多项：一次性全选完（与专业版两种形态一致）
        if (amb.size() == 1) { askWave(amb.get(0)[0], new String[]{amb.get(0)[1], amb.get(0)[2]}, all); return; }
        if (amb.size() > 1) { askMulti(amb, all); return; }
        // 生肖歧义：先一次问完所有没写玩法的生肖，再整批存（专业版整批没存完不落库）
        java.util.List<String> ambs = Parse.findAmbigZodiacs(all);
        if (!ambs.isEmpty()) {
            askAmbigNext(all, ambs, 0, new java.util.LinkedHashMap<String, String>());
            return;
        }
        doSaveCore(all, null);
    }

    /**
     * 专业版 doSave 的预处理：两个以上生肖连写、后面跟「各/各数/各号 + 金额」时，
     * 自动当成特肖（前面补「特」），不弹窗。单肖才弹窗问。
     */
    private String autoFixBareZodiac(String text) {
        if (text == null) return "";
        StringBuilder out = new StringBuilder();
        String[] lines = text.split("\n");
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (i > 0) out.append("\n");
            if (line.isEmpty()) continue;
            if (line.matches("^[马蛇龙兔虎牛鼠猪狗鸡猴羊]{2,}\\s*各\\s*(?:号|数)?\\s*[0-9].*")) {
                line = "特" + line;
            }
            out.append(line);
        }
        return out.toString();
    }

    /** 逐个问完所有未定生肖，全部选好再一次性保存整批 */
    private void askAmbigNext(final String all, final java.util.List<String> ambs,
                              final int idx, final java.util.LinkedHashMap<String, String> map) {
        if (idx >= ambs.size()) { doSaveCore(all, map); return; }
        final String zs = ambs.get(idx);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(18), dp(4), dp(18), dp(4));
        String[] opts = new String[]{"特肖：买该肖全部特号", "平特：买该肖平特", "连肖：买这几个肖连肖"};
        final android.app.AlertDialog[] holder = new android.app.AlertDialog[1];
        for (int i = 0; i < 3; i++) {
            final int which = i;
            TextView b = new TextView(this);
            b.setText(opts[i]);
            b.setTextSize(15);
            b.setTextColor(0xFF1677FF);
            b.setGravity(Gravity.CENTER_VERTICAL);
            b.setPadding(0, dp(14), 0, dp(14));
            b.setOnClickListener(v -> {
                map.put(zs, which == 0 ? "特" : (which == 1 ? "平特" : "连肖"));
                if (holder[0] != null) holder[0].dismiss();
                askAmbigNext(all, ambs, idx + 1, map);
            });
            box.addView(b);
            View div = new View(this);
            div.setBackgroundColor(0xFFEEEEEE);
            box.addView(div, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        }
        TextView cancel = new TextView(this);
        cancel.setText("重新编辑");
        cancel.setTextSize(14);
        cancel.setTextColor(0xFF888888);
        cancel.setGravity(Gravity.END);
        cancel.setPadding(0, dp(12), 0, dp(12));
        cancel.setOnClickListener(v -> { if (holder[0] != null) holder[0].dismiss(); });
        box.addView(cancel);
        if (curDlg != null && curDlg.isShowing()) curDlg.dismiss();
        dismissCurDlg();
        holder[0] = new android.app.AlertDialog.Builder(this)
                .setTitle("「" + zs + "」怎么录？")
                .setMessage("没写平/特/连，这" + zs.length() + "个生肖按哪种产品？点一下就存好。")
                .setView(box)
                .create();
        curDlg = holder[0];
        holder[0].show();
    }

    /** 整批解析入账；prefixes 为生肖歧义的选择（zs → 特/平特/连肖） */
    private void doSaveCore(String all, java.util.Map<String, String> prefixes) {
        List<String> lines = splitLines(all);
        int ok = 0;
        List<String> bad = new ArrayList<>();
        List<Order> saved = new ArrayList<>();
        double lastPrice = -1;
        for (String line : lines) {
            String fixed = line;
            if (prefixes != null) {
                for (String zs : prefixes.keySet()) {
                    fixed = fixed.replaceFirst("(^|[^特平连])" + zs, "$1" + prefixes.get(zs) + zs);
                }
            }
            try {
                Order o = Parse.parseLine(fixed);
                if (o == null) continue;
                o.customer = store.customer();
                o.shop = curShop;
                store.addOrder(o);
                saved.add(o);
                lastPrice = o.price;
                ok++;
            } catch (Exception e) {
                // 与专业版一致：这行没写价格时，沿用上一行价格再试一次
                if (lastPrice > 0 && e.getMessage() != null && e.getMessage().contains("没找到价格")) {
                    try {
                        Order o2 = Parse.parseLine(fixed + " 各" + Calc.fmt(lastPrice));
                        if (o2 != null) {
                            o2.customer = store.customer();
                            o2.shop = curShop;
                            store.addOrder(o2);
                            saved.add(o2);
                            ok++;
                            continue;
                        }
                    } catch (Exception ignored) {}
                }
                bad.add(line + " → " + e.getMessage());
            }
        }
        inputBox.setText("");
        refresh();
        showSaved(saved, bad);
        if (!bad.isEmpty()) {
            toast("保存 " + ok + " 笔，失败 " + bad.size() + " 行\n" + bad.get(0));
        } else {
            toast("已保存 " + ok + " 笔");
        }
    }

    /** 保存后回显本次录了什么（对应专业版「本次已保存：每笔 + 合计」） */
    private void showSaved(java.util.List<Order> saved, java.util.List<String> badLines) {
        if (saved.isEmpty() && badLines.isEmpty()) return;
        // 与专业版同一套回显：特号只写一次前缀、号码空格分隔、× 单价 = 金额.00元，合计加粗
        StringBuilder b = new StringBuilder("本次已保存：");
        double sum = 0;
        java.util.List<Order> merged = new java.util.ArrayList<>();
        for (Order o : saved) {
            sum += o.amount();
            if (!merged.isEmpty()) {
                Order prev = merged.get(merged.size() - 1);
                if (prev.codes.size() == 1 && o.codes.size() == 1
                        && Math.abs(prev.price - o.price) < 0.001 && prev.codes.get(0).matches("\\d{2}")
                        && o.codes.get(0).matches("\\d{2}")) {
                    merged.add(o);
                    continue;
                }
            }
            merged.add(o);
        }
        int i = 0;
        while (i < merged.size()) {
            Order o = merged.get(i);
            if (o.codes.size() == 1 && o.codes.get(0).matches("\\d{2}")) {
                int j = i;
                while (j + 1 < merged.size() && merged.get(j + 1).codes.size() == 1
                        && Math.abs(merged.get(j + 1).price - o.price) < 0.001) j++;
                int cnt = j - i + 1;
                if (cnt >= 6) {
                    b.append("\n").append(cnt).append("个号 每号").append(Calc.fmt(o.price))
                            .append(" = ").append(String.format("%.2f", cnt * o.price)).append("元");
                } else {
                    for (int k = i; k <= j; k++) b.append("\n").append(orderLine(merged.get(k)));
                }
                i = j + 1;
                continue;
            }
            b.append("\n").append(orderLine(o));
            i++;
        }
        b.append("\n合计");
        b.append(String.format("%.2f", sum)).append("元");
        if (!badLines.isEmpty()) b.append("\n没能录入：").append(badLines.size()).append(" 行（").append(badLines.get(0)).append("）");
        android.text.SpannableString ss = new android.text.SpannableString(b.toString());
        int st = b.lastIndexOf("合计");
        if (st >= 0 && badLines.isEmpty()) {
            ss.setSpan(new android.text.style.StyleSpan(android.graphics.Typeface.BOLD), st, b.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            ss.setSpan(new android.text.style.RelativeSizeSpan(1.15f), st, b.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        saveMsg.setText(ss);
        saveMsg.setTextColor(badLines.isEmpty() ? C_TXT : 0xFFB45309);
        saveMsg.setVisibility(View.VISIBLE);
    }

    /** 单行回显（专业版 display）：特号前缀只写一次，平特/连肖代码自带产品名 */
    private String orderLine(Order o) {
        if (o.codes.isEmpty()) return "";
        String c0 = o.codes.get(0);
        if (c0.contains(":")) {
            String prod = c0.substring(0, c0.indexOf(':'));
            return prod + "(" + o.codes.size() + "组) 每组" + Calc.fmt(o.price) + "元 = "
                    + String.format("%.2f", o.amount()) + "元";
        }
        String label = (c0.startsWith("平特") || c0.startsWith("连肖")) ? "" : "特号 ";
        return label + String.join(" ", o.codes) + (o.isPer ? " × " : " = ")
                + Calc.fmt(o.price) + " = " + String.format("%.2f", o.amount()) + "元";
    }

    /** 撤销上一单（专业版的「撤销上一条订单」） */
    private void undoLastOrder() {
        List<Order> t = store.todayOrders();
        if (t.isEmpty()) { toast("没有可撤销的订单"); return; }
        Order last = t.get(0);
        store.removeOrder(last.id);
        refresh();
        saveMsg.setVisibility(View.GONE);
        toast("已撤销：" + last.customer + " " + Calc.fmt(last.amount()) + " 元");
    }

    private List<String> splitLines(String s) {
        List<String> out = new ArrayList<>();
        for (String line : s.split("\n")) {
            String t = line.trim();
            if (!t.isEmpty()) out.add(t);
        }
        return out;
    }

    private void doDraw() {
        final EditText et = new EditText(this);
        et.setSingleLine(false);
        et.setHint("例：320 05 14 17 32 34 24 + 20");
        Draw cur = store.draw(curShop);
        if (cur.period > 0) et.setText(drawLine(cur));
        new android.app.AlertDialog.Builder(this)
                .setTitle("录入开奖")
                .setMessage("格式：期号 六个号码，最后一个是特码")
                .setView(et)
                .setPositiveButton("保存并结算", (d, w) -> applyDraw(et.getText().toString()))
                .setNegativeButton("取消", null)
                .show();
    }

    private void applyDraw(String t) {
        if (t == null || t.trim().isEmpty()) { toast("先填开奖"); return; }
        String norm = t.replaceAll("[\\s,，、]+", ",").replace("+", ",").replace("期", "");
        String[] parts = norm.split(",");
        List<Integer> nums = new ArrayList<>();
        int period = 0;
        for (String p : parts) {
            if (p.isEmpty()) continue;
            try {
                int n = Integer.parseInt(p);
                if (nums.isEmpty() && n > 49) { period = n; continue; }
                if (n >= 1 && n <= 49) nums.add(n);
            } catch (Exception ignored) {}
        }
        if (nums.size() < 7) { toast("要 7 个号：6 个平码 + 1 个特码"); return; }
        Draw d = new Draw();
        d.period = period;
        d.regular = new ArrayList<>(nums.subList(0, 6));
        d.special = nums.get(6);
        store.saveDraw(d, curShop);
        // 结算入累计：同一店同一期只记一次，避免反复点保存重复累加
        String settledKey = "settledPeriod_" + curShop;
        String settled = store.sp().getString(settledKey, "");
        if (!settled.equals(String.valueOf(d.period))) {
            List<Order> today = store.todayOrders(curShop);
            Settle.Result sr = Settle.of(Board.of(today), store.cap(), today, d, store.pingteMult());
            store.addUpDelta(sr.delta, new Date());
            // 自动记一条赔付流水（与专业版同口径）
            Store.PayRec rec = new Store.PayRec();
            rec.product = "自动结算";
            rec.amount = store.totalPayout(today, d);
            rec.note = "期" + d.period + " 特" + String.format("%02d", d.special);
            rec.time = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.CHINA).format(new Date());
            store.addPay(rec);
            store.sp().edit().putString(settledKey, String.valueOf(d.period)).apply();
        }
        refresh();
        toast("开奖已保存，已重算");
    }

    // ---------- 渲染 ----------

    private void refresh() {
        List<Order> today = store.todayOrders(curShop);
        Draw d = store.draw(curShop);
        double amt = store.totalAmount(today);
        double pay = d.regular.size() == 6 ? store.totalPayout(today, d) : 0;
        String date = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(new Date());

        double net = amt - pay;
        android.text.SpannableStringBuilder sm = new android.text.SpannableStringBuilder(date);
        sm.setSpan(new android.text.style.StyleSpan(android.graphics.Typeface.BOLD), 0, date.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        sm.setSpan(new android.text.style.AbsoluteSizeSpan(15, true), 0, date.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        sm.setSpan(new android.text.style.ForegroundColorSpan(0xFF333333), 0, date.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        int st0 = sm.length();
        sm.append("　本日 " + today.size() + " 单 · 收 " + String.format("%.2f", amt)
                + " · 净 " + String.format("%.2f", net));
        sm.setSpan(new android.text.style.ForegroundColorSpan(0xFF999999), st0, sm.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        summary.setText(sm);
        summary.setTextColor(C_TXT);

        // 订单列表
        renderOrdersList(today, d);

        // 结算
        resultBox.removeAllViews();
        // 专业版盈利统计首行：总单 / 赔付 / 毛净（数值 14 加粗，毛净绿红）
        double sales = 0, payout0 = 0;
        for (Order o : today) {
            sales += o.amount();
            if (d.regular.size() == 6) payout0 += Calc.win(o, d, store.pingteMult()).total;
        }
        LinearLayout pRow = new LinearLayout(this);
        pRow.setOrientation(LinearLayout.HORIZONTAL);
        pRow.setPadding(0, 0, 0, dp(4));
        pRow.addView(phead("总单 ", sales, 0xFF1A1A1A));
        pRow.addView(phead("赔付 ", -payout0, 0xFF1A1A1A));
        pRow.addView(phead("毛净 ", sales - payout0, (sales - payout0) >= 0 ? 0xFF166534 : 0xFFCF1322));
        resultBox.addView(pRow);
        if (d.regular.size() == 6) {
            resultBox.addView(tv("开奖第 " + d.period + " 期　" + drawLine(d), 13, C_TXT, false));
            boolean any = false;
            for (Order o : today) {
                Calc.Result r = Calc.win(o, d, store.pingteMult());
                if (r.lines.isEmpty()) continue;
                any = true;
                LinearLayout box = new LinearLayout(this);
                box.setOrientation(LinearLayout.VERTICAL);
                box.setPadding(0, dp(8), 0, 0);
                box.addView(tv(o.customer + "　" + o.codes.size() + " 注", 12, C_SUB, false));
                for (Calc.Line l : r.lines) box.addView(tv(l.text(), 13, C_GREEN, false));
                box.addView(tv("合计 " + Calc.fmt(r.total), 13, C_GREEN, true));
                resultBox.addView(box);
            }
            if (!any) resultBox.addView(tv("这次没有命中", 12, C_SUB, false));
            resultBox.addView(tv("总赔付 " + Calc.fmt(pay), 14, C_RED, true));
        } else {
            resultBox.addView(tv("未获取开奖数据，录了就自动出结算", 12, C_SUB, false));
        }

        renderBoard(today);
        renderSplit(today);
        renderSim(today);
        renderArchive();
        renderUp(today);
        renderRisk(today);
        renderCustomers();
        renderBalls();
        if (custPick != null) { custPick.setTag("custpick"); custPick.setText("客户：" + store.customer() + " ▾"); }
        if (orderCum != null) {
            // 与专业版同口径：按金额累计（特号 = 总收 − 平特 − 连肖 − 二三），不是数号码个数
            double emAmt = 0, pteAmt = 0, lxAmt = 0, specAmt = 0;
            for (Order o : today) {
                java.util.Set<String> seen = new java.util.HashSet<>();
                double em = 0, pte = 0, lx = 0;
                for (String c : o.codes) {
                    if (!seen.add(c)) continue;
                    double a = o.amtOf(c);
                    if (c.startsWith("二中二") || c.startsWith("三中三") || c.startsWith("三中二")) em += a;
                    else if (c.startsWith("平特")) pte += a;
                    else if (c.startsWith("连肖")) lx += a;
                }
                emAmt += em;
                pteAmt += pte;
                lxAmt += lx;
                specAmt += o.amount() - em - pte - lx;
            }
            orderCum.setText("订单累计：特号" + Calc.fmt(specAmt)
                    + "　平/连:" + Calc.fmt(pteAmt) + "/" + Calc.fmt(lxAmt)
                    + "　二/三:" + Calc.fmt(emAmt));
        }
        if (drawBox != null) {
            Draw dd = store.draw(curShop);
            drawBox.setText(dd.period > 0 ? drawLine(dd) : "未获取开奖数据");
        }
        tickClockOnce();
        // 每次重绘后把新建的输入框也关掉自动填充，避免部分机型点到按钮没反应
        try { disableAutofill(getWindow().getDecorView()); } catch (Exception ignored) {}
        renderHkBar();
    }


    private void autoFetch() {
        final String lot = curShop.equals("港") ? "港" : "澳";
        toast("正在获取开奖…");
        final Context ctx = this;
        new Thread(() -> {
            Net net = new Net(ctx);
            Draw other = net.fetch(lot.equals("港") ? "澳" : "港");
            if (other != null) store.saveDraw(other, other.lottery);
            final Draw got = net.fetch(lot);
            runOnUiThread(() -> {
                if (got == null) {
                    toast("暂时取不到开奖数据（服务器正在同步，通常一两分钟）。请稍后再点一次，也可以手动粘贴。");
                    return;
                }
                Draw cur = store.draw(curShop);
                if (cur.period > 0 && got.period < cur.period) {
                    toast("已录到第 " + cur.period + " 期。服务器这次返回的是旧数据（第 " + got.period + " 期），请过一两分钟再点一次。");
                    return;
                }
                if (cur.period == got.period && drawLine(cur).equals(drawLine(got))) {
                    drawBox.setText(drawLine(got));
                    refresh();
                    toast("已是最新，第 " + got.period + " 期没有变化");
                    return;
                }
                store.saveDraw(got, curShop);
                hkBarShown = true;
                drawBox.setText(drawLine(got));
                refresh();
                toast("已获取第 " + got.period + " 期");
            });
        }).start();
    }

    /** 跨天旧单自动拆进历史（专业版 billSplitOld）：避免昨天的单混进今天账本 */
    private void splitOldOrders() {
        List<Order> all = store.orders();
        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(new Date());
        Map<String, List<Order>> byDay = new LinkedHashMap<>();
        List<Order> keep = new ArrayList<>();
        boolean moved = false;
        for (Order o : all) {
            if (o.ts <= 0) { keep.add(o); continue; }
            String day = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(new Date(o.ts));
            if (day.equals(today)) { keep.add(o); continue; }
            byDay.computeIfAbsent(day, k -> new ArrayList<>()).add(o);
            moved = true;
        }
        if (!moved) return;
        for (Map.Entry<String, List<Order>> e : byDay.entrySet()) {
            archive.save(e.getKey() + " " + e.getValue().size() + "单", e.getValue());
        }
        store.saveOrders(keep);
    }

    private void doArchive() {
        List<Order> today = store.todayOrders(curShop);
        if (today.isEmpty()) { toast("今天还没有订单"); return; }
        Draw d = store.draw(curShop);
        String label = (d.period > 0 ? "第" + d.period + "期 " : "") + today.size() + "单";
        int n = archive.save(label, today);
        if (n == 0) { toast("归档失败"); return; }
        store.saveOrders(new ArrayList<Order>());
        refresh();
        toast("已归档 " + n + " 单，今日清空");
    }

    /** 补号模拟（专业版是 AI统计 里的一层折叠，不是独立卡片） */
    private LinearLayout renderSimBody(List<Order> today) {
        Board b = Board.of(today);
        double cap = store.cap();
        LinearLayout wrap = new LinearLayout(this);
        wrap.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams wlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        wlp.setMargins(0, dp(8), 0, 0);
        wrap.setLayoutParams(wlp);

        final LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setVisibility(View.GONE);

        LinearLayout head = foldHead("接单预演 · 补号模拟 ▶");
        head.setOnClickListener(v -> {
            boolean show = body.getVisibility() != View.VISIBLE;
            body.setVisibility(show ? View.VISIBLE : View.GONE);
            ((TextView) head.getChildAt(0)).setText(
                    ((TextView) head.getChildAt(0)).getText().toString().replace(show ? "▶" : "▼", show ? "▼" : "▶"));
            if (show) fillSim(body, b, cap);
        });
        wrap.addView(head);
        wrap.addView(body);
        return wrap;
    }

    private void fillSim(LinearLayout box, Board b, double cap) {
        box.removeAllViews();
        if (b.total <= 0) { box.addView(tv("还没有特号单", 12, C_SUB, false)); return; }
        int n = 0;
        for (double v : b.bets.values()) if (v > 0) n++;
        box.addView(tv("现在 " + n + "/49 号有注　自留 " + Calc.fmt(b.kept(cap)) + "　最坏 " + Calc.fmt(b.worst(cap)),
                11, 0xFF888888, false));

        box.addView(tv("补最低的号（补新号不会抬高最重号，纯粹加自留）：", 11, 0xFF666666, false));
        List<int[]> low = SimAdd.lowest(b, cap, 12);
        StringBuilder sb = new StringBuilder();
        for (int[] x : low) sb.append(String.format("%02d %d　", x[0], x[1]));
        box.addView(tv("现在最少的 12 个号（补这些最划算）：", 11, 0xFF555555, false));
        TextView lowTxt = tv(sb.toString().trim(), 11, C_TXT, true);
        box.addView(lowTxt);
        box.addView(tv("　括号里是「现在的注→补后」", 11, C_SUB, false));

        LinearLayout hd = new LinearLayout(this);
        hd.setOrientation(LinearLayout.HORIZONTAL);
        hd.setPadding(0, 0, 0, dp(2));
        TextView h1 = tv("补法", 11, C_SUB, false);
        h1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        hd.addView(h1);
        hd.addView(tv("进自留　　补后最坏", 11, C_SUB, false));
        box.addView(hd);
        View hdiv = new View(this);
        hdiv.setBackgroundColor(0xFFEEEEEE);
        box.addView(hdiv, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        int[][] cases = {{5, 50}, {10, 50}, {15, 50}, {20, 50}, {5, (int) cap}, {10, (int) cap}, {20, (int) cap}};
        for (int[] c : cases) {
            SimAdd.Result r = SimAdd.run(b, cap, c[0], c[1]);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(0, dp(3), 0, dp(3));
            TextView l = tv("补 " + c[0] + " 号 到 " + c[1] + " 元", 12, 0xFF333333, false);
            l.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            row.addView(l);
            row.addView(tv("+" + Calc.fmt(r.added), 12, r.added > 0 ? C_GREEN : C_SUB, false));
            TextView w = tv((r.worst >= 0 ? "+" : "") + Calc.fmt(r.worst), 12, r.worst >= 0 ? C_GREEN : C_RED, true);
            w.setPadding(dp(10), 0, 0, 0);
            row.addView(w);
            box.addView(row);
            StringBuilder pk = new StringBuilder();
            if (r.picks.isEmpty()) pk.append("（已补满）");
            else for (int[] x : r.picks) pk.append(String.format("%02d(%d→%d) ", x[0], x[1], x[2]));
            box.addView(tv(pk.toString().trim(), 10, C_SUB, false));
            View div = new View(this);
            div.setBackgroundColor(0xFFF7F7F7);
            box.addView(div, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        }
        SimAdd.Result fullFill = SimAdd.run(b, cap, 49, Math.max(1, (int) cap));
        TextView capLine = tv("上限：49 个号全补到 " + Calc.fmt(cap) + " 元，共需 " + Calc.fmt(fullFill.added)
                + " 元 → 最坏 " + (fullFill.worst >= 0 ? "+" : "") + Calc.fmt(fullFill.worst) + "（全盘任何号开出都赚）",
                11, C_GREEN, false);
        capLine.setPadding(0, dp(5), 0, 0);
        box.addView(capLine);
        addSimNeedBlocks(box, b, cap);
    }

    /** 补号模拟子块：我能扛到 / 要收的号（与专业版 simNeed / renderNeedList 同文案） */
    private void addSimNeedBlocks(LinearLayout box, Board b, double cap) {
        final double curWorst = b.worst(cap);
        // 我能扛到
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.addView(tv("我能扛到", 11, C_SUB, false));
        final EditText in = new EditText(this);
        in.setSingleLine(true);
        in.setTextSize(12);
        in.setHint("如 -800");
        in.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED);
        in.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row.addView(in);
        final TextView out = tv("", 12, C_TXT, false);
        TextView go = tv("算需要补多少", 12, Color.WHITE, true);
        go.setPadding(dp(10), dp(5), dp(10), dp(5));
        go.setBackgroundColor(0xFF333333);
        go.setOnClickListener(v -> {
            double t;
            try { t = Double.parseDouble(in.getText().toString().trim()); } catch (Exception e) { toast("填个金额，比如 -800"); return; }
            double need = simNeedAmount(b, cap, t);
            if (need <= 0) { out.setText("现在的自留已经扛得住 " + Calc.fmt(t) + "，不用再补。"); out.setTextColor(C_GREEN); return; }
            out.setText("要让最坏不低于 " + Calc.fmt(t) + "，还要补 " + Calc.fmt(need) + " 元自留（补在注额最少的号上，不抬高最重号）。");
            out.setTextColor(C_TXT);
        });
        row.addView(go);
        box.addView(row);
        box.addView(out);

        // 要收的号（照着这个去问下家）
        box.addView(tv("要收的号（照着这个去问下家）", 12, C_TXT, true));
        LinearLayout trow = new LinearLayout(this);
        trow.setOrientation(LinearLayout.HORIZONTAL);
        trow.setGravity(Gravity.CENTER_VERTICAL);
        trow.addView(tv("目标最坏", 11, C_SUB, false));
        final EditText tIn = new EditText(this);
        tIn.setSingleLine(true);
        tIn.setTextSize(12);
        tIn.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED);
        tIn.setText(Calc.fmt(Math.round(curWorst)));
        tIn.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        trow.addView(tIn);
        TextView calc = tv("算清单", 12, Color.WHITE, true);
        calc.setPadding(dp(10), dp(5), dp(10), dp(5));
        calc.setBackgroundColor(0xFF1677FF);
        trow.addView(calc);
        box.addView(trow);
        final LinearLayout listBox = new LinearLayout(this);
        listBox.setOrientation(LinearLayout.VERTICAL);
        calc.setOnClickListener(v -> {
            double t;
            try { t = Double.parseDouble(tIn.getText().toString().trim()); } catch (Exception e) { t = curWorst; }
            fillNeedList(listBox, b, cap, t);
        });
        LinearLayout quick = new LinearLayout(this);
        quick.setOrientation(LinearLayout.HORIZONTAL);
        TextView b1 = tv("按不亏算（差多少）", 11, C_GREEN, false);
        b1.setPadding(dp(4), dp(4), dp(4), dp(4));
        b1.setOnClickListener(v -> { tIn.setText("0"); fillNeedList(listBox, b, cap, 0); });
        TextView b2 = tv("按当前最坏看", 11, 0xFF666666, false);
        b2.setPadding(dp(4), dp(4), dp(4), dp(4));
        b2.setOnClickListener(v -> { tIn.setText(Calc.fmt(Math.round(curWorst))); fillNeedList(listBox, b, cap, curWorst); });
        LinearLayout.LayoutParams qlp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        quick.addView(b1, qlp);
        quick.addView(b2, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        box.addView(quick);
        box.addView(tv("默认填的是你当前盘的最坏值；想「一开任何号都不亏」就点左边那个，它会算出还要收多少钱。", 10, 0xFF999999, false));
        // 我手上 / 统一收 / 按这个收（专业版 renderNeedListByBudget）
        LinearLayout brow = new LinearLayout(this);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setGravity(Gravity.CENTER_VERTICAL);
        brow.setPadding(0, dp(4), 0, dp(2));
        brow.addView(tv("我手上", 11, 0xFF666666, false));
        final EditText budgetIn = new EditText(this);
        budgetIn.setSingleLine(true);
        budgetIn.setTextSize(12);
        budgetIn.setHint("多少钱");
        budgetIn.setInputType(InputType.TYPE_CLASS_NUMBER);
        budgetIn.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        brow.addView(budgetIn);
        brow.addView(tv("统一收", 11, 0xFF666666, false));
        final EditText unitIn = new EditText(this);
        unitIn.setSingleLine(true);
        unitIn.setTextSize(12);
        unitIn.setHint("如 50");
        unitIn.setInputType(InputType.TYPE_CLASS_NUMBER);
        unitIn.setLayoutParams(new LinearLayout.LayoutParams(dp(62), ViewGroup.LayoutParams.WRAP_CONTENT));
        brow.addView(unitIn);
        TextView byBudget = tv("按这个收", 12, Color.WHITE, true);
        byBudget.setPadding(dp(9), dp(5), dp(9), dp(5));
        byBudget.setBackgroundColor(0xFF333333);
        brow.addView(byBudget);
        box.addView(brow);
        byBudget.setOnClickListener(v -> {
            double budget, unit, t;
            try { budget = Double.parseDouble(budgetIn.getText().toString().trim()); } catch (Exception e) { toast("先填你手上有多少钱"); return; }
            try { unit = Math.abs(Double.parseDouble(unitIn.getText().toString().trim())); } catch (Exception e) { unit = 50; }
            try { t = Double.parseDouble(tIn.getText().toString().trim()); } catch (Exception e) { t = curWorst; }
            fillNeedByBudget(listBox, b, cap, budget, unit, t, curWorst);
        });
        box.addView(listBox);
    }

    /** 反推：要让最坏不小于 target，需要补多少自留（专业版 simNeedAmount 同口径） */
    private double simNeedAmount(Board b, double cap, double target) {
        double K = 0, M = 0;
        for (int n = 1; n <= 49; n++) {
            double v = Math.min(b.bets.get(n), cap);
            K += v;
            if (v > M) M = v;
        }
        return Math.max(0, target + Calc.PAY_SPECIAL * M - K);
    }

    private void fillNeedList(LinearLayout box, Board b, double cap, double target) {
        box.removeAllViews();
        double K = 0, M = 0, space = 0;
        for (int n = 1; n <= 49; n++) {
            double v = Math.min(b.bets.get(n), cap);
            K += v;
            space += cap - v;
            if (v > M) M = v;
        }
        double need = target + Calc.PAY_SPECIAL * M - K;
        if (need <= 0) { box.addView(tv("现在的自留已经扛得住 " + Calc.fmt(target) + "，不用再收。", 12, C_GREEN, false)); return; }
        if (need > space) {
            box.addView(tv("49 个号全补到 " + Calc.fmt(cap) + " 元，最多只能进 " + Calc.fmt(space) + " 元，到不了 "
                    + Calc.fmt(target) + "。差额 " + Calc.fmt(need - space) + " 元得靠削峰。", 12, C_RED, false));
            return;
        }
        box.addView(tv("共要收 " + Calc.fmt(need) + " 元（都补到 " + Calc.fmt(cap) + " 以内，不抬高最重号）", 11, C_SUB, false));
        List<Integer> nos = new ArrayList<>();
        for (int n = 1; n <= 49; n++) nos.add(n);
        nos.sort((x, y) -> Double.compare(Math.min(b.bets.get(x), cap), Math.min(b.bets.get(y), cap)));
        double remain = need;
        int cnt = 0;
        for (int n : nos) {
            if (remain <= 0.01) break;
            double v = Math.min(b.bets.get(n), cap);
            double room = cap - v;
            if (room <= 0.01) continue;
            double amt = Math.min(room, remain);
            LinearLayout r = new LinearLayout(this);
            r.setOrientation(LinearLayout.HORIZONTAL);
            r.setPadding(0, dp(2), 0, dp(2));
            r.addView(tv(String.format("%02d", n), 12, C_TXT, true));
            TextView have = tv("现有 " + Calc.fmt(v), 11, C_SUB, false);
            have.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            r.addView(have);
            r.addView(tv("收 " + Calc.fmt(amt), 12, C_TXT, true));
            box.addView(r);
            remain -= amt;
            cnt++;
        }
        box.addView(tv("共 " + cnt + " 个号，合计 " + Calc.fmt(need) + " 元", 11, C_SUB, false));
    }

    /** 按预算+统一收款额出清单（专业版 buildNeedByBudget / renderNeedListByBudget） */
    private void fillNeedByBudget(LinearLayout box, Board b, double cap, double budget, double unit, double target, double curWorst) {
        box.removeAllViews();
        List<Integer> nos = new ArrayList<>();
        for (int n = 1; n <= 49; n++) nos.add(n);
        nos.sort((x, y) -> Double.compare(Math.min(b.bets.get(x), cap), Math.min(b.bets.get(y), cap)));
        double K = 0, M = 0;
        for (int n = 1; n <= 49; n++) {
            double v = Math.min(b.bets.get(n), cap);
            K += v;
            if (v > M) M = v;
        }
        double left = budget, added = 0, maxV = M;
        int cnt = 0;
        List<String> lines = new ArrayList<>();
        for (int n : nos) {
            if (left <= 0.01) break;
            double v = Math.min(b.bets.get(n), cap);
            double room = cap - v;
            if (room <= 0.01) continue;
            double amt = Math.min(room, Math.min(unit, left));
            if (amt <= 0.01) continue;
            lines.add(String.format("%02d　现有 %s　收 %s", n, Calc.fmt(v), Calc.fmt(amt)));
            left -= amt;
            added += amt;
            if (v + amt > maxV) maxV = v + amt;
            cnt++;
        }
        if (cnt == 0) {
            box.addView(tv("预算 " + Calc.fmt(budget) + " 元收不了任何号（每个号都已经补到 " + Calc.fmt(cap) + " 元了）。", 12, C_SUB, false));
            return;
        }
        double newWorst = (K + added) - Calc.PAY_SPECIAL * maxV;
        box.addView(tv("预算 " + Calc.fmt(budget) + " 元，按每号补 " + Calc.fmt(unit) + " 元：能收 " + cnt + " 个号，合计 "
                + Calc.fmt(added) + " 元 → 最坏 " + (newWorst >= 0 ? "+" : "") + Calc.fmt(newWorst)
                + (newWorst >= target ? "（已达到你的目标 " + Calc.fmt(target) + "）"
                : "（离目标 " + Calc.fmt(target) + " 还差 " + Calc.fmt(target - newWorst) + "）"),
                11, newWorst >= 0 ? C_GREEN : C_RED, false));
        for (String ln : lines) {
            LinearLayout r = new LinearLayout(this);
            r.setOrientation(LinearLayout.HORIZONTAL);
            r.setPadding(0, dp(2), 0, dp(2));
            r.addView(tv(ln, 12, C_TXT, false));
            box.addView(r);
        }
        View div = new View(this);
        div.setBackgroundColor(0xFFF7F7F7);
        box.addView(div, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        box.addView(tv("收完还剩 " + Calc.fmt(Math.max(0, left)) + " 元没花完", 11, C_SUB, false));
    }

    private void renderSim(List<Order> today) {
        if (simBox != null && simBox.getVisibility() == View.VISIBLE) fillSim(simBox, Board.of(today), store.cap());
    }

    /** 平特肖：今日各生肖的平特注额与最坏赔付（对应专业版 singlesList） */
    private void renderPte() {
        pteBox.removeAllViews();
        List<Order> today = store.todayOrders(curShop);
        if (today.isEmpty()) { pteBox.addView(tv("今天还没单", 12, C_SUB, false)); return; }
        Map<String, Double> map = new LinkedHashMap<>();
        for (Order o : today) {
            for (int i = 0; i < o.codes.size(); i++) {
                String c = o.codes.get(i);
                if (c.startsWith("平特")) {
                    String z = c.substring(2);
                    map.put(z, map.getOrDefault(z, 0.0) + o.amtOf(c));
                }
            }
        }
        if (map.isEmpty()) { pteBox.addView(tv("今天没有平特单", 12, C_SUB, false)); return; }
        List<Map.Entry<String, Double>> list = new ArrayList<>(map.entrySet());
        list.sort((x, y) -> Double.compare(y.getValue(), x.getValue()));
        double capPte = store.capPte();
        for (Map.Entry<String, Double> e : list) {
            double amt = e.getValue();
            double kept = capPte > 0 ? Math.min(amt, capPte) : 0;
            double mult = e.getKey().equals("马") ? Calc.PAY_PINGTE_MA : store.pingteMult();
            // 专业版 singlesList 行：灰底 1px #eee 边 8 圆角，左生肖徽标，右 N单 + 金额
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable rg = new GradientDrawable();
            rg.setColor(0xFFF8F9FA);
            rg.setCornerRadius(dp(8));
            rg.setStroke(dp(1), 0xFFEEEEEE);
            row.setBackground(rg);
            row.setPadding(dp(6), dp(8), dp(6), dp(8));
            LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            rlp.setMargins(0, 0, 0, dp(3));
            row.setLayoutParams(rlp);

            LinearLayout top = new LinearLayout(this);
            top.setOrientation(LinearLayout.HORIZONTAL);
            top.setGravity(Gravity.CENTER_VERTICAL);
            TextView badge = tv(e.getKey(), 12, 0xFF333333, true);
            GradientDrawable bgb = new GradientDrawable();
            bgb.setColor(0xFFF0F0F0);
            bgb.setCornerRadius(dp(4));
            badge.setBackground(bgb);
            badge.setPadding(dp(8), dp(2), dp(8), dp(2));
            top.addView(badge);
            View sp2 = new View(this);
            sp2.setLayoutParams(new LinearLayout.LayoutParams(0, 1, 1));
            top.addView(sp2);
            top.addView(tv(cntOfCode(e.getKey()) + "单", 14, 0xFF666666, false));
            TextView amtTxt = tv(Calc.fmt(amt), 14, 0xFF1A1A1A, false);
            LinearLayout.LayoutParams atlp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            atlp.leftMargin = dp(12);
            amtTxt.setLayoutParams(atlp);
            amtTxt.setMinWidth(dp(60));
            amtTxt.setGravity(Gravity.END);
            top.addView(amtTxt);
            row.addView(top);
            row.addView(tv("自留 " + Calc.fmt(kept) + "　最坏赔 " + Calc.fmt(kept * mult) + "（×" + Calc.fmt(mult) + "）",
                    11, 0xFF999999, false));
            pteBox.addView(row);
        }
        if (pteBox.getChildCount() == 0) pteBox.addView(tv("今天没有平特单", 12, C_SUB, false));
        pteBox.addView(tv("倍数：普通肖 ×" + Calc.fmt(store.pingteMult()) + "，马 ×" + Calc.fmt(Calc.PAY_PINGTE_MA)
                + (capPte > 0 ? "；每个肖最多自留 " + Calc.fmt(capPte) : "；当前平特全飞"), 11, C_SUB, false));
    }

    /** 某玩法今天录了几单 */
    private int cntOfCode(String code) {
        int n = 0;
        for (Order o : store.todayOrders(curShop)) {
            for (String c : o.codes) if (code.equals(c) || c.equals("平特" + code)) { n++; break; }
        }
        return n;
    }

    private void renderArchive() {
        archBox.removeAllViews();
        List<Order> today = store.todayOrders(curShop);
        Draw dr = store.draw(curShop);
        double tAmt = store.totalAmount(today);
        double tPay = dr.regular.size() == 6 ? store.totalPayout(today, dr) : 0;
        double tNet = tAmt - tPay;
        if (!today.isEmpty()) {
            LinearLayout c = new LinearLayout(this);
            c.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable bg = new GradientDrawable();
            bg.setCornerRadius(dp(8));
            bg.setStroke(dp(1), 0xFFE5E5E5);
            bg.setColor(Color.WHITE);
            c.setBackground(bg);
            c.setPadding(dp(10), dp(10), dp(10), dp(10));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.bottomMargin = dp(8);
            c.setLayoutParams(lp);
            LinearLayout r1 = new LinearLayout(this);
            r1.setOrientation(LinearLayout.HORIZONTAL);
            TextView t1 = tv("今天（未归档）", 14, C_TXT, true);
            t1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            r1.addView(t1);
            r1.addView(tv("净 " + String.format("%.2f", tNet), 14, C_TXT, true));
            c.addView(r1);
            c.addView(tv(today.size() + " 单 · 收 " + String.format("%.2f", tAmt)
                    + " · 赔付 " + String.format("%.2f", tPay), 12, 0xFF888888, false));
            archBox.addView(c);
        }
        List<String[]> list = archive.list();
        if (list.isEmpty() && today.isEmpty()) {
            TextView empty = tv("还没有归档记录。点顶部「今日归档」就会把当天存成一份，之后随时能翻。",
                    13, C_SUB, false);
            empty.setPadding(dp(16), dp(24), dp(16), dp(24));
            empty.setGravity(Gravity.CENTER);
            archBox.addView(empty);
            return;
        }
        for (String[] a : list) {
            final String key = a[0];
            List<Order> old = archive.load(key);
            double amt = store.totalAmount(old);
            double pay = dr.regular.size() == 6 ? store.totalPayout(old, dr) : 0;
            double net = amt - pay;
            LinearLayout c = new LinearLayout(this);
            c.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable bg2 = new GradientDrawable();
            bg2.setCornerRadius(dp(8));
            bg2.setStroke(dp(1), 0xFFE5E5E5);
            bg2.setColor(Color.WHITE);
            c.setBackground(bg2);
            c.setPadding(dp(10), dp(10), dp(10), dp(10));
            LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp2.bottomMargin = dp(8);
            c.setLayoutParams(lp2);
            LinearLayout r1 = new LinearLayout(this);
            r1.setOrientation(LinearLayout.HORIZONTAL);
            TextView t1 = tv(a[1], 14, C_TXT, true);
            t1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            r1.addView(t1);
            r1.addView(tv(old.size() + " 单 · 净 " + String.format("%.2f", net), 13, 0xFF666666, false));
            c.addView(r1);
            LinearLayout r2 = new LinearLayout(this);
            r2.setOrientation(LinearLayout.HORIZONTAL);
            r2.setGravity(Gravity.CENTER_VERTICAL);
            TextView t2 = tv("收 " + String.format("%.2f", amt) + " · 赔付 " + String.format("%.2f", pay)
                    + "　", 12, 0xFF888888, false);
            t2.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            r2.addView(t2);
            TextView viewLink = tv("查看明细 →", 12, C_TXT, false);
            viewLink.setPadding(0, dp(2), 0, dp(2));
            viewLink.setOnClickListener(v -> showArchiveDetail(key, a[1]));
            r2.addView(viewLink);
            c.addView(r2);
            TextView del = tv("删除此日", 12, C_SUB, false);
            del.setPadding(0, dp(6), 0, 0);
            del.setOnClickListener(v -> new android.app.AlertDialog.Builder(this)
                    .setMessage("确认删除 " + a[1] + " 的历史账单？此操作不可恢复。")
                    .setPositiveButton("删除", (dg, w) -> {
                        archive.remove(key);
                        renderArchive();
                        toast("已删除这份归档");
                    })
                    .setNegativeButton("取消", null)
                    .show());
            c.addView(del);
            archBox.addView(c);
        }
    }

    /** 历史账单明细（专业版 billView：单量 / 收 / 赔付 / 净 + 逐单 + 恢复为当前账本） */
    private void showArchiveDetail(String key, String label) {
        List<Order> old = archive.load(key);
        Draw dr = store.draw(curShop);
        double amt = store.totalAmount(old);
        double pay = dr.regular.size() == 6 ? store.totalPayout(old, dr) : 0;
        double net = amt - pay;
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(14), dp(6), dp(14), dp(6));
        LinearLayout stat = new LinearLayout(this);
        stat.setOrientation(LinearLayout.HORIZONTAL);
        stat.setBackgroundColor(0xFFFAFAFA);
        stat.setPadding(dp(8), dp(8), dp(8), dp(8));
        stat.addView(tv("收 " + String.format("%.2f", amt), 12, C_TXT, false));
        stat.addView(tv("　赔付 " + String.format("%.2f", pay), 12, C_TXT, false));
        stat.addView(tv("　净 " + String.format("%.2f", net), 12, 0xFF7C3AED, true));
        box.addView(stat);
        java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("MM-dd HH:mm", Locale.CHINA);
        for (Order o : old) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(7), 0, dp(7));
            LinearLayout left = new LinearLayout(this);
            left.setOrientation(LinearLayout.VERTICAL);
            left.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            left.addView(tv(o.customer == null || o.customer.isEmpty() ? "散客" : o.customer, 13, C_TXT, true));
            left.addView(tv(String.join(" ", o.codes), 12, 0xFF888888, false));
            row.addView(left);
            row.addView(tv(Calc.fmt(o.amount()) + "　" + f.format(new Date(o.ts)), 12, C_TXT, true));
            box.addView(row);
            View div = new View(this);
            div.setBackgroundColor(0xFFF0F0F0);
            box.addView(div, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        }
        if (old.isEmpty()) box.addView(tv("这天没有订单", 13, C_SUB, false));
        ScrollView sv = new ScrollView(this);
        sv.addView(box);
        new android.app.AlertDialog.Builder(this)
                .setTitle(label + "　" + old.size() + " 单")
                .setView(sv)
                .setPositiveButton("关闭", null)
                .setNeutralButton("把这天恢复为当前账本", (dg, w) -> {
                    List<Order> now = store.todayOrders(curShop);
                    if (!now.isEmpty()) {
                        Draw d0 = store.draw(curShop);
                        archive.save((d0.period > 0 ? "第" + d0.period + "期 " : "") + now.size() + "单", now);
                    }
                    store.saveOrders(old);
                    refresh();
                    toast("已把 " + label + " 恢复为当前账本");
                })
                .show();
    }

    /** 上家卡片：本周 / 今日 / 历史，以及本期飞走与结算 */

    private void doRestore() {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm.getPrimaryClip() == null || cm.getPrimaryClip().getItemCount() == 0) {
                toast("剪贴板是空的");
                return;
            }
            String txt = String.valueOf(cm.getPrimaryClip().getItemAt(0).getText());
            if (!txt.contains("NTV-BACKUP")) { toast("这段内容不是备份"); return; }
            final String body = txt;
            new android.app.AlertDialog.Builder(this)
                    .setTitle("从剪贴板恢复")
                    .setMessage("会覆盖当前订单与设置，确定吗？")
                    .setPositiveButton("恢复", (d1, w) -> {
                        int n = store.restoreFromText(body);
                        refresh();
                        toast(n >= 0 ? "已恢复 " + n + " 单" : "备份内容损坏");
                    })
                    .setNegativeButton("取消", null)
                    .show();
        } catch (Exception e) {
            toast("读取剪贴板失败");
        }
    }


    private void renderRisk(List<Order> today) {
        riskBox.removeAllViews();
        if (today.isEmpty()) {
            // 没有订单：不显示开奖结果、持仓、风险体检这些「看着像有账」的块
            riskBox.addView(tv("还没有订单，录了单这里自动出统计", 13, C_SUB, false));
            return;
        }
        Board b = Board.of(today);
        double cap = store.cap();
        double capPte = store.capPte();
        double capLx = store.capLx();
        double full = b.total + b.other;
        Draw d = store.draw(curShop);

        // 各产品注额
        double pteBet = 0, lxBet = 0, emBet = 0;
        Map<String, Double> pteByZod = new LinkedHashMap<>();
        for (Order o : today) {
            for (int i = 0; i < o.codes.size(); i++) {
                String c = o.codes.get(i);
                double amt = o.amtOf(c);
                if (c.startsWith("平特")) {
                    String z = c.substring(2);
                    pteByZod.put(z, pteByZod.getOrDefault(z, 0.0) + amt);
                    pteBet += amt;
                } else if (c.startsWith("连肖")) {
                    lxBet += amt;
                } else if (c.startsWith("二中二:") || c.startsWith("三中三:") || c.startsWith("三中二:")) {
                    emBet += amt;
                }
            }
        }
        // ② 已飞累计（历史上确认过的）
        double already = 0;
        for (double v : store.flown().values()) already += v;
        double shouldFly = 0;
        for (int n = 1; n <= 49; n++) shouldFly += Math.max(0, b.bets.get(n) - cap);
        double pending = Math.max(0, shouldFly - already);

        // ① 顶部阈值（实时）
        riskBox.addView(tv(String.format("当前飞单阈值（实时）特号 %s ｜ 平特 %s ｜ 连肖 %s",
                Calc.fmt(cap), Calc.fmt(capPte), Calc.fmt(capLx)), 11, C_SUB, false));

        double pteFlyPre = 0, pteKeptPre = 0;
        for (Map.Entry<String, Double> e : pteByZod.entrySet()) {
            double a0 = e.getValue();
            double k0 = capPte > 0 ? Math.min(a0, capPte) : 0;
            pteKeptPre += k0;
            pteFlyPre += Math.max(0, a0 - k0);
        }
        // ② 三格
        LinearLayout tri = new LinearLayout(this);
        tri.setOrientation(LinearLayout.HORIZONTAL);
        tri.setPadding(0, dp(6), 0, dp(6));
        tri.addView(triCell("总单", Calc.fmt(full), C_TXT, "全部产品订单总额"));
        tri.addView(triCell("已飞(实际)", Calc.fmt(already), C_RED, "历史上已确认飞出的"));
        tri.addView(triCell("待飞", Calc.fmt(pending + pteFlyPre), 0xFFD97706, "按当前阈值还该飞"));
        riskBox.addView(tri);

        riskBox.addView(tv("三个数不同口径：总单是全部产品订单；已飞是之前手动确认过的累计；待飞是照当前阈值「特号 "
                + Calc.fmt(cap) + " / 平特 " + Calc.fmt(capPte) + " / 连肖 " + Calc.fmt(capLx)
                + "」还算该飞多少。下方号码表的「飞」只算特号 01–49，跟这三个不是一回事。", 10, C_SUB, false));

        // ③ 赔付与自留（用于最坏/自留现金）
        double specPayout = 0;
        for (int n = 1; n <= 49; n++) specPayout = Math.max(specPayout, Math.min(b.bets.get(n), cap) * Calc.PAY_SPECIAL);
        // 平特最坏：注额最高的 7 个肖都中
        List<Double> pteKeptPay = new ArrayList<>();
        double pteKept = 0, pteFly = 0;
        for (Map.Entry<String, Double> e : pteByZod.entrySet()) {
            double amt = e.getValue();
            double kept = capPte > 0 ? Math.min(amt, capPte) : 0;
            pteKept += kept;
            pteFly += Math.max(0, amt - kept);
            pteKeptPay.add(kept * (e.getKey().equals("马") ? Calc.PAY_PINGTE_MA : store.pingteMult()));
        }
        pteKeptPay.sort((x, y) -> Double.compare(y, x));
        double ptePayout = 0;
        for (int i = 0; i < Math.min(7, pteKeptPay.size()); i++) ptePayout += pteKeptPay.get(i);
        // 连肖最坏：全中
        double lxPayout = 0, lxKept = 0;
        for (Order o : today) {
            for (int i = 0; i < o.codes.size(); i++) {
                String c = o.codes.get(i);
                if (!c.startsWith("连肖")) continue;
                String zod = c.substring(2);
                double amt = o.amtOf(c);
                double kept = capLx > 0 ? Math.min(amt, capLx) : amt;
                lxKept += kept;
                double odds = zod.length() == 2 ? 4 : zod.length() == 3 ? 10 : 30;
                if (zod.contains("马")) odds -= 0.5;
                lxPayout += kept * odds;
            }
        }
        double totalPayout = specPayout + ptePayout + lxPayout;
        double keptCash = full - (b.total - b.kept(cap)) - pteFly - (lxBet - lxKept);
        double worstNet = keptCash - totalPayout;
        int heaviest = 1;
        for (int n = 1; n <= 49; n++) if (b.bets.get(n) > b.bets.get(heaviest)) heaviest = n;

        // ④ 已开奖块
        if (d.regular.size() == 6 && d.special > 0) {
            double net = keptCash - Math.min(b.bets.get(d.special), cap) * Calc.PAY_SPECIAL - ptePayout - lxPayout;
            LinearLayout box = new LinearLayout(this);
            box.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable dbg = new GradientDrawable();
            dbg.setColor(0xFFF8F9FA);
            dbg.setCornerRadius(dp(8));
            dbg.setStroke(dp(1), 0xFFE5E5E5);
            box.setBackground(dbg);
            box.setPadding(dp(12), dp(10), dp(12), dp(10));
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            blp.setMargins(0, dp(6), 0, dp(6));
            box.setLayoutParams(blp);
            // 标题点一下就收起/展开，不想看就藏起来（号码、盈亏一起藏）
            final TextView dHead = tv("已开奖：特" + String.format("%02d", d.special) + " " + Z.of(d.special) + " ▾", 15, 0xFF333333, true);
            final LinearLayout dBody = new LinearLayout(this);
            dBody.setOrientation(LinearLayout.VERTICAL);
            StringBuilder regs = new StringBuilder("平号：");
            for (int r : d.regular) regs.append(String.format("%02d", r)).append(Z.of(r)).append(" ");
            dBody.addView(tv(regs.toString(), 13, 0xFF666666, false));
            dBody.addView(tv("实际净盈亏：" + (net >= 0 ? "+" : "") + Calc.fmt(net), 18, net >= 0 ? 0xFF166534 : C_RED, true));
            dHead.setOnClickListener(v -> {
                boolean show = dBody.getVisibility() != View.VISIBLE;
                dBody.setVisibility(show ? View.VISIBLE : View.GONE);
                dHead.setText(dHead.getText().toString().replace(show ? "▸" : "▾", show ? "▾" : "▸"));
            });
            box.addView(dHead);
            box.addView(dBody);
            riskBox.addView(box);
        }

        // ⑤ 持仓分析（可折叠）
        final LinearLayout odBody = new LinearLayout(this);
        odBody.setOrientation(LinearLayout.VERTICAL);
        odBody.setVisibility(View.GONE);
        GradientDrawable odbg = new GradientDrawable();
        odbg.setColor(0xFFF8F9FA);
        odbg.setCornerRadius(dp(8));
        odbg.setStroke(dp(1), 0xFFE5E5E5);
        odBody.setBackground(odbg);
        odBody.setPadding(dp(12), dp(10), dp(12), dp(12));
        // 正文：特号独立盈亏 + 三个阈值建议（不亏 / 只亏 20% / 只亏 40%）
        double odFull = b.total;
        odBody.addView(tv("持仓费用：总单 " + Calc.fmt(odFull) + " 元，自留 " + Calc.fmt(keptCash)
                + " 元，最坏 " + (worstNet >= 0 ? "+" : "") + Calc.fmt(worstNet) + " 元", 14, 0xFF333333, false));
        odBody.addView(tv("特号独立盈亏：全号都中要赔 " + Calc.fmt(specPayout) + " 元（按每号留 "
                + Calc.fmt(cap) + " 元 × " + Calc.fmt(Calc.PAY_SPECIAL) + " 倍）", 14, 0xFF333333, false));
        double rec0 = recommendCap(b, 0);
        double rec20 = recommendCap(b, -odFull * 0.2);
        double rec40 = recommendCap(b, -odFull * 0.4);
        double keepNoLose = rec0 / Calc.PAY_SPECIAL;
        odBody.addView(tv("不亏：每号最多留 " + Calc.fmt(keepNoLose) + " 元（阈值 " + Calc.fmt(rec0) + "）", 14, 0xFF333333, false));
        odBody.addView(tv("只亏当天 20%（" + Calc.fmt(-odFull * 0.2) + "）：每号最多留 "
                + Calc.fmt(rec20 / Calc.PAY_SPECIAL) + " 元（阈值 " + Calc.fmt(rec20) + "）", 14, 0xFF333333, false));
        odBody.addView(tv("只亏当天 40%（" + Calc.fmt(-odFull * 0.4) + "）：每号最多留 "
                + Calc.fmt(rec40 / Calc.PAY_SPECIAL) + " 元（阈值 " + Calc.fmt(rec40) + "）", 14, 0xFF333333, false));
        odBody.addView(tv("这里的数按当前盘面算，改了上方阈值或录了新单会自动重算。", 11, 0xFF999999, false));
        final LinearLayout odHead = foldHead("持仓分析" + (cap > 0 ? "（飞单后）" : "（全飞）")
                + (d.regular.size() == 6 && d.special > 0 ? "（已开奖）" : "（开奖前预测）")
                + " · 最坏 " + Calc.fmt(worstNet) + " ▶");
        odHead.setOnClickListener(v -> {
            boolean show = odBody.getVisibility() != View.VISIBLE;
            odBody.setVisibility(show ? View.VISIBLE : View.GONE);
            ((TextView) odHead.getChildAt(0)).setText(((TextView) odHead.getChildAt(0)).getText().toString()
                    .replace(show ? "▶" : "▼", show ? "▼" : "▶"));
        });
        riskBox.addView(odHead);
        riskBox.addView(odBody);

        // ⑥ 特号持仓（独立折叠，与专业版标题/行格式一致）
        final LinearLayout specBody = new LinearLayout(this);
        specBody.setOrientation(LinearLayout.VERTICAL);
        specBody.setVisibility(View.GONE);
        final LinearLayout specHead = foldHead("特号持仓 · 下注 " + Calc.fmt(b.total)
                + " · 最坏 " + Calc.fmt(b.kept(cap) - specPayout) + "（开" + String.format("%02d", heaviest) + "） ▶");
        specHead.setOnClickListener(v -> {
            boolean show = specBody.getVisibility() != View.VISIBLE;
            specBody.setVisibility(show ? View.VISIBLE : View.GONE);
            ((TextView) specHead.getChildAt(0)).setText(((TextView) specHead.getChildAt(0)).getText().toString()
                    .replace(show ? "▶" : "▼", show ? "▼" : "▶"));
            if (show && specBody.getChildCount() == 0) fillSpecTable(specBody, b, cap, b.kept(cap));
        });
        riskBox.addView(specHead);
        riskBox.addView(specBody);

        // ⑦ 平特持仓（有平特单才出现）
        if (pteBet > 0) {
            final LinearLayout pteBody = new LinearLayout(this);
            pteBody.setOrientation(LinearLayout.VERTICAL);
            pteBody.setVisibility(View.GONE);
            final String[] zs = new String[]{"最多" + Math.min(7, pteByZod.size()) + "肖同时中"};
            final LinearLayout pteHead = foldHead("平特持仓 · 下注 " + Calc.fmt(pteBet)
                    + " / 自留 " + Calc.fmt(pteKept) + " · 最坏赔 " + Calc.fmt(ptePayout)
                    + "（" + zs[0] + "） ▶");
            pteHead.setOnClickListener(v -> {
                boolean show = pteBody.getVisibility() != View.VISIBLE;
                pteBody.setVisibility(show ? View.VISIBLE : View.GONE);
                ((TextView) pteHead.getChildAt(0)).setText(((TextView) pteHead.getChildAt(0)).getText().toString()
                        .replace(show ? "▶" : "▼", show ? "▼" : "▶"));
                if (show && pteBody.getChildCount() == 0) {
                    pteBody.addView(pteRow(0, "生肖", "下注", "飞了", "自留净赔"));
                    List<Map.Entry<String, Double>> arr = new ArrayList<>(pteByZod.entrySet());
                    arr.sort((x, y) -> Double.compare(y.getValue(), x.getValue()));
                    for (Map.Entry<String, Double> e : arr) {
                        double kept = capPte > 0 ? Math.min(e.getValue(), capPte) : 0;
                        double fly = Math.max(0, e.getValue() - kept);
                        double mult = e.getKey().equals("马") ? Calc.PAY_PINGTE_MA : store.pingteMult();
                        double gross = kept * mult, netPay = gross - kept;
                        String flyTxt = fly > 0 ? Calc.fmt(fly) : "-";
                        String payTxt = kept <= 0 ? "全飞" : Calc.fmt(netPay);
                        pteBody.addView(pteRow(1, e.getKey(), Calc.fmt(e.getValue()), flyTxt, payTxt,
                                fly > 0 ? C_RED : C_SUB, kept <= 0 ? C_SUB : C_RED));
                    }
                }
            });
            riskBox.addView(pteHead);
            riskBox.addView(pteBody);
        }

        // ⑦b 连肖持仓（专业版：自留有 ≥2 个肖时出现）
        List<String> pteKeptZ = new ArrayList<>();
        List<Double> pteKeptA = new ArrayList<>();
        for (Map.Entry<String, Double> e : pteByZod.entrySet()) {
            double kept = capPte > 0 ? Math.min(e.getValue(), capPte) : 0;
            if (kept > 0) { pteKeptZ.add(e.getKey()); pteKeptA.add(kept); }
        }
        if (pteKeptZ.size() >= 2) {
            double sumKept = 0, allPay = 0;
            StringBuilder who = new StringBuilder();
            for (int i = 0; i < pteKeptZ.size(); i++) {
                double a = pteKeptA.get(i);
                sumKept += a;
                allPay += a * (pteKeptZ.get(i).equals("马") ? Calc.PAY_PINGTE_MA : Calc.PAY_PINGTE);
                if (i > 0) who.append("、");
                who.append(pteKeptZ.get(i)).append(Calc.fmt(a));
            }
            final LinearLayout lxHedgeBody = new LinearLayout(this);
            lxHedgeBody.setOrientation(LinearLayout.VERTICAL);
            lxHedgeBody.setVisibility(View.GONE);
            final String headTxt = "连肖持仓 ▶";
            final LinearLayout lxHedgeHead = foldHead(headTxt);
            final double fSumKept = sumKept, fAllPay = allPay;
            final String fWho = who.toString();
            lxHedgeHead.setOnClickListener(v -> {
                boolean show = lxHedgeBody.getVisibility() != View.VISIBLE;
                lxHedgeBody.setVisibility(show ? View.VISIBLE : View.GONE);
                ((TextView) lxHedgeHead.getChildAt(0)).setText(((TextView) lxHedgeHead.getChildAt(0)).getText().toString()
                        .replace(show ? "▶" : "▼", show ? "▼" : "▶"));
                if (show && lxHedgeBody.getChildCount() == 0) {
                    lxHedgeBody.addView(tv("持仓" + pteKeptZ.size() + "个肖：" + fWho, 13, C_TXT, false));
                    lxHedgeBody.addView(tv("收" + Calc.fmt(fSumKept) + " 全中赔" + Calc.fmt(fAllPay), 13, C_TXT, false));
                    View hr = new View(this);
                    hr.setBackgroundColor(0xFFFCD34D);
                    lxHedgeBody.addView(hr, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
                    double worstNoHedge = fSumKept - fAllPay;
                    lxHedgeBody.addView(tv("连肖全中要赔：" + (worstNoHedge >= 0 ? "+" : "") + Calc.fmt(worstNoHedge),
                            13, worstNoHedge < 0 ? C_RED : C_GREEN, true));
                }
            });
            riskBox.addView(lxHedgeHead);
            riskBox.addView(lxHedgeBody);
        }

        // ⑧ 飞单明细（可折叠）
        final LinearLayout flyBody = new LinearLayout(this);
        flyBody.setOrientation(LinearLayout.VERTICAL);
        flyBody.setVisibility(View.GONE);
        final LinearLayout flyHead = foldHead("📄 飞单明细 ▶");
        flyHead.setOnClickListener(v -> {
            boolean show = flyBody.getVisibility() != View.VISIBLE;
            flyBody.setVisibility(show ? View.VISIBLE : View.GONE);
            ((TextView) flyHead.getChildAt(0)).setText(((TextView) flyHead.getChildAt(0)).getText().toString()
                    .replace(show ? "▶" : "▼", show ? "▼" : "▶"));
        });

        StringBuilder fb = new StringBuilder();
        fb.append("阈值 特 ").append(Calc.fmt(cap)).append(" ｜ 平 ").append(Calc.fmt(capPte))
          .append(" ｜ 连 ").append(Calc.fmt(capLx)).append("\n");
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            if (nb > cap) fb.append("— ").append(String.format("%02d", n)).append(" ").append(Calc.fmt(nb)).append("\n");
        }
        for (Map.Entry<String, Double> e : pteByZod.entrySet()) {
            fb.append("— ").append(e.getKey()).append(" ").append(Calc.fmt(e.getValue())).append("\n");
        }
        fb.append("合计　").append(Calc.fmt(shouldFly + pteFly)).append("\n");
        fb.append("飞出去·特号（本轮该飞，未凑整）").append(Calc.fmt(shouldFly)).append("\n");
        if (pteFly > 0) fb.append("飞出去（平特那边赔）").append(Calc.fmt(pteFly)).append("\n");
        fb.append("飞出去合计").append(Calc.fmt(shouldFly + pteFly));
        fb.append("　已飞累计 ").append(Calc.fmt(already)).append("（含早前确认过的）");
        fb.append(" · 按现阈值还该飞 ").append(Calc.fmt(shouldFly + pteFly))
          .append("，扣掉已飞还要补 ").append(Calc.fmt(Math.max(0, shouldFly + pteFly - already)))
          .append(" → 凑整后 ").append(Calc.fmt(Math.max(0, shouldFly + pteFly - already))).append("\n");
        fb.append("飞完实付（不含二/三中三）").append(Calc.fmt(shouldFly + pteFly)).append("\n");
        if (capPte <= 0) fb.append("未凑整，按原额飞\n");
        else if (Math.abs(Math.round((shouldFly + pteFly) / 5.0) * 5 - (shouldFly + pteFly)) < 0.01)
            fb.append("　凑整差额 0（飞额已是 5 的倍数）\n");
        fb.append("自留现金").append(Calc.fmt(keptCash))
          .append("　现在手上 ").append(Calc.fmt(full - already))
          .append("（总单减已飞）· 补飞完才是上面这个数\n");
        fb.append("├ 特号赔付").append(Calc.fmt(specPayout)).append("\n");
        fb.append("├ 平特赔付").append(Calc.fmt(ptePayout)).append("\n");
        fb.append("└ 连肖赔付").append(Calc.fmt(lxPayout)).append("\n");
        fb.append("总赔付风险").append(Calc.fmt(totalPayout)).append("\n");
        fb.append("自留后最坏净盈亏").append(Calc.fmt(worstNet));
        flyBody.addView(tv(fb.toString(), 12, C_TXT, false));

        // ⑨ 号码表（削峰档 / 录单阈值 两模式共用一张表，与专业版 cutMode 同口径）
        String mode = store.cutMode();
        if (!"cut".equals(mode)) mode = "raw";
        final double cutPick = store.cutPick();
        final double capTab = "cut".equals(mode) ? (cutPick > 0 ? cutPick : cap) : cap;

        // ---- 号码表 ----
        LinearLayout numTable = new LinearLayout(this);
        numTable.setOrientation(LinearLayout.VERTICAL);
        numTable.setPadding(0, dp(8), 0, dp(4));
        double tabKept = 0, tabTotal = 0;
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            tabTotal += nb;
            tabKept += Math.min(nb, capTab);
        }
        LinearLayout ntTitle = new LinearLayout(this);
        ntTitle.setOrientation(LinearLayout.HORIZONTAL);
        TextView ntL = tv("号码表（" + ("cut".equals(mode) ? "削峰档" : "录单阈值") + " " + Calc.fmt(capTab)
                + " 元/号）｜每行＝这个号开出时整本账的盈亏", 11, C_SUB, false);
        ntL.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        ntTitle.addView(ntL);
        ntTitle.addView(tv("自留 " + Calc.fmt(tabKept) + " · 飞 " + Calc.fmt(tabTotal - tabKept), 11, C_SUB, false));
        numTable.addView(ntTitle);
        numTable.addView(tv("本表只算特号 01–49（合计 " + Calc.fmt(tabTotal) + " 元）；平特/连肖/三中三另算，当前自留 "
                + Calc.fmt(pteKept) + " 元" + (pteKept > 0 ? "，开出来还要再赔这块" : ""), 11, C_SUB, false));
        LinearLayout two = new LinearLayout(this);
        two.setOrientation(LinearLayout.HORIZONTAL);
        two.setPadding(0, dp(4), 0, 0);
        LinearLayout colA = new LinearLayout(this);
        colA.setOrientation(LinearLayout.VERTICAL);
        LinearLayout colB = new LinearLayout(this);
        colB.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams cl = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        cl.rightMargin = dp(10);
        colA.setLayoutParams(cl);
        colB.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        List<Integer> nos = new ArrayList<>();
        for (int n = 1; n <= 49; n++) nos.add(n);
        nos.sort((x, y) -> {
            double p = b.bets.get(x), q = b.bets.get(y);
            if (p != q) return p > q ? -1 : 1;
            return x - y;
        });
        int half = (nos.size() + 1) / 2;
        for (LinearLayout col : new LinearLayout[]{colA, colB}) {
            LinearLayout hd = new LinearLayout(this);
            hd.setOrientation(LinearLayout.HORIZONTAL);
            hd.setPadding(0, 0, 0, dp(2));
            TextView h1 = tv("号 注额→自留 飞", 11, 0xFF999999, false);
            h1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            hd.addView(h1);
            hd.addView(tv("开出净盈亏", 11, 0xFF999999, false));
            View hdiv = new View(this);
            hdiv.setBackgroundColor(0xFFEEEEEE);
            col.addView(hd);
            col.addView(hdiv, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        }
        for (int i = 0; i < nos.size(); i++) {
            int n = nos.get(i);
            double nb = b.bets.get(n);
            double self = Math.min(nb, capTab);
            double f = Math.max(0, nb - self);
            double net = tabKept - self * Calc.PAY_SPECIAL;
            boolean noBet = nb <= 0;
            LinearLayout wrap = new LinearLayout(this);
            wrap.setOrientation(LinearLayout.VERTICAL);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(0, dp(2), 0, dp(2));
            LinearLayout leftG = new LinearLayout(this);
            leftG.setOrientation(LinearLayout.HORIZONTAL);
            leftG.setGravity(Gravity.CENTER_VERTICAL);
            leftG.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            TextView lb = tv(String.format("%02d%s", n, Z.of(n)), 12, noBet ? 0xFFBBBBBB : C_TXT, !noBet);
            lb.setMinWidth(dp(26));
            leftG.addView(lb);
            TextView mid = tv(Calc.fmt(nb) + "→" + Calc.fmt(self), 12, 0xFFBBBBBB, false);
            leftG.addView(mid);
            if (f > 0) leftG.addView(tv(" 飞" + Calc.fmt(f), 12, C_RED, false));
            if (noBet) leftG.addView(tv(" 没人买", 12, 0xFFBBBBBB, false));
            row.addView(leftG);
            row.addView(tv((net >= 0 ? "+" : "") + Calc.fmt(net), 12, net >= 0 ? C_GREEN : C_RED, true));
            wrap.addView(row);
            View div = new View(this);
            div.setBackgroundColor(0xFFF7F7F7);
            wrap.addView(div, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
            (i < half ? colA : colB).addView(wrap);
        }
        two.addView(colA);
        two.addView(colB);
        numTable.addView(two);
        numTable.addView(tv("红＝开出来亏，绿＝赚；注额→自留，飞是该号飞出去的钱；按注额从大到小排，左列接右列；灰字「没人买」的号开出来全赚自留金。",
                11, C_SUB, false));
        numTable.addView(tv("这张表按当前阈值从零算（每号留 " + Calc.fmt(capTab) + "），不看早前已飞过多少；所以这里的自留总额可能跟上面「自留现金」不一样，两者口径不同，别对不上就以为错了。",
                12, 0xFFB45309, false));

        // ⑨b 风险体检 · 削峰（专业版同文案：建议落点 / 盘形 / 阈值 / 本盘建议 / 开奖后按号算 / 自动稳健）
        List<Double> vals = new ArrayList<>();
        double sumAll = 0, maxBet = 0;
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            if (nb > 0) { vals.add(nb); sumAll += nb; }
            if (nb > maxBet) maxBet = nb;
        }
        vals.sort(Double::compare);
        double med = 0;
        if (!vals.isEmpty()) {
            int m = vals.size();
            med = (m % 2 == 1) ? vals.get(m / 2) : (vals.get(m / 2 - 1) + vals.get(m / 2)) / 2.0;
        }
        int medCnt = 0;
        for (double v : vals) if (Math.abs(v - med) <= 5) medCnt++;
        double dBase = med;
        if (medCnt < 5 && !vals.isEmpty()) {
            int bestCnt = -1, best0 = 0;
            for (double v : vals) {
                int k = (int) Math.floor(v / 10) * 10;
                int c = 0;
                for (double w : vals) if (Math.floor(w / 10) * 10 == k) c++;
                if (c > bestCnt) { bestCnt = c; best0 = k; }
            }
            dBase = best0 + 5;
        }
        double dShare = sumAll > 0 ? maxBet / sumAll * 100 : 0;
        String dShape = (dShare >= 30 || vals.size() < 20) ? "畸形"
                : (dShare >= 20 || vals.size() < 30) ? "偏态"
                : (dShare >= 10 || vals.size() < 40) ? "中等" : "均衡";
        double baseKept = sumAll, baseFlown = 0;
        double baseWorst = sumAll - Calc.PAY_SPECIAL * maxBet;
        double[] lv = new double[]{95, 90, 85, 80, 78, 70, 63, 55, 47, 40, 30, 21};
        double optM = 0, optWorst = 0, optFlown = 0, optKept = 0;
        double bestM = 0, bestWorst = -1e18, bestKept = 0, bestFlown = 0;
        boolean optFound = false, broken = false;
        for (double m : lv) {
            if (m >= maxBet) continue;
            double keptM = 0, flownM = 0, maxKM = 0;
            for (int n = 1; n <= 49; n++) {
                double nb = b.bets.get(n);
                if (nb <= 0) continue;
                double k = Math.min(nb, m);
                keptM += k;
                flownM += nb - k;
                if (k > maxKM) maxKM = k;
            }
            double worstM = keptM - Calc.PAY_SPECIAL * maxKM;
            double lineM = keptM / Calc.PAY_SPECIAL;
            if (worstM > bestWorst) { bestWorst = worstM; bestM = m; bestKept = keptM; bestFlown = flownM; }
            if (broken) continue;
            double df = flownM - baseFlown;
            double e = df > 0 ? (worstM - baseWorst) / df : 0;
            if (lineM >= dBase && e >= 5) { optM = m; optWorst = worstM; optFlown = flownM; optKept = keptM; optFound = true; }
            else broken = true;
        }
        if (!optFound && bestM > 0) { optM = bestM; optWorst = bestWorst; optFlown = bestFlown; optKept = bestKept; }

        double breakeven = Math.max(0, (keptCash - ptePayout - lxPayout) / Calc.PAY_SPECIAL);
        int overCnt = 0;
        for (int n = 1; n <= 49; n++) {
            double nb0 = b.bets.get(n);
            if (nb0 > 0 && nb0 > breakeven) overCnt++;
        }
        LinearLayout health = new LinearLayout(this);
        health.setOrientation(LinearLayout.VERTICAL);
        health.setPadding(0, dp(8), 0, dp(4));
        health.addView(tv("风险体检 · 削峰", 13, C_TXT, true));
        if (optFound && optM > 0 && optM < 100) {
            double curFlown = Math.max(0, b.total - b.kept(cap));
            double curWorst = b.kept(cap) - Calc.PAY_SPECIAL * Math.min(maxBet, cap);
            double dFl = curFlown - optFlown, dW = curWorst - optWorst;
            LinearLayout sug = new LinearLayout(this);
            sug.setOrientation(LinearLayout.HORIZONTAL);
            sug.setGravity(Gravity.CENTER_VERTICAL);
            sug.addView(tv("建议 ", 11, C_SUB, false));
            final double om = optM;
            TextView big = tv(Calc.fmt(optM), 23, 0xFF1677FF, true);
            big.setOnClickListener(v -> {
                store.setCutPick(om);
                store.setCutMode("cut");
                store.setCap(om);
                store.setAutoStable(false);
                renderRisk(store.todayOrders(curShop));
            });
            sug.addView(big);
            sug.addView(tv("最坏 ", 12, 0xFF666666, false));
            sug.addView(tv(Calc.fmt(optWorst), 12, C_RED, true));
            sug.addView(tv("　飞 ", 12, 0xFF666666, false));
            sug.addView(tv(Calc.fmt(optFlown) + " 元", 12, C_TXT, true));
            TextView chip = tv("最优落点", 10, C_GREEN, false);
            GradientDrawable chipBg = new GradientDrawable();
            chipBg.setColor(Color.TRANSPARENT);
            chipBg.setStroke(dp(1), C_GREEN);
            chipBg.setCornerRadius(dp(3));
            chip.setBackground(chipBg);
            chip.setPadding(dp(4), 0, dp(4), 0);
            LinearLayout.LayoutParams chipLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            chipLp.leftMargin = dp(6);
            sug.addView(chip, chipLp);
            health.addView(sug);
            if (dFl > 0.5) {
                double ce = dW > 0 ? dW / dFl : 99;
                health.addView(tv("从 " + Calc.fmt(maxBet) + " 再削要多飞 " + Calc.fmt(dFl) + " 元，只换回 "
                        + Calc.fmt(dW) + " 元安全（每飞 1 元换 " + String.format("%.1f", ce) + " 元）", 11, C_SUB, false));
            } else if (dFl < -0.5) {
                health.addView(tv("当前 " + Calc.fmt(maxBet) + " 比建议少飞 " + Calc.fmt(-dFl) + " 元，最坏多亏 "
                        + Calc.fmt(-dW) + " 元；按建议补上更划算", 11, C_SUB, false));
            } else {
                health.addView(tv("当前 " + Calc.fmt(maxBet) + " 已是最优落点，不用动", 11, C_GREEN, false));
            }
        } else if (optFound && optM == 100) {
            health.addView(tv("建议 不削 — 吃最大 " + Calc.fmt(maxBet) + " 元/号 已守住基准，再往下削都是白飞", 12, C_TXT, false));
        } else if (bestM > 0) {
            health.addView(tv("每号留到 " + Calc.fmt(dBase) + " 才安全（盘面中位注额），现在做不到：最划算的 "
                    + Calc.fmt(bestM) + " 档最坏 " + Calc.fmt(bestWorst) + "、每号只能留 "
                    + String.format("%.1f", bestKept / Calc.PAY_SPECIAL) + "，还差 "
                    + String.format("%.1f", dBase - bestKept / Calc.PAY_SPECIAL)
                    + " 元/号；再往下多飞也没多少改善，缺口只能加飞或拒单", 12, C_RED, false));
        } else {
            health.addView(tv("这盘怎么削都守不住（安全线 " + Calc.fmt(dBase) + " 元/号），削峰救不了，只能加飞或拒单",
                    12, C_RED, false));
        }
        if (optFound && optM > 0) {
            double nextUnder = 0;
            for (double lvq : lv) if (lvq < optM && lvq >= 21) { nextUnder = lvq; break; }
            if (nextUnder > 0) {
                double kU = 0, mU = 0;
                for (int n = 1; n <= 49; n++) {
                    double keepU = Math.min(b.bets.get(n), nextUnder);
                    kU += keepU;
                    if (keepU > mU) mU = keepU;
                }
                double lineU = mU > 0 ? kU / Calc.PAY_SPECIAL : 0;
                if (lineU >= dBase) {
                    health.addView(tv("再往下 " + Calc.fmt(nextUnder) + " 也守得住（每号能留 " + String.format("%.1f", lineU)
                            + " ≥ 安全线 " + Calc.fmt(dBase) + "）；号越分散越好削。", 11, C_GREEN, false));
                }
            }
        }
        health.addView(tv("盘形 " + dShape + " · 最重 " + heaviest + "号占 " + String.format("%.1f", dShare)
                + "% · " + vals.size() + "号有注 · 安全线 " + Calc.fmt(dBase) + " 元/号（中位注额）· 现在每号能留 "
                + String.format("%.1f", b.kept(cap) / Calc.PAY_SPECIAL) + " · 超线号 " + overCnt + "/49", 11, C_SUB, false));
        // 阈值输入行
        LinearLayout thRow = new LinearLayout(this);
        thRow.setOrientation(LinearLayout.HORIZONTAL);
        thRow.setGravity(Gravity.CENTER_VERTICAL);
        thRow.setPadding(0, dp(2), 0, dp(2));
        thRow.addView(tv("阈值", 11, C_SUB, false));
        TextView thIn = tv(cap <= 0 ? "0" : Calc.fmt(cap), 12, 0xFF1677FF, true);
        thIn.setPadding(dp(4), dp(2), dp(4), dp(2));
        thIn.setBackgroundColor(0xFFF1F5F9);
        thRow.addView(thIn, new LinearLayout.LayoutParams(dp(66), ViewGroup.LayoutParams.WRAP_CONTENT));
        thIn.setOnClickListener(view -> {
            EditText et = new EditText(this);
            et.setSingleLine(true);
            et.setTextSize(15);
            et.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
            et.setText(cap <= 0 ? "" : Calc.fmt(cap));
            new android.app.AlertDialog.Builder(this)
                    .setTitle("阈值录入（每号最多自留，元）")
                    .setView(et)
                    .setPositiveButton("确定", (dg, w) -> {
                        try {
                            double v = Double.parseDouble(et.getText().toString().trim());
                            store.setCap(v);
                            renderRisk(store.todayOrders(curShop));
                            toast("阈值已改为每号留 " + Calc.fmt(v) + " 元");
                        } catch (Exception ignored) {
                        }
                    })
                    .setNegativeButton("取消", null)
                    .show();
        });
        thRow.addView(tv("元/号", 11, C_SUB, false));
        thRow.addView(tv("（与飞单统计同一个数，改哪边都一样）", 10, 0xFF999999, false));
        health.addView(thRow);
        if (bestM > 0 && bestWorst > -1e17) {
            final double bm = bestM;
            boolean curIsBest = Math.abs(cap - bestM) < 0.01;
            TextView link = tv(curIsBest
                    ? "本盘建议 " + Calc.fmt(bestM) + " 档（亏最少 " + Calc.fmt(bestWorst) + "）· 当前已用"
                    : "本盘建议 " + Calc.fmt(bestM) + " 档（亏最少 " + Calc.fmt(bestWorst) + "）· 点一下直接填",
                    11, curIsBest ? C_GREEN : 0xFF1677FF, false);
            if (!curIsBest) link.setOnClickListener(v -> {
                store.setCap(bm);
                store.setAutoStable(false);
                renderRisk(store.todayOrders(curShop));
                toast("阈值已改为每号留 " + Calc.fmt(bm) + " 元");
            });
            health.addView(link);
        }
        int noBet = 0, smallWin = 0, smallLose = 0, bigLose = 0;
        double band = 0;
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            double self = cap > 0 ? Math.min(nb, cap) : 0;
            double net = b.kept(cap) - self * Calc.PAY_SPECIAL;
            if (self <= 0) noBet++;
            else if (net > 0.5) { smallWin++; band = Math.max(band, net); }
        }
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            double self = cap > 0 ? Math.min(nb, cap) : 0;
            double net = b.kept(cap) - self * Calc.PAY_SPECIAL;
            if (self > 0 && net <= -0.5) { if (-net <= band) smallLose++; else bigLose++; }
        }
        LinearLayout postRow = new LinearLayout(this);
        postRow.setOrientation(LinearLayout.HORIZONTAL);
        postRow.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout postWrap = new LinearLayout(this);
        postWrap.setOrientation(LinearLayout.HORIZONTAL);
        postWrap.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        postWrap.addView(tv("开奖后按号算 ", 10, C_SUB, false));
        postWrap.addView(tv("纯赚 " + noBet, 12, C_GREEN, false));
        postWrap.addView(tv("号 ", 10, C_SUB, false));
        postWrap.addView(tv("小赚 " + smallWin, 12, C_GREEN, false));
        postWrap.addView(tv("号 ", 10, C_SUB, false));
        postWrap.addView(tv("小亏 " + smallLose, 12, 0xFFE67E22, false));
        postWrap.addView(tv("号 ", 10, C_SUB, false));
        postWrap.addView(tv("大亏 " + bigLose, 12, C_RED, false));
        postWrap.addView(tv("号", 10, C_SUB, false));
        postRow.addView(postWrap);
        android.widget.CheckBox autoChk = new android.widget.CheckBox(this);
        autoChk.setText("自动稳健（自动切到最优落点）");
        autoChk.setTextSize(10);
        autoChk.setTextColor(0xFF888888);
        autoChk.setChecked(store.autoStable());
        final double autoM = optM > 0 ? optM : bestM;
        autoChk.setOnCheckedChangeListener((cb, checked) -> {
            store.setAutoStable(checked);
            if (checked) {
                if (!store.sp().contains("prev_th_before_auto")) store.sp().edit().putFloat("prev_th_before_auto", (float) cap).apply();
                if (autoM > 0) store.setCap(autoM);
            } else {
                if (store.sp().contains("prev_th_before_auto")) {
                    store.setCap(store.sp().getFloat("prev_th_before_auto", (float) cap));
                    store.sp().edit().remove("prev_th_before_auto").apply();
                }
            }
            renderRisk(store.todayOrders(curShop));
        });
        postRow.addView(autoChk);
        health.addView(postRow);

        // ⑨c 挑模式：两模式共用下面一张号码表（与专业版 switchCutMode 同文案）
        LinearLayout cutBlock = new LinearLayout(this);
        cutBlock.setOrientation(LinearLayout.VERTICAL);
        cutBlock.setPadding(0, dp(8), 0, dp(4));
        cutBlock.addView(tv("挑模式（两模式共用下面这张号码表）", 13, C_TXT, true));
        LinearLayout btnRow = new LinearLayout(this);
        btnRow.setOrientation(LinearLayout.HORIZONTAL);
        String tagRaw = cap <= 30 ? "稳·亏少" : (cap >= 60 ? "留多·赚多亏多" : "折中");
        String tagCut = cutPick <= 30 ? "稳·亏少" : (cutPick >= 60 ? "留多·赚多亏多" : "折中");
        String[][] btnDef = new String[][]{
                {"raw", "按录单阈值 " + Calc.fmt(cap) + " 元/号\n" + ("raw".equals(mode) ? "✓ 正在用 · " : "") + tagRaw},
                {"cut", "按削峰档 " + Calc.fmt(cutPick) + " 元/号\n" + ("cut".equals(mode) ? "✓ 正在用 · " : "") + tagCut}
        };
        for (String[] bd : btnDef) {
            final String mkey = bd[0];
            boolean on = mode.equals(mkey);
            TextView btn = tv(bd[1], 13, on ? Color.WHITE : 0xFF999999, true);
            btn.setGravity(Gravity.CENTER);
            btn.setPadding(dp(4), dp(9), dp(4), dp(9));
            GradientDrawable mbg = new GradientDrawable();
            mbg.setCornerRadius(dp(8));
            if (on) {
                int c = "raw".equals(mkey) ? 0xFF333333 : 0xFF1677FF;
                mbg.setColor(c);
                mbg.setStroke(dp(2), c);
            } else {
                mbg.setColor(0xFFFFFFFF);
                mbg.setStroke(dp(1), 0xFFDDDDDD);
            }
            btn.setBackground(mbg);
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            blp.rightMargin = dp(8);
            btn.setOnClickListener(v -> {
                store.setCutMode(mkey);
                if ("cut".equals(mkey)) store.setCap(store.cutPick());
                renderRisk(store.todayOrders(curShop));
            });
            btnRow.addView(btn, blp);
        }
        cutBlock.addView(btnRow);
        cutBlock.addView(tv("下面号码表当前按 " + ("cut".equals(mode) ? "削峰档" : "录单阈值") + " " + Calc.fmt(capTab) + " 元/号 计算",
                12, C_TXT, false));
        if (Math.abs(cap - cutPick) < 0.01) {
            cutBlock.addView(tv("两边都是 " + Calc.fmt(cap) + " 元/号，个数一样，所以点哪个按钮号码表都不会变。想换档位就点下面那张档位卡。",
                    11, 0xFFB45309, false));
        }
        cutBlock.addView(tv("数字越小＝每号自留越少、飞得越多＝越稳；数字越大＝留得越多＝赚也多大、亏也多大。",
                11, C_SUB, false));

        // ⑨d 挑一档（只列比当前档更低的档位，与专业版同口径；专业版仅在「按削峰档」模式才显示）
        if ("cut".equals(mode)) {
        double topCut = Math.min(maxBet, capTab);
        cutBlock.addView(tv("挑一档（数字＝削到该值后的最坏净盈亏；完全不削是 " + Calc.fmt(baseWorst) + "）", 12, C_SUB, false));
        LinearLayout gA = new LinearLayout(this);
        gA.setOrientation(LinearLayout.VERTICAL);
        LinearLayout gB = new LinearLayout(this);
        gB.setOrientation(LinearLayout.VERTICAL);
        LinearLayout gWrap = new LinearLayout(this);
        gWrap.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        glp.rightMargin = dp(6);
        gA.setLayoutParams(glp);
        gB.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        gWrap.addView(gA);
        gWrap.addView(gB);
        List<Double> cards = new ArrayList<>();
        cards.add(100.0);
        for (double m : lv) if (m < topCut) cards.add(m);
        int cA = (cards.size() + 1) / 2;
        double lineM = 0;
        for (int i2 = 0; i2 < cards.size(); i2++) {
            final double m = cards.get(i2);
            double keptM = 0, flownM = 0, maxKM = 0;
            for (int n = 1; n <= 49; n++) {
                double nb = b.bets.get(n);
                if (nb <= 0) continue;
                double k = m >= 100 ? nb : Math.min(nb, m);
                keptM += k;
                flownM += nb - k;
                if (k > maxKM) maxKM = k;
            }
            double worstM = keptM - Calc.PAY_SPECIAL * maxKM;
            double df = flownM - baseFlown;
            double eff = df > 0 ? (worstM - baseWorst) / df : 0;
            if (m < 100 && eff >= 5) lineM = m;
            int nMove = 0;
            for (int n = 1; n <= 49; n++) if (b.bets.get(n) > m) nMove++;
            final double fm = m >= 100 ? 0 : m;
            boolean sel = Math.abs(capTab - (m >= 100 ? topCut : m)) < 0.01;
            boolean isOpt = m >= 100 ? false : Math.abs(m - optM) < 0.01;
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable cbg = new GradientDrawable();
            cbg.setCornerRadius(dp(6));
            cbg.setColor(isOpt ? 0xFFF0FDF4 : (sel ? 0xFFEEF4FF : 0xFFFAFAFA));
            cbg.setStroke(dp(1), isOpt ? C_GREEN : (sel ? 0xFF1677FF : 0xFFEEEEEE));
            card.setBackground(cbg);
            card.setPadding(dp(6), dp(5), dp(6), dp(5));
            LinearLayout.LayoutParams clp2 = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            clp2.setMargins(0, 0, 0, dp(4));
            card.setLayoutParams(clp2);
            LinearLayout line1 = new LinearLayout(this);
            line1.setOrientation(LinearLayout.HORIZONTAL);
            line1.setGravity(Gravity.CENTER_VERTICAL);
            line1.addView(tv(m >= 100 ? "不削" : Calc.fmt(m), 13, C_TXT, sel || isOpt));
            if (isOpt) {
                TextView optTag = tv("最优", 9, C_GREEN, false);
                optTag.setPadding(dp(2), 0, 0, 0);
                line1.addView(optTag);
            }
            line1.addView(new View(this), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            line1.addView(tv((worstM >= 0 ? "+" : "") + Calc.fmt(worstM), 12, worstM >= 0 ? C_GREEN : C_RED, true));
            card.addView(line1);
            card.addView(tv("自留 " + Calc.fmt(keptM) + " · 飞 " + Calc.fmt(flownM), 11, C_SUB, false));
            if (fm > 0) card.addView(tv("多飞1元换" + String.format("%.1f", eff) + "元安全", 11,
                    eff >= 5 ? C_GREEN : (eff >= 2 ? 0xFFB45309 : C_RED), false));
            card.addView(tv(m >= 100 ? "动 " + nMove + " 号" : "要动 " + nMove + " 个号（超过这档的号飞掉）", 11, C_SUB, false));
            card.setOnClickListener(v -> {
                store.setCutPick(fm == 0 ? 100 : fm);
                store.setCutMode("cut");
                store.setCap(fm == 0 ? 100 : fm);
                store.setAutoStable(false);
                renderRisk(store.todayOrders(curShop));
                toast(fm == 0 ? "已设为不削" : "阈值已改为每号留 " + Calc.fmt(fm) + " 元");
            });
            (i2 < cA ? gA : gB).addView(card);
        }
        cutBlock.addView(gWrap);
        // 我能扛 → 算档位 / ≤20% / ≤40%
        final double fMaxBet = maxBet, fSumAll = sumAll;
        final Board fB = b;
        final double fPtePay = ptePayout, fLxPay = lxPayout;
        LinearLayout tolRow = new LinearLayout(this);
        tolRow.setOrientation(LinearLayout.HORIZONTAL);
        tolRow.setGravity(Gravity.CENTER_VERTICAL);
        tolRow.addView(tv("我能扛", 12, C_SUB, false));
        final EditText tolIn = new EditText(this);
        tolIn.setSingleLine(true);
        tolIn.setTextSize(13);
        tolIn.setHint("填金额");
        tolIn.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED);
        tolIn.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        tolRow.addView(tolIn);
        TextView tolBtn = tv("算档位", 13, Color.WHITE, true);
        tolBtn.setGravity(Gravity.CENTER);
        tolBtn.setBackgroundColor(0xFF333333);
        tolBtn.setPadding(dp(12), dp(6), dp(12), dp(6));
        tolBtn.setOnClickListener(v -> {
            double v2;
            try { v2 = Math.abs(Double.parseDouble(tolIn.getText().toString().trim())); } catch (Exception e) { toast("先填一个你能扛的亏损金额，比如 1500"); return; }
            if (v2 <= 0) { toast("先填一个你能扛的亏损金额，比如 1500"); return; }
            double hit = 0;
            for (int m = (int) Math.floor(fMaxBet); m >= 1; m--) {
                double k = 0, mk = 0;
                for (int n = 1; n <= 49; n++) {
                    double nb = fB.bets.get(n);
                    if (nb <= 0) continue;
                    double keep = Math.min(nb, m);
                    k += keep;
                    if (keep > mk) mk = keep;
                }
                if (-(k - Calc.PAY_SPECIAL * mk) <= v2) { hit = m; break; }
            }
            if (hit > 0) {
                store.setCutPick(hit);
                store.setCutMode("cut");
                store.setCap(hit);
                store.setAutoStable(false);
                renderRisk(store.todayOrders(curShop));
                toast("阈值已改为每号留 " + Calc.fmt(hit) + " 元");
            } else {
                toast("削到 1 元/号 也扛不住 " + Calc.fmt(v2) + " 元，这盘只能靠飞单摊尾部。");
            }
        });
        tolRow.addView(tolBtn);
        String[] pct = new String[]{"≤20%", "≤40%"};
        final double[] pctRate = new double[]{0.2, 0.4};
        for (int i3 = 0; i3 < 2; i3++) {
            final double rate = pctRate[i3];
            final String pctLabel = pct[i3];
            TextView pb = tv(pctLabel, 11, 0xFF666666, false);
            pb.setPadding(dp(7), dp(5), dp(7), dp(5));
            pb.setBackgroundColor(0xFFFFFFFF);
            pb.setOnClickListener(v -> {
                double tgt = -fSumAll * rate - (fPtePay + fLxPay);
                double hit = 0;
                for (int m = (int) Math.floor(fMaxBet); m >= 0; m--) {
                    double k = 0, mk = 0;
                    for (int n = 1; n <= 49; n++) {
                        double nb = fB.bets.get(n);
                        if (nb <= 0) continue;
                        double keep = Math.min(nb, m);
                        k += keep;
                        if (keep > mk) mk = keep;
                    }
                    if ((k - Calc.PAY_SPECIAL * mk) + fPtePay + fLxPay >= tgt) { hit = m; break; }
                }
                store.setCutPick(hit);
                store.setCutMode("cut");
                store.setCap(hit);
                store.setAutoStable(false);
                renderRisk(store.todayOrders(curShop));
                toast("阈值已改为每号留 " + Calc.fmt(hit) + " 元（" + pctLabel + "）");
            });
            LinearLayout.LayoutParams plp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            plp.leftMargin = dp(6);
            tolRow.addView(pb, plp);
        }
        cutBlock.addView(tolRow);
        if (lineM > 0) {
            double lk = 0, lf = 0, lmk = 0;
            for (int n = 1; n <= 49; n++) {
                double nb = b.bets.get(n);
                if (nb <= 0) continue;
                double keep = Math.min(nb, lineM);
                lk += keep;
                lf += nb - keep;
                if (keep > lmk) lmk = keep;
            }
            double lworst = lk - Calc.PAY_SPECIAL * lmk;
            double lline = lk / Calc.PAY_SPECIAL;
            boolean safe = lline >= dBase;
            cutBlock.addView(tv("最划算的是 " + Calc.fmt(lineM) + " 档（每多飞 1 元能换回 5 元以上安全）：最坏 " + Calc.fmt(lworst)
                    + "、每号能留 " + String.format("%.1f", lline) + "，"
                    + (safe ? "已够安全线 " + Calc.fmt(dBase)
                    : "离安全线 " + Calc.fmt(dBase) + " 还差 " + String.format("%.1f", dBase - lline) + "，只是亏得少些，不算安全")
                    + "；再往下就不值了", 12, safe ? C_GREEN : 0xFFB45309, false));
        } else {
            cutBlock.addView(tv("这盘再怎么削，每多飞 1 元也换不回 5 元安全，飞单不划算", 12, 0xFFB45309, false));
        }
        }

        riskBox.addView(health);
        riskBox.addView(cutBlock);
        riskBox.addView(numTable);
        riskBox.addView(renderSimBody(today));
        riskBox.addView(flyHead);
        riskBox.addView(flyBody);
    }

    /** 某阈值下的最坏净盈亏（与专业版 worstAt 同口径） */
    private double riskWorstAt(Board b, double T, double pteFly, double lxFly, double otherPayout) {
        double fly = 0;
        for (int n = 1; n <= 49; n++) fly += Math.max(0, b.bets.get(n) - T);
        double kept = b.total + b.other - fly - pteFly - lxFly;
        double maxKept = T > 0 ? Math.min(maxBetRisk(b), T) : 0;
        return kept - maxKept * Calc.PAY_SPECIAL - otherPayout;
    }

    private double maxBetRisk(Board b) {
        double mx = 0;
        for (int n = 1; n <= 49; n++) if (b.bets.get(n) > mx) mx = b.bets.get(n);
        return mx > 0 ? mx : 100;
    }

    /** 特号持仓明细（专业版行格式：号+生肖 / 注额(飞) / 净盈亏） */
    private void fillSpecTable(LinearLayout box, Board b, double cap, double keptCash) {
        LinearLayout two = new LinearLayout(this);
        two.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout colA = new LinearLayout(this);
        colA.setOrientation(LinearLayout.VERTICAL);
        LinearLayout colB = new LinearLayout(this);
        colB.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams cl = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        cl.rightMargin = dp(10);
        colA.setLayoutParams(cl);
        colB.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        List<Integer> nos = new ArrayList<>();
        for (int n = 1; n <= 49; n++) nos.add(n);
        nos.sort((x, y) -> {
            double p = b.bets.get(x), q = b.bets.get(y);
            if (p != q) return p > q ? -1 : 1;
            return x - y;
        });
        int half = (nos.size() + 1) / 2;
        for (int i = 0; i < nos.size(); i++) {
            int n = nos.get(i);
            double nb = b.bets.get(n);
            double self = Math.min(nb, cap);
            double fly = Math.max(0, nb - self);
            double net = keptCash - self * Calc.PAY_SPECIAL;
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(0, dp(2), 0, dp(2));
            TextView lb = tv(String.format("%02d%s", n, Z.of(n)), 12, nb > 0 ? C_TXT : 0xFFCCCCCC, false);
            lb.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            row.addView(lb);
            TextView mid = tv("", 12, nb > 0 ? 0xFF1A1A1A : 0xFFBBBBBB, false);
            if (nb <= 0) {
                mid.setText("-");
            } else if (fly > 0) {
                // 专业版：注额 12px 深灰，飞出去的 10px #999 跟在后面
                android.text.SpannableStringBuilder ms = new android.text.SpannableStringBuilder(Calc.fmt(nb));
                int st = ms.length();
                ms.append("飞").append(Calc.fmt(fly));
                ms.setSpan(new android.text.style.ForegroundColorSpan(0xFF999999), st, ms.length(),
                        android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                ms.setSpan(new android.text.style.RelativeSizeSpan(10f / 12f), st, ms.length(),
                        android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                mid.setText(ms);
            } else {
                mid.setText(Calc.fmt(nb));
            }
            mid.setGravity(Gravity.END);
            mid.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            row.addView(mid);
            row.addView(tv((net >= 0 ? "+" : "") + Calc.fmt(net), 12, nb > 0 ? (net >= 0 ? C_GREEN : C_RED) : 0xFFBBBBBB, false));
            (i < half ? colA : colB).addView(row);
        }
        two.addView(colA);
        two.addView(colB);
        box.addView(two);
    }

    /** 平特持仓表的一行 */
    private LinearLayout pteRow(int kind, String a, String b2, String c, String d2) {
        return pteRow(kind, a, b2, c, d2, kind == 0 ? C_SUB : C_TXT, kind == 0 ? C_SUB : C_RED);
    }

    private LinearLayout pteRow(int kind, String a, String b2, String c, String d2, int cColor, int dColor) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(2), 0, dp(2));
        int col = kind == 0 ? C_SUB : C_TXT;
        TextView t1 = tv(a, 12, col, kind == 0);
        t1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row.addView(t1);
        TextView t2 = tv(b2, 12, col, kind == 0);
        t2.setGravity(Gravity.END);
        t2.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row.addView(t2);
        TextView t3 = tv(c, 12, cColor, kind == 0);
        t3.setGravity(Gravity.END);
        t3.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row.addView(t3);
        TextView t4 = tv(d2, 12, dColor, kind == 0);
        t4.setGravity(Gravity.END);
        t4.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row.addView(t4);
        return row;
    }

    /** 三格之一 */
    private LinearLayout triCell(String label, String val, int color, String note) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackgroundColor(0xFFF8F9FA);
        c.setPadding(dp(8), dp(8), dp(8), dp(8));
        c.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        lp.rightMargin = dp(4);
        c.setLayoutParams(lp);
        c.addView(tv(label, 11, C_SUB, false));
        c.addView(tv(val, 16, color, true));
        c.addView(tv(note, 10, 0xFFBBBBBB, false));
        return c;
    }

    /** 折叠标题条 */
    private LinearLayout foldHead(String text) {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable hb = new GradientDrawable();
        hb.setColor(0xFFF5F5F5);
        hb.setCornerRadius(dp(8));
        hb.setStroke(dp(1), 0xFFDDDDDD);
        l.setBackground(hb);
        l.setPadding(dp(12), dp(8), dp(12), dp(8));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, dp(8), 0, dp(4));
        l.setLayoutParams(lp);
        l.addView(tv(text, 14, 0xFF333333, true));
        return l;
    }

    /** 想最坏亏不超过 target 时，每号最多留多少（二分试算，与专业版 findT 同法） */
    private double recommendCap(Board b, double target) {
        double maxBet = 0;
        for (double v : b.bets.values()) maxBet = Math.max(maxBet, v);
        if (maxBet <= 0) return 0;
        if (worstAt(b, target, 0) < target) return 0;
        if (worstAt(b, target, maxBet) >= target) return maxBet;
        double lo = 0, hi = maxBet;
        for (int i = 0; i < 30; i++) {
            double mid = (lo + hi) / 2;
            if (worstAt(b, target, mid) >= target) lo = mid; else hi = mid;
        }
        return Math.floor(lo);
    }

    private double worstAt(Board b, double target, double t) {
        double flySum = 0;
        double maxKept = 0;
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            flySum += Math.max(0, nb - t);
            maxKept = Math.max(maxKept, Math.min(nb, t));
        }
        return (b.total - flySum) - maxKept * Calc.PAY_SPECIAL - b.other;
    }

    private void renderUp(List<Order> today) {
        upBox.removeAllViews();
        Date now = new Date();
        double wk = store.upWeek(now);
        double td = store.upToday(now);
        double all = store.upTotal();
        upBox.addView(tv("本周盈亏（周一起）  " + signed(wk), 15, wk >= 0 ? C_GREEN : C_RED, true));
        upBox.addView(tv("今日盈亏  " + signed(td), 12, td >= 0 ? C_GREEN : C_RED, false));
        upBox.addView(tv("历史累计  " + signed(all), 11, C_SUB, false));

        Draw d = store.draw(curShop);
        if (d.regular.size() == 6 && !today.isEmpty()) {
            Settle.Result r = Settle.of(Board.of(today), store.cap(), today, d, store.pingteMult());
            upBox.addView(tv("本期飞走 " + Calc.fmt(r.flyOut)
                    + "　命中赔回 " + Calc.fmt(r.flyBack)
                    + "　结算 " + signed(-r.delta), 13, C_TXT, true));
            if (!r.hits.isEmpty()) {
                for (String h : r.hits) upBox.addView(tv("  " + h, 11, C_SUB, false));
            }
        } else {
            upBox.addView(tv("录上开奖才出本期结算", 11, C_SUB, false));
        }
    }


    // ---------- 首页视觉 ----------
    private int ballColor(int n) {
        int[] red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46};
        int[] blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48};
        for (int r : red) if (r == n) return 0xFFE74C3C;
        for (int b : blue) if (b == n) return 0xFF3498DB;
        return 0xFF27AE60;
    }

    private View ball(int n) {
        TextView t = new TextView(this);
        t.setText(String.format("%02d", n));
        t.setTextColor(0xFFFFFFFF);
        t.setTextSize(15);
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        t.setGravity(Gravity.CENTER);
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
        g.setShape(android.graphics.drawable.GradientDrawable.OVAL);
        g.setColor(ballColor(n));
        t.setBackground(g);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(40), dp(40));
        lp.rightMargin = dp(5);
        t.setLayoutParams(lp);
        return t;
    }

    private void renderBalls() {
        if (ballRow == null) return;
        ballRow.removeAllViews();
        Draw d = store.draw(curShop);
        if (d.regular.size() < 6) {
            ballRow.addView(tv("还没开奖，录了开奖这里出球", 12, C_SUB, false));
            return;
        }
        for (int n : d.regular) ballRow.addView(ball(n));
        ballRow.addView(ball(d.special));
    }

    private void tickClockOnce() {
        if (clockTxt != null && clockTxt.getText().length() == 0) tickClock();
    }

    /** 香港开奖条：有香港单 +（本次点过获取，或开奖在 24 小时内）才出现（专业版 hkDrawBar 同口径） */
    private void renderHkBar() {
        if (hkBar == null) return;
        List<Order> hkOrders = store.todayOrders("港");
        Draw hd = store.draw("港");
        if (hkOrders.isEmpty()) { hkBar.setVisibility(View.GONE); return; }
        boolean hasNums = hd.period > 0 && hd.regular.size() >= 6;
        boolean hasNext = hd.nextDraw > 0 && !hd.nextAt.isEmpty();
        if (!hasNums && !hasNext) { hkBar.setVisibility(View.GONE); return; }
        // 香港不是天天开：刚开完奖 24 小时内才自动摆出来，平时要手动点一次获取
        if (!hkBarShown && !hkFresh(hd.at)) { hkBar.setVisibility(View.GONE); return; }

        if (!hasNums) {
            // 网站已公布下期时间但还没开奖
            android.text.SpannableStringBuilder sb = new android.text.SpannableStringBuilder("香港 下期 ");
            int st = sb.length();
            sb.append(String.valueOf(hd.nextDraw)).append(" 期　").append(slice5(hd.nextAt))
                    .append("（未开奖）");
            sb.setSpan(new android.text.style.ForegroundColorSpan(0xFF888888), st, sb.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            hkBar.setText(sb);
            hkBar.setVisibility(View.VISIBLE);
            return;
        }
        StringBuilder b = new StringBuilder("香港 期" + hd.period + "　");
        for (int r : hd.regular) b.append(String.format("%02d", r)).append(" ");
        b.append("　特 ").append(String.format("%02d", hd.special));
        android.text.SpannableStringBuilder sb = new android.text.SpannableStringBuilder(b.toString());
        if (!hd.at.isEmpty()) {
            int st = sb.length();
            sb.append("　").append(slice5(hd.at));
            sb.setSpan(new android.text.style.ForegroundColorSpan(0xFFBBBBBB), st, sb.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        if (hasNext) {
            int st = sb.length();
            sb.append("　下期 ").append(String.valueOf(hd.nextDraw)).append(" 期 ").append(slice5(hd.nextAt));
            sb.setSpan(new android.text.style.ForegroundColorSpan(0xFF888888), st, sb.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        hkBar.setText(sb);
        hkBar.setVisibility(View.VISIBLE);
    }

    /** "2026-11-15 21:32:00" → "11-15 21:32"（专业版 slice(5,16) 同款） */
    private String slice5(String at) {
        return at.length() >= 16 ? at.substring(5, 16) : at;
    }

    /** 开奖在 24 小时内才算新鲜（专业版 hkDrawIsFresh） */
    private boolean hkFresh(String at) {
        if (at == null || at.isEmpty()) return false;
        try {
            java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.CHINA);
            Date t = f.parse(at);
            long gap = System.currentTimeMillis() - t.getTime();
            return gap >= 0 && gap < 24L * 3600 * 1000;
        } catch (Exception e) {
            return false;
        }
    }

    private void tickClock() {
        if (clockTxt == null) return;
        clockTxt.setText(new java.text.SimpleDateFormat("HH:mm:ss", Locale.CHINA).format(new Date()));
        clockTxt.postDelayed(this::tickClock, 1000);
    }

    /** 客户下拉：列出全部客户（可存多个），长按删除，与专业版 chip 的右键删除一致 */
    private void pickCustomer() {
        if (curDlg != null) { try { curDlg.dismiss(); } catch (Exception ignored) {} }
        final List<String> list = store.customers();
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(10), dp(4), dp(10), dp(4));
        for (final String name : list) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(8), dp(12), dp(8), dp(12));
            GradientDrawable rbg = new GradientDrawable();
            rbg.setColor(0xFFFFFFFF);
            rbg.setCornerRadius(dp(6));
            rbg.setStroke(dp(1), 0xFFEEEEEE);
            row.setBackground(rbg);
            LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            rlp.bottomMargin = dp(6);
            row.setLayoutParams(rlp);
            boolean on = name.equals(store.customer());
            TextView t = tv(name + (on ? " ✓" : ""), 14, on ? 0xFF111111 : 0xFF666666, on);
            t.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            row.addView(t);
            TextView cnt = tv(cntOf(name), 11, C_SUB, false);
            row.addView(cnt);
            row.setOnClickListener(v -> {
                store.setCustomer(name);
                dismissCurDlg();
                refresh();
            });
            row.setOnLongClickListener(v -> {
                if ("散客".equals(name)) { toast("「散客」是默认客户，不能删"); return true; }
                new android.app.AlertDialog.Builder(this)
                        .setMessage("删除客户「" + name + "」？\n只是从名单移除，已录的订单不动。")
                        .setPositiveButton("删除", (dd, ww) -> {
                            store.removeRoster(name);
                            if (name.equals(store.customer())) store.setCustomer("散客");
                            refresh();
                            toast("已从名单移除：" + name);
                        })
                        .setNegativeButton("取消", null)
                        .show();
                return true;
            });
            box.addView(row);
        }
        final android.app.AlertDialog[] holder = new android.app.AlertDialog[1];
        holder[0] = new android.app.AlertDialog.Builder(this)
                .setTitle("选客户（共 " + list.size() + " 个，长按可删）")
                .setView(box)
                .setNeutralButton("新客户", (d, w) -> askNewCustomer())
                .setPositiveButton("客户统计", (d, w) -> showCustStats())
                .setNegativeButton("取消", null)
                .create();
        curDlg = holder[0];
        holder[0].show();
    }

    /** 某客户今日单数文字 */
    private String cntOf(String name) {
        int n = 0;
        for (Order o : store.todayOrders(curShop)) {
            String c = o.customer == null || o.customer.isEmpty() ? "散客" : o.customer;
            if (c.equals(name)) n++;
        }
        return n > 0 ? n + "单" : "";
    }

    /** 客户统计：按客户汇总单数、注额、赔付、净 */
    private void showCustStats() {
        List<Order> today = store.todayOrders(curShop);
        Draw d = store.draw(curShop);
        if (today.isEmpty()) { toast("今天还没单"); return; }
        Map<String, Integer> cnt = new LinkedHashMap<>();
        Map<String, Double> amt = new LinkedHashMap<>();
        Map<String, Double> pay = new LinkedHashMap<>();
        for (Order o : today) {
            String c = o.customer == null || o.customer.isEmpty() ? "散客" : o.customer;
            cnt.put(c, cnt.getOrDefault(c, 0) + 1);
            amt.put(c, amt.getOrDefault(c, 0.0) + o.amount());
            pay.put(c, pay.getOrDefault(c, 0.0) + (d.regular.size() == 6 ? store.payoutOf(o, d) : 0));
        }
        StringBuilder b = new StringBuilder();
        b.append("今日 ").append(today.size()).append(" 单，").append(cnt.size()).append(" 个客户\n\n");
        List<String> list = new ArrayList<>(cnt.keySet());
        list.sort((x, y) -> Double.compare(amt.get(y), amt.get(x)));
        for (String c : list) {
            double a = amt.get(c), p = pay.get(c);
            b.append(c).append("（").append(cnt.get(c)).append(" 单）\n");
            b.append("  下注 ").append(Calc.fmt(a));
            if (d.regular.size() == 6) {
                b.append("　中奖 ").append(Calc.fmt(p));
                b.append("　盈利 ").append(signed(p - a));
            }
            b.append("\n");
        }
        b.append("\n合计下注 ").append(Calc.fmt(store.totalAmount(today)));
        if (d.regular.size() == 6) b.append("　合计中奖 ").append(Calc.fmt(store.totalPayout(today, d)));
        new android.app.AlertDialog.Builder(this)
                .setTitle("客户统计（" + (curShop.equals("澳") ? "澳门" : "香港") + "）")
                .setMessage(b.toString())
                .setPositiveButton("知道了", null)
                .show();
    }

    private void askNewCustomer() {
        final EditText et = new EditText(this);
        et.setHint("客户名");
        new android.app.AlertDialog.Builder(this)
                .setTitle("新客户")
                .setView(et)
                .setPositiveButton("确定", (d, w) -> {
                    String n = et.getText().toString().trim();
                    if (n.isEmpty()) return;
                    store.setCustomer(n);
                    refresh();
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void switchShop() {
        curShop = curShop.equals("澳") ? "港" : "澳";
        if (store != null) store.setShop(curShop);
        if (shopTxt != null) shopTxt.setText(curShop.equals("澳") ? "澳门🇲🇴 ▾" : "香港🇭🇰 ▾");
        refresh();
        toast(curShop.equals("澳") ? "切到澳门" : "切到香港");
    }

    /** 展开/收起某块 */
    private void toggleTag(String tag) {
        View v = root == null ? null : root.findViewWithTag(tag);
        if (v == null) { toast("这块还没做"); return; }
        v.setVisibility(v.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE);
    }

    /** 滚到某块 */
    private void scrollToTag(String tag) {
        View v = root == null ? null : root.findViewWithTag(tag);
        if (v == null) { toast("这块还没做"); return; }
        final int[] loc = new int[2];
        v.getLocationInWindow(loc);
        if (sv != null) sv.smoothScrollTo(0, Math.max(0, loc[1] - dp(10)));
    }


    /** 四个统计面板：AI统计 / 飞单统计 / 盈利统计 / 平特肖 */
    private void showStats(String key) {
        List<Order> today = store.todayOrders(curShop);
        Draw d = store.draw(curShop);
        StringBuilder b = new StringBuilder();
        if (today.isEmpty()) {
            toast("今天还没单");
            return;
        }

        if (key.equals("ai")) {
            Board bd = Board.of(today);
            int withBet = 0;
            double maxNb = 0; int maxNo = 0;
            for (Map.Entry<Integer, Double> e : bd.bets.entrySet()) {
                if (e.getValue() > 0) withBet++;
                if (e.getValue() > maxNb) { maxNb = e.getValue(); maxNo = e.getKey(); }
            }
            b.append("今日 ").append(today.size()).append(" 单\n");
            b.append("特号合计 ").append(Calc.fmt(bd.total)).append("\n");
            b.append("有注的号 ").append(withBet).append("/49\n");
            b.append("最重 ").append(String.format("%02d", maxNo)).append(" ").append(Calc.fmt(maxNb)).append("\n");
            b.append("平均每单 ").append(Calc.fmt(store.totalAmount(today) / today.size())).append("\n");
            b.append("非特号玩法 ").append(Calc.fmt(bd.other)).append(" 元");
        } else if (key.equals("profit")) {
            double amt = store.totalAmount(today);
            double pay = d.regular.size() == 6 ? store.totalPayout(today, d) : 0;
            b.append("今日收 ").append(Calc.fmt(amt)).append("\n");
            if (d.regular.size() == 6) {
                b.append("今日赔 ").append(Calc.fmt(pay)).append("\n");
                b.append("净 ").append(signed(amt - pay)).append("\n\n");
                Settle.Result r = Settle.of(Board.of(today), store.cap(), today, d, store.pingteMult());
                b.append("飞走 ").append(Calc.fmt(r.flyOut)).append("\n");
                b.append("上家赔回 ").append(Calc.fmt(r.flyBack)).append("\n");
                b.append("跟庄净 ").append(signed(store.totalAmount(today) - r.flyOut - pay + r.flyBack));
            } else {
                b.append("还没录开奖，只有收");
            }
        } else if (key.equals("fly")) {
            if (d.regular.size() != 6) { toast("先录开奖"); return; }
            Settle.Result r = Settle.of(Board.of(today), store.cap(), today, d, store.pingteMult());
            b.append("飞走 ").append(Calc.fmt(r.flyOut)).append("\n");
            b.append("命中赔回 ").append(Calc.fmt(r.flyBack)).append("\n");
            b.append("结算（上家赔你） ").append(signed(-r.delta)).append("\n");
            if (!r.hits.isEmpty()) {
                b.append("\n命中明细：\n");
                for (String h : r.hits) b.append(h).append("\n");
            }
        } else {
            // 平特肖：按生肖汇总
            Map<String, Double> byZ = new LinkedHashMap<>();
            for (Order o : today) {
                for (String c : o.codes) {
                    String z = Parse.zodiacOf(c);
                    if (z == null) continue;
                    byZ.put(z, byZ.getOrDefault(z, 0.0) + o.amount());
                }
            }
            if (byZ.isEmpty()) { toast("今天没有平特/生肖单"); return; }
            b.append("今天收的生肖注额：\n");
            List<Map.Entry<String, Double>> list = new ArrayList<>(byZ.entrySet());
            list.sort((x, y) -> Double.compare(y.getValue(), x.getValue()));
            for (Map.Entry<String, Double> e : list) {
                b.append("  ").append(e.getKey()).append("　").append(Calc.fmt(e.getValue())).append("\n");
            }
        }

        new android.app.AlertDialog.Builder(this)
                .setTitle(key.equals("ai") ? "AI统计" : key.equals("fly") ? "飞单统计"
                        : key.equals("profit") ? "盈利统计" : "平特肖")
                .setMessage(b.toString())
                .setPositiveButton("知道了", null)
                .show();
    }

    private void onGrid(String key) {
        switch (key) {
            case "arch": doArchive(); setPanel("hist"); break;
            case "clear":
                dismissCurDlg();
                if (inputBox != null) inputBox.setText("");
                if (saveMsg != null) { saveMsg.setText(""); saveMsg.setVisibility(View.GONE); }
                store.saveOrders(new ArrayList<Order>());
                store.clearFlown();          // 已飞登记属于当日订单，一起清，别留「没有订单还已飞600」
                // 清掉「本次已保存」回显、输入框内容、还开着的录单选择框
                if (saveMsg != null) { saveMsg.setText(""); saveMsg.setVisibility(View.GONE); }
                if (inputBox != null) inputBox.setText("");
                if (curDlg != null && curDlg.isShowing()) curDlg.dismiss();
                curDlg = null;
                refresh();
                toast("订单已清空（已飞登记一起清零）");
                setPanel("rank");
                break;
            case "hist": togglePanel("hist"); break;
            case "rank": togglePanel("rank"); break;
            case "ai": togglePanel("ai"); break;
            case "fly": togglePanel("fly"); break;
            case "profit": togglePanel("profit"); break;
            case "pte": togglePanel("pte"); renderPte(); break;
            default: break;
        }
    }

    /** 盈利统计的一格：13px 灰字 + 14px 加粗数值 */
    private TextView phead(String label, double v, int color) {
        android.text.SpannableStringBuilder sb = new android.text.SpannableStringBuilder(label);
        int st = sb.length();
        sb.append(Calc.fmt(v));
        sb.setSpan(new android.text.style.RelativeSizeSpan(14f / 13f), st, sb.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        sb.setSpan(new android.text.style.StyleSpan(Typeface.BOLD), st, sb.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        sb.setSpan(new android.text.style.ForegroundColorSpan(color), st, sb.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        TextView t = tv("", 13, 0xFF333333, false);
        t.setText(sb);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        t.setLayoutParams(lp);
        return t;
    }

    private String signed(double v) {
        return (v >= 0 ? "+" : "-") + Calc.fmt(Math.abs(v));
    }

    /** 常用客户快捷切换 */
    private void renderCustomers() {
        if (custRow == null) return;
        custRow.removeAllViews();
        List<String> list = store.customers();
        if (list.size() <= 1) return;      // 只有一个客户就不重复显示
        int n = 0;
        for (String c : list) {
            if (n++ >= 8) break;
            boolean on = c.equals(store.customer());
            Button b = tbtn(c, 15, on ? 0xFF333333 : 0xFFFFFFFF, on ? 0xFF333333 : 0xFFCCCCCC,
                    on ? 0xFFFFFFFF : 0xFF333333, 999, true);
            b.setOnClickListener(v -> {
                store.setCustomer(c);
                refresh();
            });
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            clp.rightMargin = dp(6);
            b.setPadding(dp(12), dp(5), dp(12), dp(5));
            custRow.addView(b, clp);
        }
    }

    private void renderSplit(List<Order> today) {
        Board b = Board.of(today);
        double cap = store.cap();
        double capPte = store.capPte();
        double capLx = store.capLx();
        boolean roundOn = store.flyRound();
        boolean autoDone = store.autoFly() || ("港".equals(curShop) && store.hkAutoFly());
        FlyBook.Ledger L = FlyBook.build(today, cap, capPte, capLx, roundOn, store.flown(), autoDone);
        splitBox.removeAllViews();

        // ① 阈值三框（专业版同一行：特号 [100]  平特 [0]  连肖 [0]）
        LinearLayout th = new LinearLayout(this);
        th.setOrientation(LinearLayout.HORIZONTAL);
        th.setGravity(Gravity.CENTER_VERTICAL);
        th.setPadding(0, dp(2), 0, dp(6));
        th.addView(thLabel("特号"));
        android.widget.EditText eSpec = capInput(cap);
        th.addView(eSpec);
        th.addView(thLabel("平特"));
        android.widget.EditText ePte = capInput(capPte);
        th.addView(ePte);
        th.addView(thLabel("连肖"));
        android.widget.EditText eLx = capInput(capLx);
        th.addView(eLx);
        Button apply = btn("应用", v -> {
            double a2 = parseNum(eSpec.getText().toString(), cap);
            double p2 = parseNum(ePte.getText().toString(), capPte);
            double l2 = parseNum(eLx.getText().toString(), capLx);
            store.setCap(a2); store.setCapPte(p2); store.setCapLx(l2);
            refresh();
        });
        apply.setTextSize(12);
        apply.setPadding(dp(10), 0, dp(10), 0);
        th.addView(apply, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(42)));
        splitBox.addView(th);
        splitBox.addView(tv("特=每个号最多留多少；平=每个平特肖留多少；连=连肖留多少。0 表示全飞", 10, C_SUB, false));
        // 4×2 网格：左列选产品（点一下看该产品明细），右列是操作（专业版同位置）
        String[][] grid = {{"特号", "spec"}, {"飞单目录", "dir"}, {"平特", "pte"}, {"重置已飞", "reset"},
                {"连肖", "lx"}, {"复制", "copy"}, {"二中二三中三", "em"}, {"确认飞单", "ok"}};
        final FlyBook.Ledger Lg = L;
        final boolean rg = roundOn;
        final double rSum = roundOn ? L.pendingRound : L.pending;
        for (int r = 0; r < 4; r++) {
            LinearLayout grow = new LinearLayout(this);
            grow.setOrientation(LinearLayout.HORIZONTAL);
            if (r > 0) grow.setPadding(0, dp(3), 0, 0);
            for (int c = 0; c < 2; c++) {
                String label = grid[r * 2 + c][0];
                String act = grid[r * 2 + c][1];
                Button gb = btn(label, v -> onFlyCell(act, Lg, rg, rSum));
                gb.setTextSize(13);
                boolean sel = act.equals(flyGroup);
                if (sel) {
                    gb.setTextColor(android.graphics.Color.WHITE);
                    gb.setBackgroundColor(0xFF1A1A1A);
                } else {
                    gb.setTextColor(0xFF333333);
                    gb.setBackgroundColor(android.graphics.Color.WHITE);
                    GradientDrawable gbg = new GradientDrawable();
                    gbg.setColor(android.graphics.Color.WHITE);
                    int bc = 0xFFCCCCCC, tc = 0xFF333333;
                    if ("reset".equals(act)) { bc = C_RED; tc = C_RED; }
                    if ("ok".equals(act)) { bc = C_GREEN; tc = C_GREEN; }
                    gbg.setStroke(dp(1), bc);
                    gbg.setCornerRadius(dp(6));
                    gb.setBackground(gbg);
                    gb.setTextColor(tc);
                }
                LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(0, dp(40), 1);
                if (c == 0) glp.rightMargin = dp(3); else glp.leftMargin = dp(3);
                grow.addView(gb, glp);
            }
            splitBox.addView(grow);
        }

        // 三条勾选（专业版原文）
        android.widget.CheckBox cbAuto = new android.widget.CheckBox(this);
        cbAuto.setText("即飞产品自动复制（连肖/二中二/三中三）");
        cbAuto.setTextSize(12);
        cbAuto.setTextColor(0xFF666666);
        cbAuto.setChecked(store.autoFly());
        cbAuto.setOnCheckedChangeListener((v, on) -> { store.setAutoFly(on); refresh(); });
        splitBox.addView(cbAuto);
        splitBox.addView(tv("勾选后这些产品自动默认已飞，仅用于统计客单赔付", 11, C_SUB, false));

        android.widget.CheckBox cbRound = new android.widget.CheckBox(this);
        cbRound.setText("金额凑整 5 元档");
        cbRound.setTextSize(12);
        cbRound.setTextColor(0xFF666666);
        cbRound.setChecked(store.flyRound());
        cbRound.setOnCheckedChangeListener((v, on) -> { store.setFlyRound(on); refresh(); });
        splitBox.addView(cbRound);
        splitBox.addView(tv("勾选后每个号就近凑到 5 的倍数（34→35、31→30、3→5），多飞的自付、少飞的自己留", 11, C_SUB, false));

        if ("港".equals(curShop)) {
            android.widget.CheckBox cbHk = new android.widget.CheckBox(this);
            cbHk.setText("香港单自动飞");
            cbHk.setTextSize(12);
            cbHk.setTextColor(0xFF666666);
            cbHk.setChecked(store.hkAutoFly());
            cbHk.setOnCheckedChangeListener((v, on) -> { store.setHkAutoFly(on); refresh(); });
            splitBox.addView(cbHk);
            splitBox.addView(tv("勾选后香港单直接默认已飞（转发上家），不跟澳门单混", 11, C_SUB, false));
        }

        if (L.total <= 0) {
            splitBox.addView(tv("还没有订单", 12, C_SUB, false));
            return;
        }

        // ② 当前阈值（专业版侧栏头：左标右三数，下面一条细线）
        LinearLayout curRow = new LinearLayout(this);
        curRow.setOrientation(LinearLayout.HORIZONTAL);
        curRow.setGravity(Gravity.CENTER_VERTICAL);
        curRow.setPadding(0, dp(8), 0, dp(3));
        TextView curLbl = tv("当前阈值", 13, 0xFF666666, false);
        curLbl.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        curRow.addView(curLbl);
        android.text.SpannableStringBuilder curVal = new android.text.SpannableStringBuilder(
                "特号 " + Calc.fmt(cap) + " ｜ 平特 " + Calc.fmt(capPte) + " ｜ 连肖 " + Calc.fmt(capLx));
        curVal.setSpan(new android.text.style.StyleSpan(android.graphics.Typeface.BOLD), 3, curVal.length(),
                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        TextView curTxt = tv(curVal.toString(), 13, C_TXT, false);
        curTxt.setText(curVal);
        curRow.addView(curTxt);
        splitBox.addView(curRow);
        View line1 = new View(this);
        line1.setBackgroundColor(0xFFEEEEEE);
        splitBox.addView(line1, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        // ③ 总单 ｜ 总飞出去（红）
        LinearLayout totRow = new LinearLayout(this);
        totRow.setOrientation(LinearLayout.HORIZONTAL);
        totRow.setPadding(0, dp(4), 0, 0);
        totRow.addView(tv("总单 ", 13, 0xFF666666, false));
        totRow.addView(tv(Calc.fmt(L.total), 13, C_TXT, true));
        totRow.addView(tv(" ｜ 总飞出去 ", 13, 0xFF666666, false));
        totRow.addView(tv(Calc.fmt(L.flyFull), 13, C_RED, true));
        splitBox.addView(totRow);

        // ④ 已飞 ｜ 本轮应飞（16px 红粗）
        LinearLayout flyRow = new LinearLayout(this);
        flyRow.setOrientation(LinearLayout.HORIZONTAL);
        flyRow.setGravity(Gravity.CENTER_VERTICAL);
        flyRow.setPadding(0, dp(2), 0, dp(4));
        flyRow.addView(tv("已飞 " + Calc.fmt(L.already) + " ｜ 本轮应飞", 13, 0xFF666666, false));
        TextView rnum = tv(" " + Calc.fmt(roundOn ? L.pendingRound : L.pending), 16, C_RED, true);
        flyRow.addView(rnum);
        splitBox.addView(flyRow);

        // ⑤ 飞单总目录（左未飞 / 右已飞，专业版双列同款）
        final java.util.List<FlyBook.Group> pend = L.groups;
        java.util.TreeMap<Double, java.util.List<String>> doneMap = new java.util.TreeMap<>(java.util.Collections.reverseOrder());
        double doneSum = 0;
        for (FlyBook.Line ln : L.lines) {
            double d = Math.min(ln.done, ln.full);
            if (d <= 0.01) continue;
            doneSum += d;
            java.util.List<String> ks = doneMap.get(d);
            if (ks == null) { ks = new ArrayList<>(); doneMap.put(d, ks); }
            ks.add(ln.key);
        }
        LinearLayout titleBar = new LinearLayout(this);
        titleBar.setOrientation(LinearLayout.HORIZONTAL);
        titleBar.setGravity(Gravity.CENTER_VERTICAL);
        GradientDrawable tb = new GradientDrawable();
        tb.setColor(0xFFF0F0F0);
        tb.setCornerRadii(new float[]{dp(4), dp(4), dp(4), dp(4), 0, 0, 0, 0});
        titleBar.setBackground(tb);
        titleBar.setPadding(dp(5), dp(3), dp(5), dp(3));
        TextView tbL = tv("飞单总目录（待飞" + Calc.fmt(roundOn ? L.pendingRound : L.pending) + " / 已飞" + Calc.fmt(doneSum) + "）",
                12, C_TXT, true);
        tbL.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        titleBar.addView(tbL);
        if (roundOn) titleBar.addView(tv("凑整5", 10, C_RED, false));
        splitBox.addView(titleBar);

        LinearLayout cols = new LinearLayout(this);
        cols.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout colL = new LinearLayout(this);
        colL.setOrientation(LinearLayout.VERTICAL);
        colL.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        LinearLayout colR = new LinearLayout(this);
        colR.setOrientation(LinearLayout.VERTICAL);
        colR.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        View vdiv = new View(this);
        vdiv.setBackgroundColor(0xFFEEEEEE);
        cols.addView(colL);
        cols.addView(vdiv, new LinearLayout.LayoutParams(dp(1), ViewGroup.LayoutParams.MATCH_PARENT));
        cols.addView(colR);
        splitBox.addView(cols);

        TextView hL = tv("未飞 " + Calc.fmt(roundOn ? L.pendingRound : L.pending)
                + (roundOn && Math.abs(L.pendingRound - L.pending) >= 0.01
                ? "（原" + Calc.fmt(L.pending) + "，" + (L.pendingRound > L.pending ? "多飞" : "省")
                + Calc.fmt(Math.abs(L.pendingRound - L.pending)) + "）" : ""), 10, C_RED, true);
        hL.setPadding(dp(5), dp(2), dp(5), dp(2));
        colL.addView(hL);

        if (pend.isEmpty()) {
            TextView e1 = tv("全部飞完", 11, 0xFFCCCCCC, false);
            e1.setGravity(Gravity.CENTER);
            e1.setPadding(0, dp(4), 0, dp(4));
            colL.addView(e1);
        } else {
            for (FlyBook.Group g : pend) {
                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.TOP);
                row.setPadding(dp(5), dp(2), dp(5), dp(2));
                StringBuilder b2 = new StringBuilder();
                for (String k : g.keys) b2.append(k).append(" ");
                TextView tl = tv(b2.toString(), 12, C_TXT, false);
                tl.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                row.addView(tl);
                row.addView(tv("各" + Calc.fmt(g.amt), 12, C_SUB, false));
                row.addView(tv("　" + Calc.fmt(g.amt * g.keys.size()), 12, C_RED, true));
                colL.addView(row);
                View d1 = new View(this);
                d1.setBackgroundColor(0xFFF5F5F5);
                colL.addView(d1, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
            }
        }

        LinearLayout hRrow = new LinearLayout(this);
        hRrow.setOrientation(LinearLayout.HORIZONTAL);
        hRrow.setGravity(Gravity.CENTER_VERTICAL);
        hRrow.setPadding(dp(5), dp(2), dp(5), dp(2));
        TextView hR = tv("已飞 " + Calc.fmt(doneSum), 10, C_GREEN, true);
        hR.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        hRrow.addView(hR);
        TextView copyDone = tv("复制已飞", 10, C_GREEN, true);
        GradientDrawable cdb = new GradientDrawable();
        cdb.setColor(android.graphics.Color.WHITE);
        cdb.setStroke(dp(1), C_GREEN);
        cdb.setCornerRadius(dp(4));
        copyDone.setBackground(cdb);
        copyDone.setPadding(dp(5), dp(1), dp(5), dp(1));
        copyDone.setOnClickListener(v -> copyFlownList(doneMap));
        hRrow.addView(copyDone);
        colR.addView(hRrow);

        if (doneMap.isEmpty()) {
            TextView e2 = tv("暂无", 11, 0xFFCCCCCC, false);
            e2.setGravity(Gravity.CENTER);
            e2.setPadding(0, dp(4), 0, dp(4));
            colR.addView(e2);
        } else {
            for (java.util.Map.Entry<Double, java.util.List<String>> en : doneMap.entrySet()) {
                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.TOP);
                row.setPadding(dp(5), dp(2), dp(5), dp(2));
                TextView tl = tv(String.join(" ", en.getValue()), 12, C_SUB, false);
                tl.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                row.addView(tl);
                row.addView(tv("各" + Calc.fmt(en.getKey()), 12, 0xFFBBBBBB, false));
                row.addView(tv("　" + Calc.fmt(en.getKey() * en.getValue().size()), 12, C_SUB, false));
                colR.addView(row);
            }
        }

        // 选中产品的明细（专业版点左列按钮看的就是这块）
        java.util.List<FlyBook.Line> sel = new ArrayList<>();
        for (FlyBook.Line ln : L.lines) {
            boolean hit = "spec".equals(flyGroup) ? ln.key.matches("\\d{2}")
                    : "pte".equals(flyGroup) ? ln.key.startsWith("平特")
                    : "lx".equals(flyGroup) ? ln.key.startsWith("连肖")
                    : ln.key.startsWith("二中二");
            if (hit) sel.add(ln);
        }
        String gName = "spec".equals(flyGroup) ? "特号" : "pte".equals(flyGroup) ? "平特" : "lx".equals(flyGroup) ? "连肖" : "二中二三中三";
        TextView dh = tv(gName + "明细（" + sel.size() + " 行）", 11, 0xFF666666, true);
        dh.setPadding(0, dp(6), 0, dp(2));
        splitBox.addView(dh);
        if (sel.isEmpty()) {
            splitBox.addView(tv("这一类今天没有要飞的", 11, 0xFFCCCCCC, false));
        } else {
            for (FlyBook.Line ln : sel) {
                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setPadding(dp(5), dp(2), dp(5), dp(2));
                TextView kl = tv(ln.key, 12, C_TXT, true);
                kl.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                row.addView(kl);
                row.addView(tv("该飞 " + Calc.fmt(ln.full), 12, C_SUB, false));
                if (ln.done > 0.01) row.addView(tv("　已飞 " + Calc.fmt(ln.done), 12, C_GREEN, false));
                row.addView(tv("　还该飞 " + Calc.fmt(roundOn ? Split.round5(ln.round) : ln.round), 12, C_RED, true));
                splitBox.addView(row);
            }
        }

        // ⑥ 手动登记飞单（专业版同一块）
        View spacer = new View(this);
        splitBox.addView(spacer, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(6)));
        View dash = new View(this);
        dash.setBackgroundColor(0xFFDDDDDD);
        splitBox.addView(dash, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        TextView mHead = tv("手动登记飞单（一行一个：22 140 或 平特虎 1000）", 10, 0xFF666666, true);
        mHead.setPadding(0, dp(6), 0, dp(3));
        splitBox.addView(mHead);
        final android.widget.EditText mIn = new android.widget.EditText(this);
        mIn.setTextSize(12);
        mIn.setHint("22 140\n34 90\n平特虎 1000");
        mIn.setMinLines(3);
        mIn.setGravity(Gravity.TOP);
        GradientDrawable mInBg = new GradientDrawable();
        mInBg.setColor(android.graphics.Color.WHITE);
        mInBg.setStroke(dp(1), 0xFFDDDDDD);
        mInBg.setCornerRadius(dp(6));
        mIn.setBackground(mInBg);
        mIn.setPadding(dp(5), dp(5), dp(5), dp(5));
        mIn.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));
        splitBox.addView(mIn);
        LinearLayout mBtns = new LinearLayout(this);
        mBtns.setOrientation(LinearLayout.HORIZONTAL);
        mBtns.setPadding(0, dp(4), 0, 0);
        Button mApply = btn("按清单登记已飞", v -> applyManualFly(mIn.getText().toString()));
        mApply.setTextColor(android.graphics.Color.WHITE);
        mApply.setTextSize(12);
        mApply.setBackgroundColor(0xFF000000);
        mBtns.addView(mApply, new LinearLayout.LayoutParams(0, dp(36), 1));
        Button mClear = btn("清空", v -> mIn.setText(""));
        mClear.setTextSize(12);
        mClear.setTextColor(0xFF666666);
        mClear.setBackgroundColor(android.graphics.Color.WHITE);
        GradientDrawable mcb = new GradientDrawable();
        mcb.setColor(android.graphics.Color.WHITE);
        mcb.setStroke(dp(1), 0xFFCCCCCC);
        mcb.setCornerRadius(dp(6));
        mClear.setBackground(mcb);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
        clp.leftMargin = dp(5);
        mBtns.addView(mClear, clp);
        splitBox.addView(mBtns);


    }

    private String flyGroup = "spec";
    /** 当前正在显示的录入歧义弹窗，清空/清除时要能关掉它 */
    private android.app.AlertDialog curDlg;


    private TextView thLabel(String s) {
        TextView t = tv(s, 15, C_TXT, false);
        t.setPadding(0, 0, dp(6), 0);
        return t;
    }

    /** 4×2 网格点击：左列切产品明细，右列是操作 */
    private void onFlyCell(String act, FlyBook.Ledger L, boolean roundOn, double rSum) {
        if ("spec".equals(act) || "pte".equals(act) || "lx".equals(act) || "em".equals(act)) {
            flyGroup = act;
            refresh();
            return;
        }
        if ("dir".equals(act)) {
            StringBuilder b = new StringBuilder();
            for (FlyBook.Group g : L.groups) {
                for (String k : g.keys) b.append(k).append(" ");
                b.append(" 各").append(Calc.fmt(g.amt)).append("\n");
            }
            if (b.length() == 0) b.append("没有待飞的号");
            android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
            ad.setTitle("飞单目录（待飞 " + Calc.fmt(roundOn ? L.pendingRound : L.pending) + " 元）");
            ad.setMessage(b.toString().trim());
            ad.setPositiveButton("知道了", null);
            ad.show();
            return;
        }
        if ("reset".equals(act)) {
            android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
            ad.setMessage("重置已飞记录？\n（新一期开始时用，清空后重新从全部订单算飞单）");
            ad.setPositiveButton("确定", (d, w) -> { store.clearFlown(); refresh(); });
            ad.setNegativeButton("取消", null);
            ad.show();
            return;
        }
        if ("copy".equals(act)) {
            copyFly(L.groups, roundOn ? L.pendingRound : L.pending);
            return;
        }
        // 确认飞单
        android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
        ad.setTitle("确认飞单");
        ad.setMessage("确认本轮飞单 " + Calc.fmt(rSum) + " 元？\n确认后这些金额标记为已飞，下次只算新增部分。");
        ad.setPositiveButton("确定", (d, w) -> {
            java.util.Map<String, Double> fm = store.flown();
            FlyBook.commit(L, fm, roundOn);
            store.setFlown(fm);
            refresh();
            toast("已记入已飞 " + Calc.fmt(rSum));
        });
        ad.setNegativeButton("取消", null);
        ad.show();
    }

    /** 复制已飞清单（专业版 copyFlownList：重置前留底） */
    private void copyFlownList(java.util.TreeMap<Double, java.util.List<String>> doneMap) {
        if (doneMap.isEmpty()) { toast("还没有已飞记录，没什么可复制的"); return; }
        StringBuilder b = new StringBuilder();
        double sum = 0;
        for (java.util.Map.Entry<Double, java.util.List<String>> en : doneMap.entrySet()) {
            b.append(String.join(" ", en.getValue())).append(" 各").append(Calc.fmt(en.getKey())).append("\n");
            sum += en.getKey() * en.getValue().size();
        }
        b.append("合计 ").append(Calc.fmt(sum));
        android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (cm != null) cm.setPrimaryClip(android.content.ClipData.newPlainText("已飞", b.toString()));
        toast("已复制已飞清单 " + Calc.fmt(sum) + " 元");
    }

    /** 手动登记已飞（专业版 applyManualFlyList 同规则：一行一个「号 金额」） */
    private void applyManualFly(String text) {
        if (text == null || text.trim().isEmpty()) { toast("先把清单贴进输入框"); return; }
        int cnt = 0, bad = 0;
        double sum = 0;
        java.util.Map<String, Double> fm = store.flown();
        for (String line : splitLines(text)) {
            String[] w = line.trim().split("\\s+");
            if (w.length < 2) { bad++; continue; }
            double amt;
            try { amt = Double.parseDouble(w[w.length - 1]); } catch (Exception e) { bad++; continue; }
            if (amt <= 0) { bad++; continue; }
            StringBuilder key = new StringBuilder();
            for (int i = 0; i < w.length - 1; i++) {
                if (i > 0) key.append(" ");
                key.append(w[i]);
            }
            String code = key.toString();
            if (code.matches("\\d{1,2}")) code = String.format("%02d", Integer.parseInt(code));
            Double old = fm.get(code);
            fm.put(code, (old == null ? 0 : old) + amt);
            cnt++;
            sum += amt;
        }
        if (cnt == 0) { toast("没认出来。格式要一行一个，如「22 140」或「平特虎 1000」"); return; }
        store.setFlown(fm);
        refresh();
        toast("已登记 " + cnt + " 个号，合计 " + Calc.fmt(sum) + " 元" + (bad > 0 ? "\n有 " + bad + " 行没认出来，已跳过" : ""));
    }

    /** 复制飞单目录到剪贴板（格式：01 02 各35，最后一行合计） */
    private void copyFly(java.util.List<FlyBook.Group> gs, double sum) {
        StringBuilder b = new StringBuilder();
        for (FlyBook.Group g : gs) b.append(g.text()).append("\n");
        b.append("合计 ").append(Calc.fmt(sum));
        android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (cm != null) cm.setPrimaryClip(android.content.ClipData.newPlainText("飞单", b.toString()));
        toast("已复制飞单 " + Calc.fmt(sum) + " 元，共 " + gs.size() + " 行");
    }

    /** 排行榜 + 号码表 */
    private void renderBoard(List<Order> today) {
        Board b = Board.of(today);
        double cap = store.cap();
        boardSum.setText("特号合计 " + Calc.fmt(b.total) + "　自留 " + Calc.fmt(b.kept(cap))
                + "　飞 " + Calc.fmt(b.total - b.kept(cap))
                + "　最坏 " + (b.worst(cap) >= 0 ? "+" : "") + Calc.fmt(b.worst(cap)));
        boardSum.setTextColor(C_TXT);

        // 专业版排行榜：49 号两列表（左 25 / 右 24），列 # / 特号 / 金额
        rankBox.removeAllViews();
        numBoxL.removeAllViews();
        numBoxR.removeAllViews();
        List<int[]> rk = b.rank();          // 按金额降序，含没人买的号
        if (rk.isEmpty()) { rankBox.addView(tv("还没有特号单", 12, C_SUB, false)); return; }

        int half = 25;
        addRankTable(numBoxL, rk, 0, Math.min(half, rk.size()));
        addRankTable(numBoxR, rk, half, rk.size());
    }

    /** 一张 # / 特号 / 金额 表 */
    private void addRankTable(LinearLayout col, List<int[]> rk, int from, int to) {
        if (from >= to) return;
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setPadding(0, dp(2), 0, dp(4));
        TextView h1 = tv("#", 11, C_SUB, false);
        h1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 14f / 100));
        head.addView(h1);
        TextView h2 = tv("特号", 11, C_SUB, false);
        h2.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 42f / 100));
        head.addView(h2);
        TextView h3 = tv("金额", 11, C_SUB, false);
        h3.setGravity(Gravity.END);
        h3.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 44f / 100));
        head.addView(h3);
        col.addView(head);

        int idx = from + 1;
        for (int i = from; i < to; i++, idx++) {
            int[] r = rk.get(i);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(0, dp(2), 0, dp(2));
            TextView c1 = tv(String.valueOf(idx), 12, C_SUB, false);
            c1.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 14f / 100));
            row.addView(c1);
            int wc = Z.wave(r[0]);
            int c2c = wc == 1 ? 0xFFDC2626 : wc == 2 ? 0xFF1E40AF : wc == 3 ? 0xFF166534 : 0xFF333333;
            TextView c2 = tv(String.format("%02d", r[0]) + Z.of(r[0]), 14, c2c, true);
            c2.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 42f / 100));
            row.addView(c2);
            TextView c3 = tv(Calc.fmt(r[1]), 13, r[1] > 0 ? 0xFF333333 : 0xFFBBBBBB, r[1] > 0);
            c3.setGravity(Gravity.END);
            c3.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 44f / 100));
            row.addView(c3);
            col.addView(row);
        }
    }

    /** 已录入：按客户分组，显示下注/中奖/盈亏 + 撤单/复制，下面列每笔明细 */
    private void renderOrdersList(List<Order> today, Draw d) {
        if (orderList == null) return;
        orderList.removeAllViews();
        List<Order> list = new ArrayList<>(today);
        if (list.isEmpty()) {
            orderList.addView(tv("还没有订单，上面录一单就会显示在这里", 12, C_SUB, false));
            if (orderCum2 != null) orderCum2.setText("");
            return;
        }

        // 按客户分组（下单金额大的在前）
        Map<String, List<Order>> g = new LinkedHashMap<>();
        for (Order o : list) {
            String c = o.customer == null || o.customer.isEmpty() ? "散客" : o.customer;
            if (!g.containsKey(c)) g.put(c, new ArrayList<Order>());
            g.get(c).add(o);
        }
        final double[] bet = {0}, win = {0};
        for (Order o : list) bet[0] += o.amount();
        for (Order o : list) {
            Calc.Result r = Calc.win(o, d, store.pingteMult());
            win[0] += r.total;
        }
        if (orderCum2 != null) {
            double net = win[0] - bet[0];
            orderCum2.setText(list.size() + " 单　下注 " + Calc.fmt(bet[0])
                    + "　" + (net >= 0 ? "盈利 " : "亏损 ") + Calc.fmt(Math.abs(net)));
            orderCum2.setTextColor(net >= 0 ? C_GREEN : C_RED);
        }

        // 开奖记录块（专业版订单记录页顶部就有）
        LinearLayout drawBlk = new LinearLayout(this);
        drawBlk.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable dgbg = new GradientDrawable();
        dgbg.setColor(0xFFFAFAFA);
        dgbg.setCornerRadius(dp(8));
        dgbg.setStroke(dp(1), 0xFFEEEEEE);
        drawBlk.setBackground(dgbg);
        drawBlk.setPadding(dp(8), dp(8), dp(8), dp(8));
        LinearLayout.LayoutParams dblp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        dblp.setMargins(0, 0, 0, dp(8));
        drawBlk.setLayoutParams(dblp);
        LinearLayout drawTop = new LinearLayout(this);
        drawTop.setOrientation(LinearLayout.HORIZONTAL);
        drawTop.setGravity(Gravity.CENTER_VERTICAL);
        drawTop.addView(tv("开奖记录", 12, 0xFF666666, true));
        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(0, 1, 1));
        drawTop.addView(spacer);
        if (d.regular.size() == 6) {
            Button undo = tbtn("撤销", 12, 0xFFFFFFFF, 0xFFCF1322, 0xFFCF1322, 4, false);
            undo.setOnClickListener(v -> {
                store.clearDraw(curShop);
                refresh();
                toast("开奖记录已撤销");
            });
            undo.setPadding(dp(10), dp(2), dp(10), dp(2));
            undo.setMinWidth(0);
            undo.setMinimumWidth(0);
            drawTop.addView(undo);
        }
        drawBlk.addView(drawTop);
        if (d.regular.size() == 6) {
            StringBuilder regs = new StringBuilder();
            for (int x : d.regular) regs.append(String.format("%02d", x)).append(" ");
            drawBlk.addView(tv((d.period > 0 ? "期" + d.period + "　" : "")
                    + "特" + String.format("%02d", d.special) + "(" + Z.of(d.special) + ")　平特 " + regs.toString().trim(),
                    13, C_TXT, false));
        } else {
            drawBlk.addView(tv("暂无开奖记录", 12, C_SUB, false));
        }
        orderList.addView(drawBlk);

        for (Map.Entry<String, List<Order>> e : g.entrySet()) {
            final String cust = e.getKey();
            List<Order> os = e.getValue();
            double cb = 0, cw = 0;
            for (Order o : os) {
                cb += o.amount();
                cw += Calc.win(o, d, store.pingteMult()).total;
            }

            LinearLayout blk = new LinearLayout(this);
            blk.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable gbg = new GradientDrawable();
            gbg.setColor(0xFFFFFFFF);
            gbg.setCornerRadius(dp(8));
            gbg.setStroke(dp(1), 0xFFEEEEEE);
            blk.setBackground(gbg);
            LinearLayout.LayoutParams glp2 = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            glp2.setMargins(0, 0, 0, dp(6));
            blk.setLayoutParams(glp2);

            LinearLayout hd = new LinearLayout(this);
            hd.setOrientation(LinearLayout.HORIZONTAL);
            hd.setGravity(Gravity.CENTER_VERTICAL);
            hd.setPadding(dp(8), dp(8), dp(8), dp(8));
            hd.setBackgroundColor(0xFFF8F9FA);
            LinearLayout hleft = new LinearLayout(this);
            hleft.setOrientation(LinearLayout.VERTICAL);
            hleft.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            LinearLayout h1 = new LinearLayout(this);
            h1.setOrientation(LinearLayout.HORIZONTAL);
            h1.addView(tv(cust, 14, C_TXT, true));
            h1.addView(tv(" (" + os.size() + "单)", 11, C_SUB, false));
            hleft.addView(h1);
            double cnet = cw - cb;
            android.text.SpannableStringBuilder bl = new android.text.SpannableStringBuilder();
            bl.append("下注 ").append(Calc.fmt(cb));
            bl.setSpan(new android.text.style.ForegroundColorSpan(C_TXT), 3, bl.length(), android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            bl.append("　中奖 ").append(Calc.fmt(cw));
            bl.setSpan(new android.text.style.ForegroundColorSpan(0xFFCF1322), bl.length() - Calc.fmt(cw).length(), bl.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            bl.append(cnet >= 0 ? "　盈利 " : "　亏损 ").append(Calc.fmt(Math.abs(cnet)));
            bl.setSpan(new android.text.style.ForegroundColorSpan(cnet >= 0 ? 0xFF16A34A : 0xFFCF1322),
                    bl.length() - Calc.fmt(Math.abs(cnet)).length(), bl.length(),
                    android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            TextView blTxt = tv("", 12, 0xFF666666, false);
            blTxt.setText(bl);
            hleft.addView(blTxt);
            hd.addView(hleft);

            Button delC = tbtn("撤单", 12, 0xFFFFFFFF, 0xFFCCCCCC, 0xFFCF1322, 4, false);
            delC.setOnClickListener(v -> confirmDelCust(cust));
            Button cpC = tbtn("复制", 12, 0xFFFFFFFF, 0xFFCCCCCC, 0xFF333333, 4, false);
            cpC.setOnClickListener(v -> copyCust(cust));
            delC.setPadding(dp(10), dp(2), dp(10), dp(2));
            cpC.setPadding(dp(10), dp(2), dp(10), dp(2));
            hd.addView(delC);
            LinearLayout.LayoutParams dlp2 = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            dlp2.leftMargin = dp(4);
            hd.addView(cpC, dlp2);
            blk.addView(hd);

            final LinearLayout detail = new LinearLayout(this);
            detail.setOrientation(LinearLayout.VERTICAL);
            detail.setVisibility(View.GONE);
            for (Order o : os) detail.addView(orderRow(o, d));
            TextView toggle = tv("展开详细清单 ▼", 11, C_SUB, false);
            toggle.setGravity(Gravity.CENTER);
            toggle.setPadding(0, dp(6), 0, 0);
            toggle.setOnClickListener(v -> {
                boolean show = detail.getVisibility() != View.VISIBLE;
                detail.setVisibility(show ? View.VISIBLE : View.GONE);
                toggle.setText(show ? "收起详细清单 ▲" : "展开详细清单 ▼");
            });
            blk.addView(toggle);
            blk.addView(detail);
            orderList.addView(blk);
        }
    }

    /** 撤掉某客户今日全部订单 */
    private void confirmDelCust(String cust) {
        new android.app.AlertDialog.Builder(this)
                .setTitle("撤单")
                .setMessage("把「" + cust + "」今天录的单全部删掉？")
                .setPositiveButton("确定", (d, w) -> {
                    for (Order o : store.todayOrders()) {
                        if (cust.equals(o.customer)) store.removeOrder(o.id);
                    }
                    refresh();
                    toast("已撤掉 " + cust + " 的单");
                })
                .setNegativeButton("取消", null).show();
    }

    /** 复制某客户的单到剪贴板 */
    private void copyCust(String cust) {
        StringBuilder b = new StringBuilder();
        double sum = 0;
        for (Order o : store.todayOrders()) {
            if (!cust.equals(o.customer)) continue;
            b.append(cust).append("　").append(codeLabel(o.codes)).append("　").append(Calc.fmt(o.amount())).append("\n");
            sum += o.amount();
        }
        b.append("合计 ").append(Calc.fmt(sum));
        copyText(b.toString());
        toast("已复制 " + cust + " 的单");
    }

    private View orderRow(Order o, Draw d) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(0, dp(5), 0, dp(5));

        // ① 原始行（与专业版一致：按 "; " 拆开逐行显示）
        String raw = o.raw == null ? "" : o.raw;
        String[] rl = raw.split("; ");
        boolean printed = false;
        for (String x : rl) {
            if (x.trim().isEmpty()) continue;
            row.addView(tv(x.trim(), 13, C_TXT, false));
            printed = true;
        }
        if (!printed) row.addView(tv(codeLabel(o.codes), 13, C_TXT, false));

        // ② 命中明细
        Calc.Result r = Calc.win(o, d, store.pingteMult());
        for (Calc.Line l : r.lines) row.addView(tv("命中: " + l.text(), 11, C_RED, false));

        // ③ 底行：时间 + 合计 + 删除
        LinearLayout bot = new LinearLayout(this);
        bot.setOrientation(LinearLayout.HORIZONTAL);
        bot.setGravity(Gravity.CENTER_VERTICAL);
        bot.setPadding(0, dp(4), 0, 0);
        String tm = new java.text.SimpleDateFormat("HH:mm", Locale.CHINA).format(new Date(o.ts));
        bot.addView(tv(tm, 11, C_SUB, false));
        TextView sum = tv("合计 " + Calc.fmt(o.amount()), 11, C_TXT, true);
        sum.setGravity(Gravity.END);
        sum.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        bot.addView(sum);
        Button del = tbtn("删除", 12, 0xFFF5F5F5, 0xFFCCCCCC, 0xFF666666, 4, false);
        del.setOnClickListener(v -> {
            store.removeOrder(o.id);
            refresh();
            toast("已删除");
        });
        del.setTextSize(12);
        del.setPadding(dp(8), 0, dp(8), 0);
        del.setMinWidth(0);
        del.setMinimumWidth(0);
        bot.addView(del);
        row.addView(bot);
        return row;
    }

    /** 订单里的玩法名：号码补「特」，组合码去掉冒号 */
    static String codeLabel(List<String> codes) {
        StringBuilder b = new StringBuilder();
        for (String c : codes) {
            if (b.length() > 0) b.append(" ");
            if (c.matches("\\d{1,2}")) b.append("特").append(c.length() == 1 ? "0" + c : c);
            else b.append(c.replace(":", ""));
        }
        return b.toString();
    }

    private String join(List<String> l, String sep) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < l.size(); i++) { if (i > 0) b.append(sep); b.append(l.get(i)); }
        return b.toString();
    }

    // ---------- 复制文本 ----------

    private String custText() { return Text.cust(store.customer(), store.todayOrders(curShop), store.draw(curShop), store.pingteMult()); }



    /** 香港池的单据文本（复制给上家） */
    private String hkText() {
        List<Order> hk = store.ordersOf("港");
        StringBuilder b = new StringBuilder();
        b.append("香港单　").append(hk.size()).append(" 笔　合计 ").append(Calc.fmt(store.totalAmount(hk))).append(" 元\n");
        for (Order o : hk) {
            b.append("· ").append(o.customer).append("　").append(o.raw).append("　")
                    .append(Calc.fmt(o.amount())).append(" 元\n");
        }
        if (hk.isEmpty()) b.append("（香港池还是空的）");
        return b.toString();
    }

    private String upText() { return Text.up(store.todayOrders(curShop), store.draw(curShop), store.pingteMult()); }



    private void copyText(String text) {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("order", text));
            toast("已复制");
        } catch (Exception e) {
            toast("复制失败");
        }
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_LONG).show();
    }
}
