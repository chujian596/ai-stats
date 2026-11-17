package io.github.chujian596.app.ntv;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.*;

/** 本地存储：订单、开奖、设置全在 SharedPreferences 里，断网照样读写 */
public class Store {
    private final SharedPreferences sp;
    private static final String K_ORDERS = "orders";
    private static final String K_DRAW = "draw";
    private static final String K_PINGTE = "pingteMult";
    private static final String K_CUSTOMER = "customer";
    private static final String K_CAP = "cap";
    private static final String K_UPCUM = "upCum";
    private static final String K_DAY_KEY = "upDayKey";
    private static final String K_DAY_BASE = "upDayBase";
    private static final String K_WEEK_KEY = "upWeekKey";
    private static final String K_WEEK_BASE = "upWeekBase";

    public Store(Context c) {
        sp = c.getSharedPreferences("ntv", Context.MODE_PRIVATE);
    }

    public SharedPreferences sp() { return sp; }

    /** 全部订单 + 关键设置做成一段可粘贴的文本 */
    public String backupText() {
        StringBuilder b = new StringBuilder("NTV-BACKUP v1\n");
        b.append("pingteMult=").append(pingteMult()).append("\n");
        b.append("cap=").append(cap()).append("\n");
        b.append("customer=").append(customer()).append("\n");
        for (Order o : orders()) b.append(o.toJson()).append("\n");
        return b.toString();
    }

    /** 从备份文本恢复，返回恢复的订单数，-1 表示格式不对 */
    public int restoreFromText(String txt) {
        try {
            List<Order> list = new ArrayList<>();
            for (String line : txt.split("\n")) {
                String t = line.trim();
                if (!t.startsWith("{")) continue;
                org.json.JSONObject o = new org.json.JSONObject(t);
                Order od = new Order();
                od.id = o.optString("id");
                od.customer = o.optString("customer");
                od.shop = o.optString("shop", "澳");
                od.price = o.optDouble("price");
                od.isPer = o.optBoolean("isPer");
                od.ts = o.optLong("ts");
                org.json.JSONArray cs = o.optJSONArray("codes");
                if (cs != null) for (int j = 0; j < cs.length(); j++) od.codes.add(cs.getString(j));
                list.add(od);
            }
            for (String line : txt.split("\n")) {
                if (line.startsWith("pingteMult=")) setPingteMult(Double.parseDouble(line.substring(11).trim()));
                if (line.startsWith("cap=")) setCap(Double.parseDouble(line.substring(4).trim()));
                if (line.startsWith("customer=")) setCustomer(line.substring(9).trim());
            }
            saveOrders(list);
            return list.size();
        } catch (Exception e) {
            return -1;
        }
    }

