package io.github.chujian596.app.ntv;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.*;

/** 历史归档：每期把当天订单存成一份快照，清空当前盘面但留底 */
public class Archive {

    private final SharedPreferences sp;

    public Archive(Context c) {
        sp = c.getSharedPreferences("ntv_arch", Context.MODE_PRIVATE);
    }

    /** 存一份快照，返回这次存了多少单 */
    public int save(String label, List<Order> orders) {
        if (orders.isEmpty()) return 0;
        try {
            JSONArray arr = new JSONArray();
            for (Order o : orders) arr.put(new JSONObject(o.toJson()));
            JSONObject pack = new JSONObject();
            pack.put("label", label);
            pack.put("at", System.currentTimeMillis());
            pack.put("count", orders.size());
            pack.put("orders", arr);
            sp.edit().putString("a_" + System.currentTimeMillis(), pack.toString()).apply();
            return orders.size();
        } catch (Exception e) {
            return 0;
        }
    }

    /** 归档列表：文件名 → 摘要，按时间倒序 */
    public List<String[]> list() {
        List<String[]> out = new ArrayList<>();
        for (Map.Entry<String, ?> e : sp.getAll().entrySet()) {
            try {
                JSONObject o = new JSONObject(String.valueOf(e.getValue()));
                out.add(new String[]{
                        e.getKey(),
                        o.optString("label"),
                        String.valueOf(o.optInt("count")),
                        o.optLong("at") > 0
                                ? new java.text.SimpleDateFormat("MM-dd HH:mm", Locale.CHINA)
                                .format(new Date(o.optLong("at"))) : ""
                });
            } catch (Exception ignored) {}
        }
        out.sort((a, b) -> b[3].compareTo(a[3]));
        return out;
    }

    public List<Order> load(String key) {
        List<Order> list = new ArrayList<>();
        try {
            JSONObject pack = new JSONObject(sp.getString(key, "{}"));
            JSONArray arr = pack.optJSONArray("orders");
            if (arr == null) return list;
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                Order od = new Order();
                od.id = o.optString("id");
                od.customer = o.optString("customer");
                od.price = o.optDouble("price");
                od.isPer = o.optBoolean("isPer");
                od.ts = o.optLong("ts");
                JSONArray cs = o.optJSONArray("codes");
                if (cs != null) for (int j = 0; j < cs.length(); j++) od.codes.add(cs.getString(j));
                list.add(od);
            }
        } catch (Exception ignored) {}
        return list;
    }

    public void remove(String key) {
        sp.edit().remove(key).apply();
    }

    public int count() {
        return sp.getAll().size();
    }
}
