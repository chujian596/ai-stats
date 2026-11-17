package io.github.chujian596.app.ntv;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.*;

/** 开奖抓取：只做一件事——把线上三份数据里最新的一份读回来，失败就用本机缓存 */
public class Net {

    private static final String BASE = "https://aistats-9uo.pages.dev";
    private static final String[] SOURCES = {
            "https://aistats-9uo.pages.dev/api/draw",
            "https://aistats-9uo.pages.dev/draw-latest.json",
            "https://chujian596.github.io/ai-stats/draw-latest.json",
            "https://chujian596.github.io/ai-luandan/draw-latest.json"
    };

    private final SharedPreferences sp;
    private final SimpleDateFormat fmt = new SimpleDateFormat("MM-dd HH:mm", Locale.CHINA);

    public Net(Context c) {
        sp = c.getSharedPreferences("ntv", Context.MODE_PRIVATE);
    }

    /** 拉最新开奖；返回 null 表示全失败 */
    public Draw fetch(String lottery) {
        for (String url : SOURCES) {
            try {
                url = url + (url.contains("?") ? "&" : "?") + "t=" + System.currentTimeMillis();
                String body = get(url);
                if (body == null) continue;
                JSONObject root = new JSONObject(body);
                JSONObject one = root.optJSONObject(lottery.equals("港") ? "hongkong" : "macao");
                if (one == null) continue;
                int period = one.optInt("draw");
                if (period <= 0) period = period + 1;
                org.json.JSONArray arr = one.optJSONArray("numbers");
                if (arr == null || arr.length() < 7) continue;
                List<Integer> regular = new ArrayList<>();
                for (int i = 0; i < 6; i++) regular.add(arr.optInt(i));
                Draw d = new Draw(period, regular, arr.optInt(6));
                org.json.JSONObject self = root.optJSONObject(lottery.equals("港") ? "hongkong" : "macao");
                if (self != null) d.at = self.optString("drawn_at", "");
                org.json.JSONObject nx = root.optJSONObject("next");
                if (nx != null) {
                    org.json.JSONObject onx = nx.optJSONObject(lottery.equals("港") ? "hongkong" : "macao");
                    if (onx != null) { d.nextDraw = onx.optInt("draw"); d.nextAt = onx.optString("draw_at", ""); }
                }
                d.lottery = lottery;
                saveCache(d);
                return d;
            } catch (Exception ignored) {}
        }
        return null;
    }

    private String get(String urlStr) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(urlStr).openConnection();
            c.setConnectTimeout(8000);
            c.setReadTimeout(10000);
            c.setRequestProperty("User-Agent", "ntv/1.0");
            c.setInstanceFollowRedirects(true);
            if (c.getResponseCode() != 200) return null;
            InputStream in = c.getInputStream();
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            in.close();
            return new String(bo.toByteArray(), "UTF-8");
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private void saveCache(Draw d) {
        try {
            sp.edit()
                    .putInt("cachePeriod", d.period)
                    .putInt("cacheSpecial", d.special)
                    .putString("cacheRegular", joinInts(d.regular))
                    .putString("cacheAt", fmt.format(new Date()))
                    .apply();
        } catch (Exception ignored) {}
    }

    public String lastFetchAt() {
        return sp.getString("cacheAt", "");
    }

    public String cachePeriod() {
        int p = sp.getInt("cachePeriod", 0);
        return p > 0 ? String.valueOf(p) : "";
    }

    private String joinInts(List<Integer> l) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < l.size(); i++) { if (i > 0) b.append(","); b.append(l.get(i)); }
        return b.toString();
    }
}
