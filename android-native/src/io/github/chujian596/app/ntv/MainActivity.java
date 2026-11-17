package io.github.chujian596.app.ntv;

import android.app.AlertDialog;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
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
    private LinearLayout resultBox;
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
    private TextView hkBar;

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
        getWindow().setStatusBarColor(0xFFF7F7F7);
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
        l.setBackgroundColor(C_CARD);
        l.setPadding(dp(14), dp(12), dp(14), dp(12));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, 0, 0, dp(10));
        l.setLayoutParams(lp);
        if (tag != null) l.setTag(tag);
        return l;
    }

    private android.widget.EditText capInput(double v) {
        android.widget.EditText e = new android.widget.EditText(this);
        e.setText(v > 0 ? Calc.fmt(v) : "0");
        e.setTextSize(12);
        e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        lp.setMargins(dp(2), 0, dp(2), 0);
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

    private void buildUI() {
        sv = new ScrollView(this);
        sv.setTag("scroll");
        sv.setBackgroundColor(C_BG);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(12), dp(12), dp(12), dp(24));
        sv.addView(root);
        setContentView(sv);

        // ---- 顶部汇总 ----
        LinearLayout head = card();
        LinearLayout hrow = new LinearLayout(this);
        hrow.setOrientation(LinearLayout.HORIZONTAL);
        hrow.setGravity(Gravity.CENTER_VERTICAL);
        summary = tv("", 16, C_TXT, true);
        summary.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        hrow.addView(summary);
        TextView cfgBtn = tv("⚙ 设置", 12, C_SUB, false);
        cfgBtn.setPadding(dp(8), dp(4), dp(4), dp(4));
        cfgBtn.setOnClickListener(v -> { toggleTag("cfg"); toggleTag("pays"); });
        hrow.addView(cfgBtn);
        head.addView(hrow);
        root.addView(head);

        // ---- 客户 / 时钟 / 店铺 ----
        LinearLayout cust = card();
        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        row1.setGravity(Gravity.CENTER_VERTICAL);
        custPick = tv("客户：散客 ▾", 15, C_TXT, true);
        custPick.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        custPick.setOnClickListener(v -> pickCustomer());
        row1.addView(custPick);
        clockTxt = tv("", 15, C_TXT, true);
        clockTxt.setGravity(Gravity.CENTER);
        clockTxt.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        row1.addView(clockTxt);
        shopTxt = tv("澳门 ▾", 15, C_TXT, true);
        shopTxt.setTag("shop");
        shopTxt.setGravity(Gravity.END);
        shopTxt.setOnClickListener(v -> switchShop());
        row1.addView(shopTxt);
        cust.addView(row1);
        custRow = new LinearLayout(this);
        custRow.setOrientation(LinearLayout.HORIZONTAL);
        custRow.setPadding(0, dp(8), 0, 0);
        cust.addView(custRow);
        root.addView(cust);

        // ---- 香港期号横条（有港彩开奖才显示）----
        hkBar = tv("", 12, C_SUB, false);
        hkBar.setPadding(dp(4), dp(2), dp(4), dp(6));
        hkBar.setVisibility(View.GONE);
        root.addView(hkBar);

        // ---- 订单输入 ----
        LinearLayout in = card();
        LinearLayout itop = new LinearLayout(this);
        itop.setOrientation(LinearLayout.HORIZONTAL);
        itop.setGravity(Gravity.CENTER_VERTICAL);
        TextView it1 = tv("订单输入区", 15, C_TXT, true);
        itop.addView(it1);
        orderCum = tv("", 12, C_SUB, false);
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
        inputBox.setTextSize(15);
        inputBox.setGravity(Gravity.TOP);
        inputBox.setBackgroundColor(0xFFFAFBFC);
        inputBox.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        inputBox.setPadding(dp(10), dp(8), dp(10), dp(8));
        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(96));
        ilp.topMargin = dp(2);
        inputBox.setLayoutParams(ilp);
        in.addView(inputBox);

        // 开奖行
        LinearLayout drawRow = new LinearLayout(this);
        drawRow.setOrientation(LinearLayout.HORIZONTAL);
        drawRow.setGravity(Gravity.CENTER_VERTICAL);
        drawRow.setPadding(0, dp(8), 0, 0);
        drawBox = tv("", 13, C_TXT, false);
        drawBox.setTag("draw");
        Draw d = store.draw(curShop);
        drawBox.setText(d.period > 0 ? drawLine(d) : "还没录开奖");
        drawBox.setPadding(dp(6), 0, dp(6), 0);
        drawBox.setGravity(Gravity.CENTER_VERTICAL);
        drawBox.setLayoutParams(new LinearLayout.LayoutParams(0, dp(40), 1));
        drawBox.setOnClickListener(v -> doDraw());
        drawRow.addView(drawBox);
        Button drAuto = btn("自动获取开奖", v -> autoFetch());
        drAuto.setTextSize(12);
        drAuto.setPadding(dp(6), 0, dp(6), 0);
        drAuto.setMinWidth(0);
        drAuto.setMinimumWidth(0);
        drAuto.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40)));
        drawRow.addView(drAuto);
        in.addView(drawRow);

        LinearLayout brow = new LinearLayout(this);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, dp(8), 0, 0);
        Button save = btn("保存", v -> doSave());
        Button manual = btn("手动录入", v -> doDraw());
        Button clear = btn("清空", v -> inputBox.setText(""));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        blp.rightMargin = dp(6);
        save.setLayoutParams(blp);
        manual.setLayoutParams(blp);
        clear.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        brow.addView(save);
        brow.addView(manual);
        brow.addView(clear);
        in.addView(brow);
        root.addView(in);

        // ---- 两个大按钮 ----
        LinearLayout bigRow = new LinearLayout(this);
        bigRow.setOrientation(LinearLayout.HORIZONTAL);
        bigRow.setPadding(0, 0, 0, dp(10));
        LinearLayout.LayoutParams bigLp = new LinearLayout.LayoutParams(0, dp(52), 1);
        bigLp.rightMargin = dp(6);
        Button bRank = btn("排行榜", v -> { toggleTag("board"); scrollToTag("board"); });
        bRank.setLayoutParams(bigLp);
        Button bOrders = btn("订单记录", v -> { toggleTag("orders"); scrollToTag("orders"); });
        bOrders.setLayoutParams(new LinearLayout.LayoutParams(0, dp(52), 1));
        bigRow.addView(bRank);
        bigRow.addView(bOrders);
        root.addView(bigRow);

        // ---- 功能网格 ----
        LinearLayout grid = card();
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
                Button gb = btn(cells[j][0], v -> onGrid(key));
                gb.setTextSize(13);
                LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(0, dp(46), 1);
                if (j < i + 3) glp.rightMargin = dp(6);
                gb.setLayoutParams(glp);
                gr.addView(gb);
            }
            grid.addView(gr);
        }
        root.addView(grid);

        // ---- 结算结果 ----
        resultBox = card("settle");
        resultBox.addView(tv("结算", 15, C_TXT, true));
        root.addView(resultBox);

        // ---- 订单列表 ----
        LinearLayout ol = card("orders");
        ol.addView(tv("今日订单", 15, C_TXT, true) );
        orderList = new LinearLayout(this);
        orderList.setOrientation(LinearLayout.VERTICAL);
        ol.addView(orderList);
        ol.addView(btn("归档并清空今日", v -> doArchive()));
        root.addView(ol);

        // ---- 补号模拟 ----
        LinearLayout sm = card("sim");
        sm.addView(tv("补号模拟", 15, C_TXT, true));
        sm.addView(tv("把注额最少的号补到指定金额，看最坏情况能拉回多少", 11, C_SUB, false));
        simBox = new LinearLayout(this);
        simBox.setOrientation(LinearLayout.VERTICAL);
        simBox.setPadding(0, dp(6), 0, 0);
        sm.addView(simBox);
        root.addView(sm);

        // ---- 历史归档 ----
        LinearLayout ah = card("archive");
        ah.addView(tv("历史归档", 15, C_TXT, true));
        archBox = new LinearLayout(this);
        archBox.setOrientation(LinearLayout.VERTICAL);
        archBox.setPadding(0, dp(6), 0, 0);
        ah.addView(archBox);
        root.addView(ah);

        // ---- 盘面：排行榜 + 号码表 ----
        LinearLayout bd = card("board");
        bd.addView(tv("盘面", 15, C_TXT, true));
        LinearLayout capRow = new LinearLayout(this);
        capRow.setOrientation(LinearLayout.HORIZONTAL);
        capRow.setGravity(Gravity.CENTER_VERTICAL);
        capRow.setPadding(0, dp(6), 0, 0);
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
        bd.addView(capRow);

        boardSum = tv("", 13, C_TXT, true);
        boardSum.setPadding(0, dp(8), 0, dp(4));
        bd.addView(boardSum);

        bd.addView(tv("排行榜（按特号注额）", 13, C_TXT, true));
        rankBox = new LinearLayout(this);
        rankBox.setOrientation(LinearLayout.VERTICAL);
        rankBox.setPadding(0, dp(4), 0, dp(10));
        bd.addView(rankBox);

        bd.addView(tv("号码表（每行＝这个号开出时特号这块的盈亏）", 13, C_TXT, true));
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
        bd.addView(twoCol);
        root.addView(bd);

        // ---- 削峰飞单 ----
        LinearLayout sp = card("split");
        sp.addView(tv("削峰飞单", 15, C_TXT, true));
        sp.addView(tv("超出「每号最多自留」的部分飞给上家，下面按当前阈值算", 11, C_SUB, false));
        splitBox = new LinearLayout(this);
        splitBox.setOrientation(LinearLayout.VERTICAL);
        splitBox.setPadding(0, dp(6), 0, 0);
        sp.addView(splitBox);
        root.addView(sp);

        // ---- 风控体检 ----
        LinearLayout rk = card("risk");
        rk.addView(tv("风控体检", 15, C_TXT, true));
        riskBox = new LinearLayout(this);
        riskBox.setOrientation(LinearLayout.VERTICAL);
        riskBox.setPadding(0, dp(6), 0, 0);
        rk.addView(riskBox);
        root.addView(rk);

        // ---- 上家（飞单）----
        LinearLayout up = card("up");
        up.addView(tv("上家（飞单）", 15, C_TXT, true));
        upBox = new LinearLayout(this);
        upBox.setOrientation(LinearLayout.VERTICAL);
        upBox.setPadding(0, dp(6), 0, 0);
        up.addView(upBox);
        root.addView(up);

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

        // ---- 复制 ----
        LinearLayout cp = card("copy");
        cp.addView(tv("对账文本", 15, C_TXT, true));
        LinearLayout cr = new LinearLayout(this);
        cr.setOrientation(LinearLayout.HORIZONTAL);
        cr.setPadding(0, dp(8), 0, 0);
        Button cc = btn("复制客户单", v -> copyText(custText()));
        Button cu = btn("复制上家单", v -> copyText(upText()));
        cc.setLayoutParams(blp2());
        cu.setLayoutParams(blp2());
        cr.addView(cc);
        cr.addView(cu);
        cp.addView(cr);
        root.addView(cp);

        // 面板默认收起，点按钮展开（与专业版一致）
        for (String t : new String[]{"settle", "orders", "sim", "archive", "board", "split", "risk", "up", "cfg", "pays", "copy"}) {
            View v = root.findViewWithTag(t);
            if (v != null) v.setVisibility(View.GONE);
        }
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
        new AlertDialog.Builder(this)
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
                .show();
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
            doSave(text);
        }));
        dlg.show();
    }

    private void doSave(String all) {
        // 客户名由顶部客户下拉维护，这里不再读输入框
        if (all.trim().isEmpty()) { toast("先输入订单"); return; }
        java.util.List<String[]> amb = new java.util.ArrayList<>();
        for (String line : splitLines(all)) {
            String[] w = Parse.detectWave(line);
            if (w != null) amb.add(new String[]{line, w[0], w[1]});
        }
        // 一项：三选项单框；多项：一次性全选完（与专业版两种形态一致）
        if (amb.size() == 1) { askWave(amb.get(0)[0], new String[]{amb.get(0)[1], amb.get(0)[2]}, all); return; }
        if (amb.size() > 1) { askMulti(amb, all); return; }
        List<String> lines = splitLines(all);
        int ok = 0;
        List<String> bad = new ArrayList<>();
        for (String line : lines) {
            try {
                Order o = Parse.parseLine(line);
                if (o == null) continue;
                o.customer = store.customer();
                o.shop = curShop;
                store.addOrder(o);
                ok++;
            } catch (Exception e) {
                bad.add(line + " → " + e.getMessage());
            }
        }
        inputBox.setText("");
        refresh();
        if (!bad.isEmpty()) {
            toast("保存 " + ok + " 笔，失败 " + bad.size() + " 行\n" + bad.get(0));
        } else {
            toast("已保存 " + ok + " 笔");
        }
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

        summary.setText(date + "　" + today.size() + " 单　收 "
                + Calc.fmt(amt) + (d.regular.size() == 6 ? "　赔 " + Calc.fmt(pay) : ""));
        summary.setTextColor(C_TXT);

        // 订单列表
        orderList.removeAllViews();
        if (today.isEmpty()) {
            orderList.addView(tv("还没有订单", 12, C_SUB, false));
        } else {
            for (Order o : today) {
                orderList.addView(orderRow(o, d));
            }
        }

        // 结算
        while (resultBox.getChildCount() > 1) resultBox.removeViewAt(1);
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
            resultBox.addView(tv("还没录开奖，录了就自动出结算", 12, C_SUB, false));
        }

        renderBoard(today);
        renderSplit(today);
        renderSim(today);
        renderArchive();
        renderUp(today);
        renderRisk(today);
        renderCustomers();
        renderBalls();
        if (custPick != null) custPick.setText("客户：" + store.customer() + " ▾");
        if (orderCum != null) {
            int sp = 0, pl = 0, ot = 0;
            for (Order o : today) {
                for (String c : o.codes) {
                    if (c.matches("\\d{2}")) sp++;
                    else if (c.startsWith("平")) pl++;
                    else ot++;
                }
            }
            orderCum.setText("订单累计：特号" + sp + "　平/连:" + pl + "　二/三:" + ot);
        }
        if (drawBox != null) {
            Draw dd = store.draw(curShop);
            drawBox.setText(dd.period > 0 ? drawLine(dd) : "还没录开奖");
        }
        tickClockOnce();
    }


    private void autoFetch() {
        toast("正在获取开奖…");
        final Context ctx = this;
        new Thread(() -> {
            Net net = new Net(ctx);
            final Draw got = net.fetch("澳");
            runOnUiThread(() -> {
                if (got == null) {
                    toast("拉不到开奖：检查网络，或手动录入");
                    return;
                }
                store.saveDraw(got, curShop);
                drawBox.setText(drawLine(got));
                refresh();
                toast("已获取第 " + got.period + " 期");
            });
        }).start();
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

    private void renderSim(List<Order> today) {
        Board b = Board.of(today);
        double cap = store.cap();
        simBox.removeAllViews();
        if (b.total <= 0) { simBox.addView(tv("还没有特号单", 12, C_SUB, false)); return; }

        List<int[]> low = SimAdd.lowest(b, cap, 12);
        StringBuilder sb = new StringBuilder("现在最少的 12 个号：");
        for (int[] x : low) sb.append(String.format("%02d %d　", x[0], x[1]));
        simBox.addView(tv(sb.toString().trim(), 11, C_SUB, false));

        int[][] cases = {{5, 50}, {10, 50}, {15, 50}, {20, 50}, {5, 100}, {10, 100}, {20, 100}};
        for (int[] c : cases) {
            SimAdd.Result r = SimAdd.run(b, cap, c[0], c[1]);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(3), 0, dp(3));
            TextView l = tv("补 " + c[0] + " 号到 " + c[1] + " 元　花 " + Calc.fmt(r.added), 11, C_SUB, false);
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            l.setLayoutParams(llp);
            row.addView(l);
            row.addView(tv((r.worst >= 0 ? "+" : "") + Calc.fmt(r.worst), 12, r.worst >= 0 ? C_GREEN : C_RED, true));
            simBox.addView(row);
            if (!r.picks.isEmpty()) {
                StringBuilder pk = new StringBuilder();
                for (int[] x : r.picks) pk.append(String.format("%02d(%d→%d) ", x[0], x[1], x[2]));
                simBox.addView(tv(pk.toString().trim(), 10, 0xFFBBBBBB, false));
            }
        }
    }

    private void renderArchive() {
        archBox.removeAllViews();
        List<String[]> list = archive.list();
        if (list.isEmpty()) {
            archBox.addView(tv("还没有归档", 12, C_SUB, false));
            return;
        }
        for (String[] a : list) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(4), 0, dp(4));
            TextView l = tv(a[1] + "　" + a[2] + " 单　" + a[3], 12, C_TXT, false);
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            l.setLayoutParams(llp);
            row.addView(l);
            Button viewBtn = btn("查看", v -> {
                List<Order> old = archive.load(a[0]);
                Draw dd = store.draw(curShop);
                double amt = store.totalAmount(old);
                double pay = dd.regular.size() == 6 ? store.totalPayout(old, dd) : 0;
                toast(a[1] + "\n" + old.size() + " 单　收 " + Calc.fmt(amt)
                        + (dd.regular.size() == 6 ? "　赔 " + Calc.fmt(pay) : "")
                        + "\n（按当前开奖算，没录开奖只有收）");
            });
            row.addView(viewBtn);
            Button del = btn("删除", v -> {
                archive.remove(a[0]);
                renderArchive();
                toast("已删除这份归档");
            });
            row.addView(del);
            archBox.addView(row);
        }
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
        Board b = Board.of(today);
        double cap = store.cap();
        if (b.total <= 0) { riskBox.addView(tv("还没有特号单", 12, C_SUB, false)); return; }

        double worst = b.worst(cap);
        double kept = b.kept(cap);
        riskBox.addView(tv(worst >= 0 ? "当前盘面稳，开出最重的号也赚 " + Calc.fmt(worst)
                : "当前盘面有敞口，最坏亏 " + Calc.fmt(-worst), 14, worst >= 0 ? C_GREEN : C_RED, true));

        // 号分散度：有注的号数 / 最重占比
        int n = 0;
        double maxNb = 0;
        for (double v : b.bets.values()) { if (v > 0) n++; maxNb = Math.max(maxNb, v); }
        riskBox.addView(tv("有注的号 " + n + "/49　最重一个号 " + Calc.fmt(maxNb)
                + "（占 " + Calc.fmt(maxNb / Math.max(1, b.total) * 100) + "%）", 12, C_SUB, false));
        if (n >= 40) riskBox.addView(tv("号铺得太散：每个号都有人买，削也削不干净，容易全场赔", 12, 0xFFB45309, false));

        // 建议：把最坏的号压下来
        double heavy = 0; int heavyNo = 0;
        for (Map.Entry<Integer, Double> e : b.bets.entrySet()) {
            if (e.getValue() > heavy) { heavy = e.getValue(); heavyNo = e.getKey(); }
        }
        if (worst < 0 && heavyNo > 0) {
            // 想让最坏 >= 0：这个号自留 x 要满足 kept - 47x >= 0
            double need = Math.max(0, kept / Calc.PAY_SPECIAL);
            riskBox.addView(tv(String.format("%02d 号收得最重，想不亏得把它的自留压到 %s 以下（要飞走 %s）",
                    heavyNo, Calc.fmt(need), Calc.fmt(Math.max(0, heavy - need))), 12, C_TXT, false));
        }
        riskBox.addView(tv("平特/连肖/二三 未计入这张表，开出来还要另赔 " + Calc.fmt(b.other) + " 元", 11, C_SUB, false));
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

    private void tickClock() {
        if (clockTxt == null) return;
        clockTxt.setText(new java.text.SimpleDateFormat("HH:mm:ss", Locale.CHINA).format(new Date()));
        clockTxt.postDelayed(this::tickClock, 1000);
    }

    /** 客户下拉 */
    private void pickCustomer() {
        final List<String> list = store.customers();
        String[] names = new String[list.size()];
        for (int i = 0; i < list.size(); i++) names[i] = list.get(i);
        new android.app.AlertDialog.Builder(this)
                .setTitle("选客户")
                .setItems(names, (d, which) -> {
                    store.setCustomer(list.get(which));
                    refresh();
                })
                .setNeutralButton("新客户", (d, w) -> askNewCustomer())
                .setPositiveButton("客户统计", (d, w) -> showCustStats())
                .show();
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
        if (shopTxt != null) shopTxt.setText(curShop.equals("澳") ? "澳门 ▾" : "香港 ▾");
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
                    byZ.put(z, byZ.getOrDefault(z, 0.0) + Board.betOf(o));
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
            case "arch": doArchive(); break;
            case "clear":
                store.saveOrders(new ArrayList<Order>());
                refresh();
                toast("订单已清空");
                break;
            case "hist":
                toggleTag("archive");
                scrollToTag("archive");
                break;
            case "rank":
                toggleTag("board");
                break;
            case "ai":
                toggleTag("risk");
                break;
            case "fly":
                toggleTag("split");
                toggleTag("sim");
                toggleTag("up");
                toggleTag("copy");
                break;
            case "profit":
                toggleTag("settle");
                break;
            case "pte":
                showStats("pte");
                break;
            default: break;
        }
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
            Button b = btn(c, v -> {
                store.setCustomer(c);
                refresh();
            });
            b.setTextSize(12);
            custRow.addView(b);
        }
    }

    private void renderSplit(List<Order> today) {
        Board b = Board.of(today);
        double cap = store.cap();
        double capPte = store.capPte();
        double capLx = store.capLx();
        boolean roundOn = store.flyRound();
        FlyBook.Ledger L = FlyBook.build(today, cap, capPte, capLx, roundOn, store.flown());
        splitBox.removeAllViews();

        // ---------- 三阈值输入：特 / 平 / 连 ----------
        LinearLayout th = new LinearLayout(this);
        th.setOrientation(LinearLayout.HORIZONTAL);
        th.setPadding(0, 0, 0, dp(4));
        th.addView(tv("阈值", 12, C_SUB, true));
        android.widget.EditText eSpec = capInput(cap);
        android.widget.EditText ePte = capInput(capPte);
        android.widget.EditText eLx = capInput(capLx);
        th.addView(labeled("特", eSpec));
        th.addView(labeled("平", ePte));
        th.addView(labeled("连", eLx));
        Button apply = btn("应用", v -> {
            double a = parseNum(eSpec.getText().toString(), cap);
            double p = parseNum(ePte.getText().toString(), capPte);
            double l = parseNum(eLx.getText().toString(), capLx);
            store.setCap(a); store.setCapPte(p); store.setCapLx(l);
            refresh();
        });
        apply.setTextSize(12);
        th.addView(apply);
        splitBox.addView(th);
        splitBox.addView(tv("特=每个号最多留多少；平=每个平特肖留多少；连=连肖留多少。0 表示全飞", 10, C_SUB, false));

        if (L.total <= 0) {
            splitBox.addView(tv("还没有订单", 12, C_SUB, false));
            return;
        }

        // ---------- 三段账 ----------
        LinearLayout seg1 = new LinearLayout(this);
        seg1.setOrientation(LinearLayout.HORIZONTAL);
        seg1.addView(tv("总单 ", 13, C_TXT, true));
        seg1.addView(tv(Calc.fmt(L.total), 15, C_TXT, true));
        seg1.addView(tv("  ｜ 已飞 ", 13, C_SUB, false));
        seg1.addView(tv(Calc.fmt(L.already), 13, C_SUB, true));
        seg1.addView(tv("  ｜ 待飞 ", 13, C_SUB, false));
        seg1.addView(tv(Calc.fmt(L.pending), 13, C_RED, true));
        splitBox.addView(seg1);

        LinearLayout seg2 = new LinearLayout(this);
        seg2.setOrientation(LinearLayout.HORIZONTAL);
        seg2.addView(tv("合计 ", 13, C_TXT, true));
        seg2.addView(tv(Calc.fmt(L.sum), 14, C_TXT, true));
        if (roundOn && Math.abs(L.pendingRound - L.pending) >= 0.01) {
            seg2.addView(tv("  ｜ 凑整 ", 12, C_SUB, false));
            seg2.addView(tv(Calc.fmt(L.pendingRound), 12, 0xFFB45309, true));
        }
        seg2.addView(tv("  ｜ 自留现金 ", 12, C_SUB, false));
        seg2.addView(tv(Calc.fmt(L.keepCash), 14, C_GREEN, true));
        splitBox.addView(seg2);

        if (L.totalLx > 0 || L.totalEm > 0 || L.totalPte > 0) {
            splitBox.addView(tv("特号 " + Calc.fmt(L.totalSpec) + " ｜ 平特 " + Calc.fmt(L.totalPte)
                    + " ｜ 连肖 " + Calc.fmt(L.totalLx) + " ｜ 二三中 " + Calc.fmt(L.totalEm), 11, C_SUB, false));
        }

        double kept = b.kept(cap);
        double fly = b.total - kept;
        double worst = b.worst(cap);
        splitBox.addView(tv("自留 " + Calc.fmt(kept) + " ｜ 飞 " + Calc.fmt(fly)
                + " ｜ 最坏 " + (worst >= 0 ? "+" : "") + Calc.fmt(worst), 14, worst >= 0 ? C_GREEN : C_RED, true));

        double be = Split.breakEvenCap(b, 1, Math.max(1, b.total));
        if (be <= 0) {
            splitBox.addView(tv("想一点不亏只能全部飞出去（每号自留 0）；留一点就亏一点", 12, 0xFFB45309, false));
        } else {
            splitBox.addView(tv("按不亏算：每号最多留 " + Calc.fmt(be) + "（飞 "
                    + Calc.fmt(b.total - b.kept(be)) + "）", 12, C_TXT, false));
        }

        int[] caps = {20, 30, 40, 50, 60, 80, 100};
        for (double[] r : Split.scan(b, caps)) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(2), 0, dp(2));
            TextView l = tv("每号留 " + Calc.fmt(r[0]) + "　自留 " + Calc.fmt(r[1]) + "　飞 " + Calc.fmt(r[2]), 11, C_SUB, false);
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            l.setLayoutParams(llp);
            row.addView(l);
            row.addView(tv((r[3] >= 0 ? "+" : "") + Calc.fmt(r[3]), 12, r[3] >= 0 ? C_GREEN : C_RED, true));
            splitBox.addView(row);
        }

        splitBox.addView(tv("要飞的号", 13, C_TXT, true));
        List<Split.Row> rows = Split.rows(b, cap);
        int shown = 0;
        for (Split.Row r : rows) {
            if (r.fly <= 0) continue;
            shown++;
            splitBox.addView(tv(String.format("%02d　%s→留%s　飞%s", r.no, Calc.fmt(r.nb), Calc.fmt(r.self), Calc.fmt(r.fly)), 12, C_TXT, false));
        }
        if (shown == 0) splitBox.addView(tv("这个阈值下不用飞，全部自己吃", 12, C_SUB, false));

        // ---- 凑整 + 飞单目录（与专业版 flyShowAmt / flyGroupText 同口径）----
        android.widget.CheckBox cb = new android.widget.CheckBox(this);
        cb.setText("金额凑整 5 元档");
        cb.setTextSize(12);
        cb.setTextColor(C_TXT);
        cb.setChecked(store.flyRound());
        cb.setPadding(0, dp(8), 0, 0);
        cb.setOnCheckedChangeListener((v, on) -> { store.setFlyRound(on); refresh(); });
        splitBox.addView(cb);
        splitBox.addView(tv("勾上后每个号就近凑到 5 的倍数（34→35、31→30、3→5），多飞的自付、少飞的自己留", 11, C_SUB, false));

        boolean rd = store.flyRound();
        final java.util.List<FlyBook.Group> gs = L.groups;
        final double showSum = L.pendingRound;
        final double rawSum = L.pending;
        splitBox.addView(tv("飞单目录（" + gs.size() + " 行）", 13, C_TXT, true));
        if (gs.isEmpty()) {
            splitBox.addView(tv("没有要飞的", 12, C_SUB, false));
        } else {
            for (FlyBook.Group g : gs) splitBox.addView(tv(g.text(), 12, C_TXT, false));
            if (rd && Math.abs(showSum - rawSum) >= 0.01) {
                splitBox.addView(tv("凑整前 " + Calc.fmt(rawSum) + "，凑整后 " + Calc.fmt(showSum)
                        + "（" + (showSum > rawSum ? "多飞 " : "省 ") + Calc.fmt(Math.abs(showSum - rawSum)) + "）", 11, C_SUB, false));
            }
            LinearLayout act = new LinearLayout(this);
            act.setOrientation(LinearLayout.HORIZONTAL);
            act.addView(btn("复制飞单", v -> copyFly(gs, showSum)));
            act.addView(btn("确认已飞", v -> {
                android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
                ad.setTitle("确认飞单");
                ad.setMessage("本轮共飞 " + Calc.fmt(showSum) + " 元，确认后记入已飞累计。");
                ad.setPositiveButton("确定", (d, w) -> {
                    java.util.Map<String, Double> fm = store.flown();
                    FlyBook.commit(L, fm, rd);
                    store.setFlown(fm);
                    refresh();
                    toast("已记入已飞 " + Calc.fmt(showSum));
                });
                ad.setNegativeButton("取消", null);
                ad.show();
            }));
            act.addView(btn("清空已飞", v -> {
                android.app.AlertDialog.Builder ad = new android.app.AlertDialog.Builder(this);
                ad.setMessage("清空已飞登记？已飞回到 0，待飞重新按全部计算。");
                ad.setPositiveButton("确定", (d, w) -> { store.clearFlown(); refresh(); });
                ad.setNegativeButton("取消", null);
                ad.show();
            }));
            splitBox.addView(act);
        }
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
        double kept = b.kept(cap);
        boardSum.setText("特号合计 " + Calc.fmt(b.total) + "　自留 " + Calc.fmt(kept)
                + "　飞 " + Calc.fmt(b.total - kept)
                + "　最坏 " + (b.worst(cap) >= 0 ? "+" : "") + Calc.fmt(b.worst(cap))
                + (b.other > 0 ? "\n平/连/二三 另算 " + Calc.fmt(b.other) : ""));
        boardSum.setTextColor(C_TXT);

        rankBox.removeAllViews();
        List<int[]> rk = b.rank();
        if (rk.isEmpty()) rankBox.addView(tv("还没有特号单", 12, C_SUB, false));
        int idx = 1;
        for (int[] r : rk) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(3), 0, dp(3));
            row.addView(tv(String.valueOf(idx++), 12, C_SUB, false));
            TextView no = tv(String.format("  %02d %s", r[0], Z.of(r[0])), 13, C_TXT, false);
            LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            no.setLayoutParams(nlp);
            row.addView(no);
            row.addView(tv(Calc.fmt(r[1]), 13, C_TXT, true));
            rankBox.addView(row);
        }

        numBoxL.removeAllViews();
        numBoxR.removeAllViews();
        List<Integer> nos = new ArrayList<>();
        for (int n = 1; n <= 49; n++) nos.add(n);
        // 有注的排前面，按注额从大到小；没注的放后面
        nos.sort((x, y) -> {
            double a = b.bets.get(x), c = b.bets.get(y);
            if ((a > 0) != (c > 0)) return a > 0 ? -1 : 1;
            if (a != c) return a > c ? -1 : 1;
            return x - y;
        });
        int half = (nos.size() + 1) / 2;
        for (int i = 0; i < nos.size(); i++) {
            int n = nos.get(i);
            double nb = b.bets.get(n);
            double self = Math.min(nb, cap);
            double fly = nb - self;
            double net = b.netIf(n, cap);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(2), 0, dp(2));
            String left = String.format("%02d %s%s ", n, Calc.fmt(nb),
                    fly > 0 ? "→" + Calc.fmt(self) : "");
            TextView l = tv(left, 12, nb > 0 ? C_TXT : 0xFFBBBBBB, false);
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            l.setLayoutParams(llp);
            row.addView(l);
            TextView rt = tv((net >= 0 ? "+" : "") + Calc.fmt(net), 12, net >= 0 ? C_GREEN : C_RED, false);
            rt.setGravity(Gravity.END);
            rt.setMinWidth(dp(52));
            row.addView(rt);
            if (i < half) numBoxL.addView(row); else numBoxR.addView(row);
        }
    }

    private View orderRow(Order o, Draw d) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(7), 0, dp(7));
        row.setBackgroundColor(C_CARD);
        row.setShowDividers(LinearLayout.SHOW_DIVIDER_MIDDLE);

        LinearLayout left = new LinearLayout(this);
        left.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        left.setLayoutParams(llp);
        LinearLayout line = new LinearLayout(this);
        line.setOrientation(LinearLayout.HORIZONTAL);
        TextView cu = tv(o.customer, 11, C_SUB, false);
        cu.setPadding(0, 0, dp(6), 0);
        line.addView(cu);
        String codes = codeLabel(o.codes);
        line.addView(tv(codes.length() > 24 ? codes.substring(0, 24) + "…" : codes, 13, C_TXT, false));
        left.addView(line);

        TextView right = tv(Calc.fmt(o.price) + (o.isPer ? "/号" : ""), 14, C_TXT, true);
        right.setGravity(Gravity.END);

        row.addView(left);
        row.addView(right);
        row.setOnLongClickListener(v -> {
            store.removeOrder(o.id);
            refresh();
            toast("已删除");
            return true;
        });
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
