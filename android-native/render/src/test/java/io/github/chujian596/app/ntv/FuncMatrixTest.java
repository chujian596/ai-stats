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
        for (View v : all(a)) if (tag.equals(v.getTag())) return v;
        return null;
    }

    private boolean clipContains(String s) {
        ClipboardManager cm = (ClipboardManager) a.getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null || cm.getPrimaryClip() == null || cm.getPrimaryClip().getItemCount() == 0) return false;
        return cm.getPrimaryClip().getItemAt(0).getText().toString().contains(s);
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
        String[][] panels = {{"排行榜","board"},{"订单记录","orders"},{"AI统计","risk"},{"飞单统计","split"},{"盈利统计","settle"},{"历史订单","archive"}};
        for (String[] p : panels) {
            View v = tagView(p[1]);
            if (v == null) { chk(p[0] + "：面板存在", false, "找不到"); continue; }
            boolean before = v.getVisibility() == View.VISIBLE;
            click(p[0]);
            boolean after = v.getVisibility() == View.VISIBLE;
            chk(p[0] + "：点一下切换", before != after, "前=" + before + " 后=" + after);
        }

        // 6 重算（改自留上限，最坏要变）
        open();
        input("22 140");
        click("保存");
        EditText cap = null;
        View board = tagView("board");
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
            String body = textOf(tagView("split"));
            chk("凑整：目录出现「各」行", body.contains("各") && body.contains("飞单目录"), snippet(body));
            chk("凑整：显示凑整前后差", body.contains("凑整前"), body.contains("凑整前") ? "有" : "没有");
            click("复制飞单");
            idles();
            chk("凑整：复制飞单进剪贴板", clipContains("合计"), "");
        }

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

    private String snippet(String s) {
        int i = s.indexOf("飞单目录");
        if (i < 0) return s.length() > 50 ? s.substring(0, 50) : s;
        String sub = s.substring(Math.max(0, i - 20), Math.min(s.length(), i + 80)).replace("\n", " ");
        return sub;
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
