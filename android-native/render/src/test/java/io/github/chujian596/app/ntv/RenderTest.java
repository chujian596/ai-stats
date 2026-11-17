package io.github.chujian596.app.ntv;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowToast;

import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.List;

import static org.robolectric.Shadows.shadowOf;

/** 在电脑上把界面真渲染成图片，并顺带把主要流程点一遍 */
@RunWith(org.robolectric.RobolectricTestRunner.class)
@Config(manifest = Config.NONE, sdk = 30, qualifiers = "w411dp-h891dp-xhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class RenderTest {

    private void shot(Activity a, String name) throws Exception {
        android.view.ViewGroup content = (android.view.ViewGroup) a.findViewById(android.R.id.content);
        float density = a.getResources().getDisplayMetrics().density;
        int w = a.getResources().getDisplayMetrics().widthPixels;
        if (w <= 0) w = (int) (411 * density);
        if (content.getChildCount() > 0) {
            View inner = content.getChildAt(0);
            inner.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
            int realH = inner.getMeasuredHeight();
            inner.layout(0, 0, w, realH);
            Bitmap bmp = Bitmap.createBitmap(w, Math.max(1, realH), Bitmap.Config.ARGB_8888);
            Canvas cv = new Canvas(bmp);
            cv.drawColor(0xFFFFFFFF);
            inner.draw(cv);
            File dir = new File("/tmp/shots");
            dir.mkdirs();
            FileOutputStream out = new FileOutputStream(new File(dir, name + ".png"));
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
            out.close();
            System.out.println("SHOT " + name + " " + bmp.getWidth() + "x" + bmp.getHeight());
        }
    }

    private EditText input(Activity a) {
        return (EditText) a.getWindow().getDecorView().findViewWithTag("input");
    }

    private void click(Activity a, String text) {
        List<View> all = new ArrayList<>();
        collect(a.getWindow().getDecorView(), all);
        for (View v : all) {
            if (v instanceof Button && text.equals(((Button) v).getText().toString())) {
                v.performClick();
                shadowOf(a.getMainLooper()).idle();
                System.out.println("CLICK " + text + " -> " + ShadowToast.getTextOfLatestToast());
                return;
            }
        }
        System.out.println("CLICK " + text + " NOT FOUND");
    }

    private void collect(View v, List<View> out) {
        out.add(v);
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup g = (android.view.ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) collect(g.getChildAt(i), out);
        }
    }

    @Test
    public void gridButtons() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        EditText in = input(a);
        in.setText("特码22 140\n特码34 90\n平特虎 1000");
        click(a, "保存");
        click(a, "排行榜");
        android.widget.ScrollView sv = (android.widget.ScrollView) a.getWindow().getDecorView().findViewWithTag("scroll");
        System.out.println("scrollY after 排行榜 = " + (sv == null ? "n/a" : sv.getScrollY()));
        click(a, "订单记录");
        for (String name : new String[]{"AI统计", "盈利统计", "平特肖"}) {
            click(a, name);
            android.app.AlertDialog d2 = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
            if (d2 != null) {
                StringBuilder all = new StringBuilder();
                List<View> vs2 = new ArrayList<>();
                collect(d2.getWindow().getDecorView(), vs2);
                for (View v : vs2) {
                    if (v instanceof android.widget.TextView && !(v instanceof Button)) {
                        CharSequence t = ((android.widget.TextView) v).getText();
                        if (t != null && t.length() > 12) all.append(t).append(" / ");
                    }
                }
                System.out.println("PANEL " + name + " >>> " + all.toString().replace("\n", " | "));
                d2.dismiss();
            } else {
                System.out.println("PANEL " + name + " >>> none");
            }
        }
        click(a, "今日归档");
        shot(a, "04_点了按钮");
    }


    /** 澳门单与香港单必须分开：切店后录的单不能算进另一店 */
    @Test
    public void shopSplit() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        io.github.chujian596.app.ntv.Store st = new io.github.chujian596.app.ntv.Store(a);
        st.saveOrders(new java.util.ArrayList<io.github.chujian596.app.ntv.Order>());

        // 澳门录一单
        input(a).setText("22 100");
        for (View v : allViews(a)) if (v instanceof Button && "保存".equals(((Button) v).getText().toString())) { ((Button) v).performClick(); break; }
        int mo = st.todayOrders("澳").size();
        System.out.println("CHECK 澳门单数=" + mo + " 香港单数=" + st.todayOrders("港").size());

        // 切香港再录一单
        android.widget.TextView shop = (android.widget.TextView) a.getWindow().getDecorView().findViewWithTag("shop");
        System.out.println("CHECK 切店前标签=" + shop.getText());
        shop.performClick();
        System.out.println("CHECK 切店后标签=" + shop.getText());
        input(a).setText("23 200");
        for (View v : allViews(a)) if (v instanceof Button && "保存".equals(((Button) v).getText().toString())) { ((Button) v).performClick(); break; }

        int mo2 = st.todayOrders("澳").size();
        int hk2 = st.todayOrders("港").size();
        System.out.println("CHECK 切店后 澳门=" + mo2 + " 香港=" + hk2);
        System.out.println("SHOP " + (mo == 1 && mo2 == 1 && hk2 == 1 ? "PASS" : "FAIL"));

        // 香港池金额
        System.out.println("CHECK 香港合计=" + st.totalAmount(st.todayOrders("港")));
        shot(a, "p1_店铺分池");
    }

    private java.util.List<View> allViews(Activity a) {
        java.util.List<View> out = new ArrayList<>();
        collect(a.getWindow().getDecorView(), out);
        return out;
    }

    /** 面板展开收起：点按钮要真展开，再点收起 */
    /** 属性注单两种弹窗：单项三选项 / 多项一次性选 */
    @Test
    public void waveDialogs() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();

        // 单项：红波 100
        input(a).setText("红波 100");
        click(a, "保存");
        shadowOf(a.getMainLooper()).idle();
        android.app.AlertDialog d1 = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        if (d1 == null) { System.out.println("WAVE 单项没弹窗 FAIL"); return; }
        android.widget.ListView lv = d1.getListView();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < lv.getAdapter().getCount(); i++) sb.append(lv.getAdapter().getItem(i)).append(" / ");
        System.out.println("WAVE 单项弹窗 选项=" + sb);
        // 选「总额」：应记 100 元
        lv.performItemClick(lv.getChildAt(0), 0, lv.getAdapter().getItemId(0));
        shadowOf(a.getMainLooper()).idle();
        System.out.println("WAVE 选总额后 顶部=" + topSummary(a));

        // 清空重来，选「各号」
        click(a, "清空");
        shadowOf(a.getMainLooper()).idle();
        input(a).setText("红波 100");
        click(a, "保存");
        shadowOf(a.getMainLooper()).idle();
        android.app.AlertDialog d1b = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        android.widget.ListView lvb = d1b.getListView();
        lvb.performItemClick(lvb.getChildAt(1), 1, lvb.getAdapter().getItemId(1));
        shadowOf(a.getMainLooper()).idle();
        System.out.println("WAVE 选各号后 顶部=" + topSummary(a));
        click(a, "清空");
        shadowOf(a.getMainLooper()).idle();

        // 多项：红波 + 单数
        input(a).setText("红波 100\n单数 200");
        click(a, "保存");
        shadowOf(a.getMainLooper()).idle();
        android.app.AlertDialog dd = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        if (dd == null) { System.out.println("WAVE 多项没弹窗 FAIL"); return; }
        StringBuilder txt = new StringBuilder();
        DialogText(dd.getWindow().getDecorView(), txt);
        System.out.println("WAVE 多项弹窗 内容=" + txt);
    }

    private String topSummary(Activity a) {
        for (View v : allViews(a)) {
            if (v instanceof android.widget.TextView && !(v instanceof Button)) {
                CharSequence c = ((android.widget.TextView) v).getText();
                if (c != null && c.toString().contains("单")) return c.toString();
            }
        }
        return "?";
    }

    private void DialogText(View v, StringBuilder b) {
        if (v instanceof android.widget.TextView && !(v instanceof Button)) {
            CharSequence c = ((android.widget.TextView) v).getText();
            if (c != null && c.length() > 3) b.append(c).append(" | ");
        }
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup g = (android.view.ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) DialogText(g.getChildAt(i), b);
        }
    }

    @Test
    public void panelsToggle() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        android.view.ViewGroup root = (android.view.ViewGroup) a.findViewById(android.R.id.content);
        String[][] map = {{"AI统计","risk"},{"飞单统计","split"},{"盈利统计","settle"},{"排行榜","board"},{"历史订单","archive"}};
        for (String[] m : map) {
            android.view.View v = findTagDeep(root, m[1]);
            if (v == null) { System.out.println("PANEL " + m[0] + " 找不到容器"); continue; }
            int before = v.getVisibility();
            clickText(a, m[0]);
            int after = v.getVisibility();
            System.out.println("PANEL " + m[0] + " 点前=" + before + " 点后=" + after
                    + (after != before ? " PASS" : " 没变化"));
        }
    }

    private android.view.View findTagDeep(android.view.View v, String tag) {
        if (tag.equals(v.getTag())) return v;
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup g = (android.view.ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) {
                android.view.View r = findTagDeep(g.getChildAt(i), tag);
                if (r != null) return r;
            }
        }
        return null;
    }

    private void clickText(Activity a, String text) {
        for (View v : allViews(a)) if (v instanceof Button && text.equals(((Button) v).getText().toString())) { ((Button) v).performClick(); return; }
    }

    @Test
    public void clickEveryButton() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        EditText in = input(a);
        in.setText("22 140\n34 90\n平特虎 1000\n三中三:34,32,46 5");
        click(a, "保存");

        List<View> all = new ArrayList<>();
        collect(a.getWindow().getDecorView(), all);
        int total = 0, bad = 0;
        for (View v : all) {
            if (!(v instanceof Button)) continue;
            String label = String.valueOf(((Button) v).getText());
            if (label.isEmpty()) continue;
            total++;
            try {
                ((Button) v).performClick();
                shadowOf(a.getMainLooper()).idle();
                android.app.AlertDialog d = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
                String note;
                if (d != null && d.isShowing()) {
                    note = "弹窗";
                    d.dismiss();
                } else {
                    CharSequence t = org.robolectric.shadows.ShadowToast.getTextOfLatestToast();
                    note = "toast=" + (t == null ? "-" : t);
                }
                System.out.println("BTN ok  " + label + " → " + note);
            } catch (Throwable e) {
                bad++;
                System.out.println("BTN FAIL " + label + " → " + e);
            }
        }
        System.out.println("BTN 合计 " + total + " 个，异常 " + bad + " 个");
    }

    @Test
    public void empty() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        shot(a, "01_空盘");
    }

    @Test
    public void settle() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        EditText in = input(a);
        in.setText("特码04 25\n特码22 140\n特码34 90\n特码45 85\n平特虎 1000\n三中三:34,32,46 5");
        click(a, "保存");
        click(a, "手动录入");
        android.app.AlertDialog dlg = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        if (dlg == null) { System.out.println("NO DIALOG"); return; }
        List<View> vs = new ArrayList<>();
        collect(dlg.getWindow().getDecorView(), vs);
        for (View v : vs) {
            if (v instanceof EditText) {
                ((EditText) v).setText("320 05 14 17 32 34 24 + 20");
                break;
            }
        }
        dlg.getButton(android.content.DialogInterface.BUTTON_POSITIVE).performClick();
        shadowOf(a.getMainLooper()).idle();
        click(a, "飞单统计");
        android.app.AlertDialog d3 = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        if (d3 != null) {
            StringBuilder all2 = new StringBuilder();
            List<View> vs3 = new ArrayList<>();
            collect(d3.getWindow().getDecorView(), vs3);
            for (View v : vs3) {
                if (v instanceof android.widget.TextView && !(v instanceof Button)) {
                    CharSequence t = ((android.widget.TextView) v).getText();
                    if (t != null && t.length() > 12) all2.append(t).append(" / ");
                }
            }
            System.out.println("PANEL 飞单统计 >>> " + all2.toString().replace("\n", " | "));
            d3.dismiss();
        }
        click(a, "盈利统计");
        shadowOf(a.getMainLooper()).idle();
        shot(a, "03_开奖结算后");
    }

    @Test
    public void recordAndDraw() throws Exception {
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        shadowOf(a.getMainLooper()).idle();
        EditText in = input(a);
        in.setText("特码22 140\n特码34 90\n特码45 85\n特码04 50\n特码15 50\n平特虎 1000\n三中三:34,32,46 5");
        click(a, "保存");
        shadowOf(a.getMainLooper()).idle();
        // 展开订单面板再截图，否则折叠状态下看不到单
        click(a, "订单记录");
        shadowOf(a.getMainLooper()).idle();
        shot(a, "02_录单后");
    }
}