    // ---------- 订单 ----------
    public List<Order> orders() {
        List<Order> list = new ArrayList<>();
        try {
            JSONArray arr = new JSONArray(sp.getString(K_ORDERS, "[]"));
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                Order od = new Order();
                od.id = o.optString("id");
                od.customer = o.optString("customer");
                od.shop = o.optString("shop", "澳");
                od.price = o.optDouble("price", 0);
                od.isPer = o.optBoolean("isPer", false);
                od.ts = o.optLong("ts");
                od.raw = o.optString("raw");
                JSONArray cs = o.optJSONArray("codes");
                if (cs != null) for (int j = 0; j < cs.length(); j++) od.codes.add(cs.getString(j));
                list.add(od);
            }
        } catch (Exception ignored) {}
        return list;
    }

    public void saveOrders(List<Order> list) {
        JSONArray arr = new JSONArray();
        try {
            for (Order o : list) arr.put(new JSONObject(o.toJson()));
        } catch (Exception ignored) {}
        sp.edit().putString(K_ORDERS, arr.toString()).apply();
    }

    public void addOrder(Order o) {
        List<Order> l = orders();
        o.id = String.valueOf(System.currentTimeMillis());
        l.add(0, o);
        saveOrders(l);
    }

    public void removeOrder(String id) {
        List<Order> l = orders();
        Iterator<Order> it = l.iterator();
        while (it.hasNext()) if (it.next().id.equals(id)) it.remove();
        saveOrders(l);
    }

    /** 今天录的单（不区分店铺） */
    public List<Order> todayOrders() { return todayOrders(null); }

    /** 今天录的单：shop 为 澳/港 时只取该店；null 取全部 */
    public List<Order> todayOrders(String shop) {
        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(new Date());
        List<Order> out = new ArrayList<>();
        for (Order o : orders()) {
            String d = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA)
                    .format(new Date(o.ts));
            if (!d.equals(today)) continue;
            if (shop != null && !shop.equals(o.shop)) continue;
            out.add(o);
        }
        return out;
    }

    /** 某一店全部未归档的单（做香港单复制用） */
    public List<Order> ordersOf(String shop) {
        List<Order> out = new ArrayList<>();
        for (Order o : orders()) if (shop == null || shop.equals(o.shop)) out.add(o);
        return out;
    }

    // ---------- 开奖 ----------
    public Draw draw() { return draw(null); }

    /** 按店铺取开奖：null 取默认池 */
    public Draw draw(String shop) {
        Draw d = new Draw();
        try {
            String key = (shop == null || shop.isEmpty()) ? K_DRAW : K_DRAW + "_" + shop;
            JSONObject o = new JSONObject(sp.getString(key, "{}"));
            if (!o.has("period") && shop != null) {
                o = new JSONObject(sp.getString(K_DRAW, "{}"));   // 老数据兜底
            }
            d.period = o.optInt("period");
            d.special = o.optInt("special");
            JSONArray a = o.optJSONArray("regular");
            if (a != null) for (int i = 0; i < a.length(); i++) d.regular.add(a.getInt(i));
            d.lottery = o.optString("lottery", "澳");
        } catch (Exception ignored) {}
        return d;
    }

    public void saveDraw(Draw d) { saveDraw(d, null); }

    public void saveDraw(Draw d, String shop) {
        try {
            String key = (shop == null || shop.isEmpty()) ? K_DRAW : K_DRAW + "_" + shop;
            JSONObject o = new JSONObject();
            o.put("period", d.period);
            o.put("special", d.special);
            JSONArray a = new JSONArray();
            for (int n : d.regular) a.put(n);
            o.put("regular", a);
            o.put("lottery", d.lottery);
            sp.edit().putString(key, o.toString()).apply();
        } catch (Exception ignored) {}
    }

    /** 撤销当前店的这一期开奖 */
    public void clearDraw(String shop) {
        String key = (shop == null || shop.isEmpty()) ? K_DRAW : K_DRAW + "_" + shop;
        sp.edit().remove(key).apply();
    }

    // ---------- 赔付记录 ----------
    public static class PayRec {
        public String product = "", note = "", time = "";
        public double amount = 0;
    }

    public List<PayRec> pays() {
        List<PayRec> out = new ArrayList<>();
        try {
            JSONArray arr = new JSONArray(sp.getString("pays", "[]"));
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                PayRec r = new PayRec();
                r.product = o.optString("product");
                r.note = o.optString("note");
                r.time = o.optString("time");
                r.amount = o.optDouble("amount", 0);
                out.add(r);
            }
        } catch (Exception ignored) {}
        return out;
    }

    public void addPay(PayRec r) {
        List<PayRec> l = pays();
        l.add(0, r);
        savePays(l);
    }

    public void removePay(int idx) {
        List<PayRec> l = pays();
        if (idx >= 0 && idx < l.size()) { l.remove(idx); savePays(l); }
    }

    public void clearPays() { sp.edit().putString("pays", "[]").apply(); }

    public double payTotal() {
        double t = 0;
        for (PayRec r : pays()) t += r.amount;
        return t;
    }

    private void savePays(List<PayRec> l) {
        JSONArray arr = new JSONArray();
        try {
            for (PayRec r : l) {
                JSONObject o = new JSONObject();
                o.put("product", r.product);
                o.put("note", r.note);
                o.put("time", r.time);
                o.put("amount", r.amount);
                arr.put(o);
            }
        } catch (Exception ignored) {}
        sp.edit().putString("pays", arr.toString()).apply();
    }

    /** 飞单凑整开关（5 元档），默认关 */
    public boolean flyRound() { return sp.getBoolean("flyRound", false); }
    public void setFlyRound(boolean on) { sp.edit().putBoolean("flyRound", on).apply(); }

    /** 当前店铺，重启后保持 */
    public String shop() { return sp.getString("shop", "澳"); }
    public void setShop(String s) { sp.edit().putString("shop", s).apply(); }

    // ---------- 设置 ----------
    public double pingteMult() {
        return sp.getFloat(K_PINGTE, 2f);
    }

    public void setPingteMult(double v) {
        sp.edit().putFloat(K_PINGTE, (float) v).apply();
    }

    public String customer() {
        return sp.getString(K_CUSTOMER, "散客");
    }

    public void setCustomer(String c) {
        sp.edit().putString(K_CUSTOMER, c).apply();
    }

    // ---------- 盘面阈值 ----------
    public double cap() {
        return sp.getFloat(K_CAP, 100f);
    }

    public void setCap(double v) {
        sp.edit().putFloat(K_CAP, (float) v).apply();
    }

    // ---------- 上家盈亏 ----------
    /** 结算一期：把这一期的差额记进累计，并处理跨天/跨周的起点 */
    public void addUpDelta(double delta, Date now) {
        double cum = sp.getFloat(K_UPCUM, 0f) + delta;
        String day = UpCum.dayKey(now);
        String wk = UpCum.weekKey(now);
        SharedPreferences.Editor e = sp.edit().putFloat(K_UPCUM, (float) cum);
        if (!day.equals(sp.getString(K_DAY_KEY, ""))) {
            e.putString(K_DAY_KEY, day).putFloat(K_DAY_BASE, (float) cum);
        }
        if (!wk.equals(sp.getString(K_WEEK_KEY, ""))) {
            e.putString(K_WEEK_KEY, wk).putFloat(K_WEEK_BASE, (float) cum);
        }
        e.apply();
    }

    public double upTotal() { return sp.getFloat(K_UPCUM, 0f); }

    public double upToday(Date now) {
        if (!UpCum.dayKey(now).equals(sp.getString(K_DAY_KEY, ""))) return 0;
        return UpCum.since(sp.getFloat(K_UPCUM, 0f), sp.getFloat(K_DAY_BASE, 0f));
    }

    public double upWeek(Date now) {
        if (!UpCum.weekKey(now).equals(sp.getString(K_WEEK_KEY, ""))) return 0;
        return UpCum.since(sp.getFloat(K_UPCUM, 0f), sp.getFloat(K_WEEK_BASE, 0f));
    }

    public void clearUpCum() {
        sp.edit().putFloat(K_UPCUM, 0f).putFloat(K_DAY_BASE, 0f).putFloat(K_WEEK_BASE, 0f).apply();
    }

    /** 常用客户：从现有订单里提取，去重 */
    public List<String> customers() {
        LinkedHashSet<String> set = new LinkedHashSet<>();
        String cur = customer();
        if (!cur.isEmpty()) set.add(cur);
        for (Order o : orders()) if (o.customer != null && !o.customer.isEmpty()) set.add(o.customer);
        return new ArrayList<>(set);
    }

    // ---------- 汇总 ----------
    public double totalAmount(List<Order> list) {
        double t = 0;
        for (Order o : list) t += o.amount();
        return t;
    }

    /** 单笔赔付 */
    public double payoutOf(Order o, Draw d) { return Calc.win(o, d, pingteMult()).total; }

    public double totalPayout(List<Order> list, Draw d) {
        double t = 0;
        for (Order o : list) t += Calc.win(o, d, pingteMult()).total;
        return t;
    }
}
