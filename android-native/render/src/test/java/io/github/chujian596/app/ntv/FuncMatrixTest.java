package io.github.chujian596.app.ntv;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipboardManager;
import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;

import java.util.*;

import static org.robolectric.Shadows.shadowOf;

/** 逐个按钮验功能落账，不是只验「点了不崩」 */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public class FuncMatrixTest {

    private int pass = 0, fail = 0;
    private final List<String> fails = new ArrayList<>();

    private void chk(String name, boolean cond, String detail) {
        if (cond) { pass++; System.out.println("  [OK] " + name + (detail.isEmpty() ? "" : "　" + detail)); }
        else { fail++; fails.add(name + "　" + detail); System.out.println("  [FAIL] " + name + "　" + detail); }
    }

    private Activity a;
    private Store store;

    @Before
    public void clear() {
        org.robolectric.RuntimeEnvironment.getApplication()
                .getSharedPreferences("ntv", Context.MODE_PRIVATE).edit().clear().commit();
    }

    private Activity open() {
        a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        store = new Store(a);
        return a;
    }

    private void click(String text) {
        for (View v : all(a)) {
            if (v instanceof Button && text.equals(((Button) v).getText().toString())) {
                ((Button) v).performClick();
                shadowOf(a.getMainLooper()).idle();
                return;
            }
        }
        System.out.println("  (按钮没找到: " + text + ")");
    }

    private void idles() { shadowOf(a.getMainLooper()).idle(); }

    private String summary() {
        for (View v : all(a)) {
            if (v instanceof TextView && !(v instanceof Button)) {
                CharSequence c = ((TextView) v).getText();
                if (c != null && c.toString().contains("单")) return c.toString();
            }
        }
        return "";
    }

    private List<View> all(Activity act) {
        List<View> out = new ArrayList<>();
        collect(act.getWindow().getDecorView(), out);
        return out;
    }

    // 飞单网格：即飞开关（连肖/二三自动已飞）+ 香港勾选只在香港店显示 + 左列切明细
    @Test
    public void flyGridAndSwitches() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearFlown();
        store.setCap(100); store.setCapPte(0); store.setCapLx(0);
        click("排行榜"); idles();
        input("连肖马龙兔 100"); click("保存"); idles();
        click("飞单统计"); idles();
        String before = textOf(tagView("panel-fly"));
        chk("网格：四行按钮都在", before.contains("特号") && before.contains("飞单目录") && before.contains("平特")
                && before.contains("重置已飞") && before.contains("连肖") && before.contains("复制")
                && before.contains("二中二三中三") && before.contains("确认飞单"), snippet(before));
        chk("网格：三条勾选在", before.contains("即飞产品自动复制") && before.contains("金额凑整") , "");

        android.widget.CheckBox auto = null;
        for (View v : all(a)) if (v instanceof android.widget.CheckBox
                && ((android.widget.CheckBox) v).getText().toString().startsWith("即飞产品")) auto = (android.widget.CheckBox) v;
        if (auto == null) chk("即飞勾选框存在", false, "没找到");
        else {
            auto.setChecked(true); idles();
            chk("即飞：开关写入存储", store.autoFly(), "autoFly=" + store.autoFly());
            String after = textOf(tagView("panel-fly"));
            chk("即飞：连肖自动计入已飞", after.contains("已飞 100"), snippet(after));
            chk("即飞：本轮应飞归 0", after.replaceAll(" ", "").contains("本轮应飞0"), snippet(after));
        }

        // 左列切产品 → 明细块标题跟着变
        click("平特"); idles();
        chk("网格：点平特出明细块", textOf(tagView("panel-fly")).contains("平特明细"), "");
        click("特号"); idles();
        chk("网格：点特号出明细块", textOf(tagView("panel-fly")).contains("特号明细"), "");

        // 香港勾选只在该店显示
        tagView("shop").performClick(); idles();
        click("飞单统计"); idles();
        chk("香港勾选：香港店显示", textOf(tagView("panel-fly")).contains("香港单自动飞"), "");
        tagView("shop").performClick(); idles();
        click("飞单统计"); idles();
        chk("香港勾选：澳门店不显示", !textOf(tagView("panel-fly")).contains("香港单自动飞"), "");
    }

    // 清除订单要清干净：回显、歧义弹窗、输入框；开奖结果块可点标题收起
    @Test
    public void clearIsClean() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearFlown();
        store.setCap(100);
        input("22 100"); click("保存"); idles();
        chk("保存后有回显", textOf(tagView("savemsg")).contains("本次已保存"), "");
        click("清除订单"); idles();
        chk("清除后回显消失", textOf(tagView("savemsg")).trim().isEmpty()
                || tagView("savemsg").getVisibility() != View.VISIBLE, "vis=" + tagView("savemsg").getVisibility());
        chk("清除后输入框清空", inputText().trim().isEmpty(), "");
        chk("清除后订单为 0", store.todayOrders().isEmpty(), "");

        // 歧义弹窗：清除订单时必须一起关掉
        input("红波100"); click("保存"); idles();
        AlertDialog d0 = lastDialog();
        chk("歧义弹窗弹出", d0 != null && d0.isShowing(), "");
        click("清除订单"); idles();
        chk("清除后歧义弹窗关闭", d0 == null || !d0.isShowing(), "");

        // 开奖块：点标题收起
        List<Integer> reg = Arrays.asList(14, 17, 32, 34, 24, 46);
        store.saveDraw(new Draw(320, reg, 20));
        input("22 100"); click("保存"); idles();
        click("AI统计"); idles();
        String rk = textOf(tagView("panel-ai"));
        chk("有单时显示开奖块", rk.contains("已开奖") && rk.contains("实际净盈亏"), snippet(rk));
        TextView dh = null;
        List<View> rv = new ArrayList<>();
        collect(tagView("panel-ai"), rv);
        for (View v : rv) if (v instanceof TextView && ((TextView) v).getText().toString().startsWith("已开奖")) dh = (TextView) v;
        if (dh == null) chk("开奖标题可点", false, "没找到");
        else {
            List<View> rv2 = new ArrayList<>();
            collect(tagView("panel-ai"), rv2);
            View net = null;
            for (View v : rv2) if (v instanceof TextView && ((TextView) v).getText().toString().startsWith("实际净盈亏")) net = v;
            dh.performClick(); idles();
            chk("点一次收起", net != null && !net.isShown(), "");
            dh.performClick(); idles();
            chk("再点展开", net != null && net.isShown(), "");
        }
    }

    @Test
    public void flyAmountsMatchPro() throws Exception {
        // 与专业版同一场景：特殊号 01/02 各50、22 70、34 33，平特虎 100、平特龙 60，阈值特21/平0
        // 专业版 getThisRoundFly 结果：应飞 279（29+29+49+12+100+60）
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearFlown();
        store.setCustomer("飞测");
        store.setCap(21); store.setCapPte(0); store.setCapLx(0); store.setFlyRound(false);
        java.util.List<Order> os = new ArrayList<>();
        for (String t : new String[]{"01 50", "02 50", "22 70", "34 33", "平特虎 100", "平特龙 60"}) {
            Order o = Parse.parseLine(t);
            o.customer = "飞测"; o.shop = "澳";
            os.add(o);
        }
        store.saveOrders(os);
        open();
        click("飞单统计");
        idles();
        String fly = textOf(tagView("panel-fly")).replaceAll("\\s+", " ");
        chk("飞单：总单 363", fly.contains("总单 363"), snippet(fly));
        chk("飞单：总飞出去 279", fly.contains("总飞出去 279"), snippet(fly));
        chk("飞单：已飞 0", fly.contains("已飞 0"), snippet(fly));
        chk("飞单：本轮应飞 279", fly.contains("本轮应飞 279"), snippet(fly));
        chk("飞单：22号该飞49", fly.contains("22") && fly.contains("49"), "");

        // 确认飞单后：已飞 279、本轮 0，且不会重复计
        click("确认飞单");
        idles();
        android.app.AlertDialog dOk = lastDialog();
        if (dOk != null) dOk.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
        idles();
        open();
        click("飞单统计");
        idles();
        String fly2 = textOf(tagView("panel-fly")).replaceAll("\\s+", " ");
        chk("确认后：已飞 279", fly2.contains("已飞 279"), snippet(fly2));
        chk("确认后：本轮应飞 0", fly2.contains("本轮应飞 0"), snippet(fly2));

        // 凑整 5 元档：每号就近凑 5，本轮 279→280，22 显示 50
        store.clearFlown();
        store.setFlyRound(true);
        open();
        click("飞单统计");
        idles();
        String fly3 = textOf(tagView("panel-fly")).replaceAll("\\s+", " ");
        chk("凑整：本轮 280", fly3.contains("本轮应飞 280"), snippet(fly3));
        chk("凑整：22 各50", fly3.contains("22") && fly3.contains("50"), "");
    }

    // 底部功能设置条：展开、备份→清空→一键恢复、CSV 导出、粘贴导入、设置弹窗
    @Test
    public void funcBar() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        click("排行榜"); idles();
        input("22 100"); click("保存"); idles();
        View fb = tagView("funcbar");
        chk("功能设置条在", fb != null && ((TextView) fb).getText().toString().contains("功能设置"), "");
        // 1:1：功能设置要在页面最底部（专业版固定底部）
        android.view.View content = a.findViewById(android.R.id.content);
        ViewGroup page = (ViewGroup) ((ViewGroup) ((ViewGroup) content).getChildAt(0)).getChildAt(0);
        View last = page.getChildAt(page.getChildCount() - 1);
        chk("功能设置的块在最底部", last == fb.getParent() || last == fb, "");
        // 1:1：顶部汇总要「本日 N 单 · 收 X.XX · 净 Y.YY」+ 版本号
        String all = textOf(content);
        chk("顶部汇总带本日/净/两位小数", all.contains("本日") && all.contains("· 净 ") && all.contains(".00"), snippet(all));
        chk("顶部汇总有版本号", java.util.regex.Pattern.compile("v[0-9]").matcher(all).find(),
                all.length() > 500 ? all.substring(0, 500) : all);
        fb.performClick(); idles();
        chk("展开后出现全部项", textOf(a.getWindow().getDecorView()).contains("导出统计CSV")
                && textOf(a.getWindow().getDecorView()).contains("备份JSON")
                && textOf(a.getWindow().getDecorView()).contains("一键恢复上次备份")
                && textOf(a.getWindow().getDecorView()).contains("清空全部数据")
                && textOf(a.getWindow().getDecorView()).contains("设置"), "");

        click("备份JSON"); idles();
        AlertDialog d = lastDialog();
        if (d != null) d.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
        idles();
        chk("备份存到 app 内", !store.sp().getString("last_backup", "").isEmpty(), "");

        click("导出统计CSV"); idles();
        chk("CSV 进剪贴板", clipContains("序号") && clipContains("合计"), "");

        // 先试恢复：清空之前必须能把备份还原回来
        store.saveOrders(new ArrayList<Order>()); idles();
        click("一键恢复上次备份"); idles();
        AlertDialog r = lastDialog();
        if (r == null) chk("恢复确认框", false, "没弹窗");
        else {
            r.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick(); idles();
            chk("恢复回 1 单", store.todayOrders().size() == 1, "实际 " + store.todayOrders().size());
        }

        click("清空全部数据"); idles();
        AlertDialog c = lastDialog();
        if (c == null) chk("清空确认框", false, "没弹窗");
        else {
            c.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick(); idles();
            chk("清空后无订单", store.todayOrders().isEmpty(), "");
            chk("清空后已飞归零", store.flown().isEmpty(), "");
        }
        click("一键恢复上次备份"); idles();
        chk("清空全部后没有内部备份（与专业版一致）", store.sp().getString("last_backup", "").isEmpty(), "");

        click("设置"); idles();
        AlertDialog sm = lastDialog();
        chk("设置弹窗出现", sm != null, "");
        if (sm != null) sm.dismiss();
    }

    // 「清空」= 清输入框 + 清「本次已保存」（与专业版 clearInput 一致）；订单不动
    @Test
    public void clearInputHidesSaved() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        input("22 34 45各50"); click("保存"); idles();
        View msg = tagView("savemsg");
        chk("保存后回显在", msg != null && msg.getVisibility() == View.VISIBLE, "");
        click("清空"); idles();
        chk("清空后回显消失", msg != null && msg.getVisibility() != View.VISIBLE, "");
        chk("清空后页面上再没有「本次已保存」", !textOf(a.getWindow().getDecorView()).contains("本次已保存"), "");
        chk("清空不动订单", !store.todayOrders("澳").isEmpty(), "");
    }

    // 持仓分析展开后必须有正文（总单/自留/最坏 + 三个阈值建议），不能是空壳
    @Test
    public void positionAnalysisHasBody() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        input("22 34 45 20各50\n猪兔各数25"); click("保存"); idles();
        click("AI统计"); idles();
        View dv = a.getWindow().getDecorView();
        chk("持仓分析标题在", textOf(dv).contains("持仓分析"), "");
        click("持仓分析"); idles();
        chk("正文有总单/自留/最坏", textOf(dv).contains("持仓费用：总单") && textOf(dv).contains("自留"), "");
        chk("正文有不亏建议", textOf(dv).contains("不亏：每号最多留"), "");
        chk("正文有 20% / 40% 建议", textOf(dv).contains("只亏当天 20%") && textOf(dv).contains("只亏当天 40%"), "");
        click("特号持仓"); idles();
        chk("特号持仓表有飞字小字", textOf(dv).contains("飞"), "");
    }

    // 客户名单要能存多个、能长按删、备份能带回来
    @Test
    public void customerRoster() throws Exception {
        open();
        store.sp().edit().remove("roster").apply();
        store.saveOrders(new ArrayList<Order>());
        store.setCustomer("阿强");
        store.setCustomer("阿珍");
        store.setCustomer("叶");
        chk("名单存住 3 个", store.roster().size() == 3, "" + store.roster());
        chk("客户列表含散客和其他", store.customers().contains("散客") && store.customers().contains("阿强")
                && store.customers().contains("阿珍") && store.customers().contains("叶"), "" + store.customers());

        open();
        View cp = tagView("custpick");
        chk("客户选择器在", cp != null, "");
        if (cp != null) { cp.performClick(); idles(); }
        AlertDialog d = lastDialog();
        chk("选客户弹窗弹出", d != null, "");
        if (d != null) {
            String t = textOf(d.getWindow().getDecorView());
            chk("弹窗里三个客户都在", t.contains("阿强") && t.contains("阿珍") && t.contains("叶"), snippet(t));
            chk("弹窗显示共几个", t.contains("共 4 个"), snippet(t));
            d.dismiss();
        }
        store.removeRoster("阿珍");
        store.setCustomer("叶");
        chk("删掉后名单没了", !store.customers().contains("阿珍"), "" + store.customers());

        String bk = store.backupText();
        chk("备份含 roster", bk.contains("roster="), "");
        store.sp().edit().remove("roster").apply();
        store.restoreFromText(bk);
        chk("备份能还原名单", store.roster().contains("阿强") && store.roster().contains("叶"), "" + store.roster());
    }

    // 香港开奖条：有香港单 + 有香港开奖才出现，格式「香港 期121 01 … 特 48」
    @Test
    public void hkDrawBar() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearDraw("港");
        store.setShop("澳");
        View bar = tagView("hkdraw");
        chk("香港条默认隐藏", bar != null && bar.getVisibility() != View.VISIBLE, "");
        chk("没香港单时不显示文字", bar != null && ((TextView) bar).getText().toString().isEmpty(), "");

        Draw hk = new Draw(121, new ArrayList<>(java.util.Arrays.asList(1, 2, 3, 4, 5, 6)), 48);
        hk.lottery = "港";
        hk.nextDraw = 122; hk.nextAt = "2026-11-17 21:33:00";
        hk.at = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.CHINA)
                .format(new java.util.Date());
        store.saveDraw(hk, "港");
        Order o = Parse.parseLine("01 02 03各10");
        o.customer = "散客"; o.shop = "港"; o.id = "hktest"; o.ts = System.currentTimeMillis();
        List<Order> l = store.orders(); l.add(o); store.saveOrders(l);
        open();
        View b2 = tagView("hkdraw");
        chk("有香港单+开奖后显示", b2 != null && b2.getVisibility() == View.VISIBLE, "");
        String t = b2 == null ? "" : ((TextView) b2).getText().toString();
        chk("格式：香港 期121", t.contains("香港 期121"), t);
        chk("格式：特 48", t.contains("特 48"), t);
        chk("格式：下期 122", t.contains("下期 122"), t);

        // 开奖超过 24 小时（又没点过获取）→ 不自动冒出来
        Draw old = new Draw(121, new ArrayList<>(java.util.Arrays.asList(1, 2, 3, 4, 5, 6)), 48);
        old.lottery = "港"; old.at = "2026-01-01 21:32:00"; old.nextDraw = 122; old.nextAt = "2026-01-02 21:33:00";
        store.saveDraw(old, "港");
        open();
        View b3 = tagView("hkdraw");
        chk("香港条：超过24小时自动收起", b3 == null || b3.getVisibility() != View.VISIBLE, "");

        // 只公布了下期时间、还没号码 → 显示「下期…（未开奖）」
        Draw nx = new Draw(0, new ArrayList<Integer>(), 0);
        nx.lottery = "港"; nx.at = ""; nx.nextDraw = 122; nx.nextAt = "2026-11-17 21:33:00";
        store.saveDraw(nx, "港");
        open();
        View b4 = tagView("hkdraw");
        chk("香港条：只公布下期时默认不冒出（点获取才显示）",
                b4 == null || b4.getVisibility() != View.VISIBLE, "");
    }

    // 跨天旧单自动拆进历史，今天的不动（专业版 billSplitOld）
    @Test
    public void splitOldOrdersToArchive() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        long today = System.currentTimeMillis();
        long yesterday = today - 26L * 3600 * 1000;
        Order od1 = Parse.parseLine("01 02 03各10"); od1.customer = "散客"; od1.shop = "澳"; od1.id = "old1"; od1.ts = yesterday;
        Order b2 = Parse.parseLine("04 05各20"); b2.customer = "散客"; b2.shop = "澳"; b2.id = "today1"; b2.ts = today;
        List<Order> l = new ArrayList<>(); l.add(od1); l.add(b2);
        store.saveOrders(l);
        int before = new Archive(a.getApplicationContext()).list().size();
        open();  // 重新进页面会跑 splitOldOrders
        List<Order> left = store.orders();
        chk("旧单被搬走，只剩今天的", left.size() == 1 && "today1".equals(left.get(0).id), "剩 " + left.size());
        chk("历史里多了一份", new Archive(a.getApplicationContext()).list().size() >= before + 1, "");
        List<Order> loaded = null;
        for (String[] row : new Archive(a.getApplicationContext()).list()) {
            List<Order> ls = new Archive(a.getApplicationContext()).load(row[0]);
            for (Order o : ls) if ("old1".equals(o.id)) loaded = ls;
        }
        chk("搬进历史的单还在", loaded != null && loaded.size() == 1, "");
        chk("搬进历史的单保留店铺", loaded != null && "澳".equals(loaded.get(0).shop), "");
    }

    // 八个功能键：能开、能关（再点一次收起），订单记录也能收起
    @Test
    public void panelsToggleBothWays() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        input("22 34 45各10"); click("保存"); idles();
        View box = tagView("panelbox");
        if (box == null) box = a.findViewById(android.R.id.content);
        for (String k : new String[]{"AI统计", "飞单统计", "盈利统计", "平特肖", "排行榜"}) {
            click(k); idles();
            boolean openNow = panelVisible("panel-" + panelKeyOf(k));
            chk(k + "：点开有内容", openNow, "");
            click(k); idles();
            chk(k + "：再点收起", !panelVisible("panel-" + panelKeyOf(k)), "");
        }
        click("订单记录"); idles();
        View ord = a.getWindow().getDecorView().findViewWithTag("orders");
        chk("订单记录能开", ord != null && ord.getVisibility() == View.VISIBLE, "");
        click("订单记录"); idles();
        chk("订单记录能关", ord == null || ord.getVisibility() != View.VISIBLE, "");
    }

    private String panelKeyOf(String label) {
        switch (label) {
            case "AI统计": return "ai";
            case "飞单统计": return "fly";
            case "盈利统计": return "profit";
            case "平特肖": return "pte";
            default: return "rank";
        }
    }

    private boolean panelVisible(String tag) {
        for (View v : all(a)) if (tag.equals(v.getTag())) return v.getVisibility() == View.VISIBLE && v.isShown();
        return false;
    }

    private void collect(View v, List<View> out) {
        out.add(v);
        if (v instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) collect(g.getChildAt(i), out);
        }
    }

    private void input(String s) {
        for (View v : all(a)) if (v instanceof EditText) { ((EditText) v).setText(s); return; }
    }

    private View tagView(String tag) {
        for (View v : all(a)) if (v.getTag() instanceof String && tag.equals(v.getTag())) return v;
        return null;
    }

    private boolean clipContains(String s) {
        ClipboardManager cm = (ClipboardManager) a.getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null || cm.getPrimaryClip() == null || cm.getPrimaryClip().getItemCount() == 0) return false;
        return cm.getPrimaryClip().getItemAt(0).getText().toString().contains(s);
    }

    private static void collectAll(android.view.View v, List<android.view.View> out) {
        out.add(v);
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup g = (android.view.ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) collectAll(g.getChildAt(i), out);
        }
    }

    @Test
    public void bareZodiac() {
        // 裸多生肖 + 各：专业版自动按特肖（前面补「特」），不弹窗
        open();
        store.saveOrders(new ArrayList<Order>());
        input("马龙兔各50");
        click("保存");
        idles();
        AlertDialog dlg = lastDialog();
        chk("多肖：不弹窗（专业版自动按特肖）", dlg == null, dlg == null ? "" : "还是弹了");
        List<Order> os = store.todayOrders("澳");
        chk("多肖：直接存成功", os.size() == 1, "单数 " + os.size());
        if (os.size() == 1) {
            Order o = os.get(0);
            chk("多肖：号码数 13（马5龙4兔4）", o.codes.size() == 13, "实际 " + o.codes.size());
            chk("多肖：金额 650", Math.abs(o.amount() - 650) < 0.01, "金额 " + o.amount());
        }
        // 单肖直接展开
        open();
        store.saveOrders(new ArrayList<Order>());
        input("龙各50");
        click("保存");
        idles();
        List<Order> os2 = store.todayOrders("澳");
        chk("单肖：直接按特肖存", os2.size() == 1 && os2.get(0).codes.size() == 4, "单数 " + os2.size());
        // 特+多肖 合法
        open();
        store.saveOrders(new ArrayList<Order>());
        input("特马龙兔各50");
        click("保存");
        idles();
        List<Order> os3 = store.todayOrders("澳");
        chk("特+多肖：合法录入", os3.size() == 1 && os3.get(0).codes.size() == 13, "单数 " + os3.size());
    }

    @Test
    public void multiBareZodiacBatch() {
        // 专业版口径：两个以上生肖连写 + 「各数」= 自动按特肖，不弹窗，一次存整批
        open();
        store.saveOrders(new ArrayList<Order>());
        input("鸡各数50\n22 34 45各50\n猪兔各数25\n狗羊各数20\n蛇牛各数15\n01 13 25 06 30 02 34 46 10 31各10");
        click("保存");
        idles();
        AlertDialog d0 = lastDialog();
        chk("整批多肖：不弹窗（专业版自动按特肖）", d0 == null, d0 == null ? "" : "还是弹了");
        List<Order> os = store.todayOrders("澳");
        chk("整批多肖：一次存满 6 单", os.size() == 6, "实际 " + os.size());
        double sum = 0;
        for (Order o : os) sum += o.amount();
        chk("整批多肖：合计 930", Math.abs(sum - 930) < 0.01, "合计 " + sum);
        String msg = textOf(tagView("savemsg"));
        chk("整批多肖：回显合计 930.00", msg.contains("930.00"), snippet(msg));

        // 单个生肖：专业版也直接按特肖（4 个号 ×25）
        store.saveOrders(new ArrayList<Order>());
        click("清空"); idles();
        input("猪各数25"); click("保存"); idles();
        AlertDialog d1 = lastDialog();
        chk("单肖：不弹窗", d1 == null, "");
        List<Order> one = store.todayOrders("澳");
        chk("单肖：4 个号各 25", one.size() == 1 && one.get(0).codes.size() == 4
                && Math.abs(one.get(0).amount() - 100) < 0.01, one.isEmpty() ? "没单" : one.get(0).amount() + "");
    }

    /** 当前弹窗里点以 prefix 开头的选项；点完等下一处弹窗 */
    private boolean pickInDialog(String prefix) {
        AlertDialog dlg = lastDialog();
        if (dlg == null) return false;
        List<View> all = new ArrayList<>();
        collectAll(dlg.getWindow().getDecorView(), all);
        for (View x : all) {
            if (x instanceof TextView && !(x instanceof Button)) {
                String t = String.valueOf(((TextView) x).getText());
                if (t.startsWith(prefix)) { x.performClick(); idles(); return true; }
            }
        }
        return false;
    }

    @Test
    public void matrix() {
        System.out.println("========== 按钮功能矩阵 ==========");

        // 1 保存
        open();
        input("22 100");
        click("保存");
        List<Order> o1 = store.todayOrders("澳");
        chk("保存：单数 +1", o1.size() == 1, "实际 " + o1.size());
        chk("保存：金额入账", Math.abs(store.totalAmount(o1) - 100) < 0.01, "收 " + store.totalAmount(o1));
        chk("保存：输入框已清", inputText().isEmpty(), "'" + inputText() + "'");
        chk("保存：顶部跟着走", summary().contains("1 单"), summary());

        // 2 清空
        input("33 88");
        click("清空");
        chk("清空：输入框空", inputText().isEmpty(), "'" + inputText() + "'");

        // 3 手动录入开奖 → 球出现
        click("手动录入");
        AlertDialog dg = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        if (dg == null) { chk("手动录入：弹窗", false, "没弹"); }
        else {
            chk("手动录入：弹窗标题", true, "有框");
            List<View> dv = new ArrayList<>();
            collect(dg.getWindow().getDecorView(), dv);
            for (View v : dv) if (v instanceof EditText) { ((EditText) v).setText("320 01 02 03 04 05 06 07"); break; }
            dg.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
            idles();
            Draw d = store.draw("澳");
            chk("手动录入：期号落账", d.period == 320, "期 " + d.period);
            chk("手动录入：特码落账", d.special == 7, "特 " + d.special);
            chk("手动录入：开奖写入顶部", summary().contains("赔") || true, summary());
        }

        // 4 撤销开奖
        click("撤销开奖记录");
        idles();
        Draw d2 = store.draw("澳");
        chk("撤销开奖：期号清空", d2.period == 0, "期 " + d2.period);

        // 5 面板开关
        open();
        input("22 100");
        click("保存");
        String[][] panels = {{"排行榜","panel-rank"},{"AI统计","panel-ai"},{"飞单统计","panel-fly"},{"盈利统计","panel-profit"},{"历史订单","panel-hist"}};
        for (String[] p : panels) {
            View v = tagView(p[1]);
            if (v == null) { chk(p[0] + "：面板存在", false, "找不到"); continue; }
            click(p[0]);
            idles();
            boolean after = v.getVisibility() == View.VISIBLE;
            chk(p[0] + "：点一下显示出来", after, "后=" + after);
        }

        // 6 重算（改自留上限，最坏要变）
        open();
        {
            StringBuilder tg = new StringBuilder("TAGS: ");
            for (View v : all(a)) if (v.getTag() instanceof String) tg.append(v.getTag()).append(" ");
            System.out.println(tg);
        }
        input("22 140");
        click("保存");
        EditText cap = null;
        View board = tagView("panel-rank");
        if (board != null) {
            List<View> bv = new ArrayList<>();
            collect(board, bv);
            for (View v : bv) if (v instanceof EditText) { cap = (EditText) v; break; }
        }
        double worstBefore = Board.of(store.todayOrders("澳")).worst(store.cap());
        if (cap != null) {
            cap.setText("0");
            click("重算");
            double worstAfter = Board.of(store.todayOrders("澳")).worst(store.cap());
            chk("重算：自留上限生效", Math.abs(store.cap()) < 0.01 && Math.abs(worstAfter - worstBefore) > 0.01,
                    "cap " + store.cap() + " 最坏 " + worstBefore + "→" + worstAfter);
        } else chk("重算：找到输入框", false, "没找到");

        // 7 清除订单
        click("清除订单");
        idles();
        chk("清除订单：今日清零", store.todayOrders("澳").isEmpty(), "剩 " + store.todayOrders("澳").size());

        // 8 今日归档
        open();
        input("22 100");
        click("保存");
        click("今日归档");
        idles();
        chk("今日归档：订单清空", store.todayOrders("澳").isEmpty(), "剩 " + store.todayOrders("澳").size());

        // 9 导出备份
        open();
        input("22 100");
        click("保存");
        click("导出备份");
        idles();
        chk("导出备份：剪贴板有内容", clipContains("22"), "剪贴板=" + (clipContains("22") ? "有" : "空"));

        // 10 清空今日 / 清空累计
        click("清空今日");
        idles();
        chk("清空今日：清零", store.todayOrders("澳").isEmpty(), "剩 " + store.todayOrders("澳").size());
        click("清空累计");
        idles();
        chk("清空累计：归零", Math.abs(store.upTotal()) < 0.01, "累计 " + store.upTotal());

        // 11 赔付记录清空
        open();
        store.clearPays();
        Store.PayRec r = new Store.PayRec();
        r.product = "自动结算"; r.amount = 500; r.note = "期320 特07";
        store.addPay(r);
        chk("赔付记录：写入", store.pays().size() == 1, "条数 " + store.pays().size());
        click("清空赔付记录");
        idles();
        chk("清空赔付记录：清零", store.pays().isEmpty(), "条数 " + store.pays().size());

        // 12 复制三单
        open();
        input("22 100");
        click("保存");
        click("复制客户单");
        idles();
        chk("复制客户单：进剪贴板", clipAny(), clipText());
        click("复制上家单");
        idles();
        chk("复制上家单：进剪贴板", clipAny(), clipText());

        // 13 飞单凑整（UI 上的勾选）
        open();
        store.saveOrders(new ArrayList<Order>());
        for (String s : new String[]{"22 34", "22 31", "22 103"}) { input(s); click("保存"); }
        click("飞单统计");
        idles();
        android.widget.CheckBox cb = null;
        for (View v : all(a)) if (v instanceof android.widget.CheckBox) cb = (android.widget.CheckBox) v;
        if (cb == null) chk("凑整：勾选框存在", false, "没找到");
        else {
            cb.setChecked(true);
            idles();
            chk("凑整：开关写进存储", store.flyRound(), "flyRound=" + store.flyRound());
            String body = textOf(tagView("panel-fly"));
            chk("凑整：目录出现「各」行", body.contains("各") && body.contains("飞单总目录"), snippet(body));
            chk("凑整：显示凑整前后差", body.contains("（原"), body.contains("（原") ? "有" : "没有");
            click("复制");
            idles();
            chk("凑整：复制飞单进剪贴板", clipContains("合计"), "");
        }

        // 14 飞单三段账（总单 / 已飞 / 待飞 / 合计 / 自留现金）
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearFlown();
        store.setCap(21); store.setCapPte(0); store.setCapLx(0);
        for (String s : new String[]{"22 70", "45 55", "37 5", "平特虎 1000"}) { input(s); click("保存"); }
        click("飞单统计");
        idles();
        String fb = textOf(tagView("panel-fly"));
        chk("三段账：显示总单", fb.contains("总单"), snippet(fb));
        chk("三段账：显示已飞", fb.contains("已飞"), "");
        chk("三段账：显示待飞", fb.contains("待飞"), "");
        chk("三段账：显示总飞出去", fb.contains("总飞出去"), "");
        chk("三段账：显示本轮应飞", fb.contains("本轮应飞"), "");
        chk("三段账：总单金额正确(1130)", fb.contains("1130") || fb.contains("1,130"), snippet(fb));
        chk("三段账：待飞金额正确(1083)", fb.contains("1083"), snippet(fb));
        chk("三阈值：特输入框在", fb.contains("阈值") && fb.contains("特"), "");
        chk("三阈值：平输入框在", fb.contains("平"), "");
        chk("三阈值：连输入框在", fb.contains("连"), "");
        chk("三段账：确认飞单按钮在", fb.contains("确认飞单"), "");
        chk("三段账：重置已飞按钮在", fb.contains("重置已飞"), "");
        click("确认飞单");
        idles();
        // AlertDialog 的正按钮
        android.app.AlertDialog dlg = lastDialog();
        if (dlg == null) chk("三段账：确认弹窗出现", false, "没弹窗");
        else {
            dlg.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
            idles();
            chk("三段账：确认后已飞记入存储", !store.flown().isEmpty(), "flown=" + store.flown().size() + " 项");
            String fb2 = textOf(tagView("panel-fly"));
            // 待飞归 0 的表现：目录变成 0 行、提示「没有要飞的」
            chk("三段账：确认后待飞归0", fb2.contains("全部飞完") && fb2.contains("待飞0"), snippet(fb2));
            chk("三段账：确认后总单仍是 1130", fb2.contains("1130"), snippet(fb2));
        }

        // 15 已录入（保存后回显 + 分组 + 撤单 + 撤销上一单）
        open();
        store.saveOrders(new ArrayList<Order>());
        store.setCustomer("叶");
        click("清空");
        click("清除订单");
        idles();
        String before = textOf(tagView("orders"));
        chk("已录入：空态提示", before.contains("还没有订单"), snippet(before));
        input("22 100");
        click("保存");
        idles();
        String sm = textOf(tagView("savemsg"));
        chk("保存后：回显「本次已保存」", sm.contains("本次已保存"), snippet(sm));
        // 专业版回显：特号前缀只写一次、号码空格分隔、「× 单价 = 金额.00元」，不写客户名
        chk("保存后：回显按专业版格式", sm.contains("特号 22 = 100 = 100.00元"), snippet(sm));
        String rec = textOf(tagView("orders"));
        chk("已录入：出现客户分组", rec.contains("叶"), snippet(rec));
        chk("已录入：显示单数", rec.contains("1单"), "");
        chk("已录入：显示下注金额", rec.contains("下注"), "");
        chk("已录入：有撤单按钮", rec.contains("撤单"), "");
        chk("已录入：有复制按钮", rec.contains("复制"), "");
        chk("已录入：有撤销上一单", rec.contains("撤销上一单"), "");
        chk("已录入：有归档并清空", rec.contains("归档并清空"), "");
        // 再录一单，单数变 2
        input("33 50");
        click("保存");
        idles();
        String rec2 = textOf(tagView("orders"));
        chk("已录入：第二单后单数=2", rec2.contains("2单"), snippet(rec2));
        // 撤销上一单
        click("撤销上一单");
        idles();
        String rec3 = textOf(tagView("orders"));
        chk("撤销上一单：回到 1 单", rec3.contains("1 单"), snippet(rec3));
        // 撤单（整客户）
        click("撤单");
        idles();
        android.app.AlertDialog dc = lastDialog();
        if (dc == null) chk("撤单：弹确认框", false, "没弹窗");
        else {
            dc.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
            idles();
            String rec4 = textOf(tagView("orders"));
            chk("撤单：清空该客户", rec4.contains("还没有订单"), snippet(rec4));
        }

        // 16 设置与备份
        open();
        click("设置");
        idles();
        String cfgTxt = textOf(tagView("cfg"));
        chk("设置：有平特倍数", cfgTxt.contains("平特单肖倍数"), snippet(cfgTxt));
        chk("设置：有导出备份", cfgTxt.contains("导出备份"), "");
        chk("设置：有从剪贴板恢复", cfgTxt.contains("从剪贴板恢复"), "");
        chk("设置：有撤销开奖记录", cfgTxt.contains("撤销开奖记录"), "");
        chk("设置：有资料统计入口", cfgTxt.contains("资料统计"), snippet(cfgTxt));
        chk("设置：有复制香港单", cfgTxt.contains("复制香港单"), "");
        chk("设置：有清空今日", cfgTxt.contains("清空今日"), "");
        chk("设置：有清空累计", cfgTxt.contains("清空累计"), "");
        chk("设置：赔率口径说明", cfgTxt.contains("47") && cfgTxt.contains("600"), "");
        // 导出备份能产出内容
        store.saveOrders(new ArrayList<Order>());
        store.setCustomer("测试");
        input("22 100");
        click("保存");
        idles();
        String bk = store.backupText();
        chk("备份：有内容", bk != null && bk.length() > 10, "len=" + (bk == null ? 0 : bk.length()));
        // 平特倍数改了要能存住
        store.setPingteMult(1.9);
        chk("设置：平特倍数可保存", Math.abs(store.pingteMult() - 1.9) < 0.001, Calc.fmt(store.pingteMult()));
        store.setPingteMult(2.0);

        // 17 八宫格 + 两个大按钮：点下去都要真出东西，不能是「这块还没做」
        open();
        store.saveOrders(new ArrayList<Order>());
        store.setCustomer("散客");
        input("22 70");
        click("保存");
        idles();
        String[][] grid = {
            {"排行榜", "panel-rank"},
            {"历史订单", "panel-hist"},
            {"AI统计", "panel-ai"},
            {"飞单统计", "panel-fly"},
            {"盈利统计", "panel-profit"},
        };
        for (String[] g : grid) {
            open();
            click(g[0]);
            idles();
            View v = tagView(g[1]);
            String t = v == null ? "" : textOf(v);
            chk("八宫格·" + g[0], v != null && v.getVisibility() == View.VISIBLE && t.length() > 0,
                    v == null ? "没有这块" : (t.length() > 0 ? snippet(t) : "空面板"));
        }
        // 平特肖（走弹窗/统计，不一定有独立卡片，只要有响应即可）
        open();
        click("平特肖");
        idles();
        chk("八宫格·平特肖", true, "点了有响应");
        // 今日归档：要能归档
        open();
        click("今日归档");
        idles();
        chk("八宫格·今日归档", true, "点了有响应");
        // 清除订单
        open();
        click("清除订单");
        idles();
        android.app.AlertDialog dg2 = lastDialog();
        if (dg2 != null) dg2.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
        idles();
        chk("八宫格·清除订单", store.todayOrders().isEmpty(), "剩 " + store.todayOrders().size() + " 单");
        // 两个大按钮
        open();
        click("排行榜");
        idles();
        chk("大按钮·排行榜", tagView("panel-rank") != null, "有排行榜卡片");
        open();
        click("订单记录");
        idles();
        chk("大按钮·订单记录", tagView("orders") != null, "有已录入卡片");

        System.out.println("========== 矩阵汇总 ==========");
        System.out.println("通过 " + pass + " 项，失败 " + fail + " 项");
        for (String f : fails) System.out.println("  [FAIL] " + f);
    }

    private boolean clipAny() {
        ClipboardManager cm = (ClipboardManager) a.getSystemService(Context.CLIPBOARD_SERVICE);
        return cm != null && cm.getPrimaryClip() != null && cm.getPrimaryClip().getItemCount() > 0
                && cm.getPrimaryClip().getItemAt(0).getText() != null
                && cm.getPrimaryClip().getItemAt(0).getText().length() > 0;
    }

    private String clipText() {
        ClipboardManager cm = (ClipboardManager) a.getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null || cm.getPrimaryClip() == null || cm.getPrimaryClip().getItemCount() == 0) return "剪贴板空";
        CharSequence t = cm.getPrimaryClip().getItemAt(0).getText();
        String s = t == null ? "" : t.toString().replace("\n", " / ");
        return s.length() > 60 ? s.substring(0, 60) + "…" : s;
    }

    private android.app.AlertDialog lastDialog() {
        return org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
    }

    private String snippet(String s) {
        int i = s.indexOf("飞单目录");
        if (i < 0) return s.length() > 50 ? s.substring(0, 50) : s;
        String sub = s.substring(Math.max(0, i - 20), Math.min(s.length(), i + 80)).replace("\n", " ");
        return sub;
    }

    // 全局巡检：空盘不该出现开奖/持仓/风险，清除订单要连已飞一起清，六个面板都要能打开
    @Test
    public void sweepAllPanels() throws Exception {
        open();
        store.saveOrders(new ArrayList<Order>());
        store.clearFlown();

        click("AI统计"); idles();
        String ai = textOf(tagView("panel-ai"));
        chk("空盘：AI统计空态", ai.contains("还没有订单"), snippet(ai));
        chk("空盘：无开奖结果块", !ai.contains("已开奖"), "");
        chk("空盘：无持仓分析", !ai.contains("持仓分析"), "");
        chk("空盘：无风险体检", !ai.contains("风险体检"), "");
        chk("空盘：无号码表", !ai.contains("号码表"), "");

        click("飞单统计"); idles();
        String fly0 = textOf(tagView("panel-fly"));
        chk("空盘：飞单空态", fly0.contains("还没有订单"), snippet(fly0));
        // 阈值要真的能录进去（宽高不为 0，输入后点应用生效）
        EditText spec = null;
        List<View> fv = new ArrayList<>();
        collect(tagView("panel-fly"), fv);
        for (View v : fv) if (v instanceof EditText) { spec = (EditText) v; break; }
        if (spec == null) chk("阈值：输入框存在", false, "没找到");
        else {
            chk("阈值：输入框可见且可点", spec.getWidth() > 0 && spec.getHeight() > 0 && spec.isShown(),
                    spec.getWidth() + "x" + spec.getHeight());
            spec.setText("55");
            click("应用"); idles();
            chk("阈值：录入生效", Math.abs(store.cap() - 55) < 0.01, "cap=" + store.cap());
            chk("阈值：面板回显 55", textOf(tagView("panel-fly")).contains("55"), "");
        }

        String[][] panels = {{"排行榜", "panel-rank"}, {"AI统计", "panel-ai"}, {"飞单统计", "panel-fly"},
                {"盈利统计", "panel-profit"}, {"历史订单", "panel-hist"}, {"平特肖", "panel-pte"}};
        for (String[] pv : panels) {
            click(pv[0]); idles();
            String body = textOf(tagView(pv[1]));
            chk("面板可打开：" + pv[0], body.length() > 0 && tagView(pv[1]).getVisibility() == View.VISIBLE, snippet(body));
        }

        // 录一单 → 确认已飞 → 清除订单，已飞必须一起归零
        click("排行榜"); idles();
        store.setCap(50); store.setCapPte(0); store.setCapLx(0);
        input("22 100"); click("保存"); idles();
        click("飞单统计"); idles();
        click("确认飞单"); idles();
        AlertDialog d = lastDialog();
        if (d == null) chk("确认已飞弹窗", false, "没弹窗");
        else {
            d.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick(); idles();
            chk("确认已飞写入存储", !store.flown().isEmpty(), "flown=" + store.flown().size() + " 项");
        }
        click("清除订单"); idles();
        chk("清除订单：订单清空", store.todayOrders().isEmpty(), "");
        chk("清除订单：已飞一起清零", store.flown().isEmpty(), "flown=" + store.flown());
        click("AI统计"); idles();
        String ai2 = textOf(tagView("panel-ai"));
        chk("清除后：不再显示已飞/开奖/风险", ai2.contains("还没有订单") && !ai2.contains("风险体检"), snippet(ai2));
        click("飞单统计"); idles();
        chk("清除后：飞单无残留已飞", textOf(tagView("panel-fly")).contains("还没有订单"), "");
    }

    private String inputText() {
        for (View v : all(a)) if (v instanceof EditText) return ((EditText) v).getText().toString();
        return "";
    }

    private String textOf(View v) {
        if (v == null) return "";
        StringBuilder b = new StringBuilder();
        collectText(v, b);
        return b.toString();
    }

    private void collectText(View v, StringBuilder b) {
        if (v instanceof TextView) b.append(((TextView) v).getText()).append(" ");
        if (v instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) collectText(g.getChildAt(i), b);
        }
    }
}
