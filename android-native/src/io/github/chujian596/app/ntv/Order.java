package io.github.chujian596.app.ntv;

import java.util.*;

/** 一注订单：codes 里每个元素代表一个可单独结算的玩法，price 是这一注的单价 */
public class Order {
    public String id = "";
    public String customer = "";
    public String shop = "澳";      // 澳 / 港，两池分开算
    public List<String> codes = new ArrayList<>();
    public double price = 0;
    public boolean isPer = false;   // true = 各数（每个号码各多少钱）
    public long ts = System.currentTimeMillis();
    public String raw = "";

    /** isPer（各数）时 price 是每个号的单价；否则 price 就是这一笔的总金额 */
    public double amount() { return isPer ? price * codes.size() : price; }

    public String toJson() {
        StringBuilder b = new StringBuilder("{");
        b.append("\"id\":\"").append(esc(id)).append("\",");
        b.append("\"customer\":\"").append(esc(customer)).append("\",");
        b.append("\"shop\":\"").append(esc(shop)).append("\",");
        b.append("\"price\":").append(price).append(",");
        b.append("\"isPer\":").append(isPer).append(",");
        b.append("\"ts\":").append(ts).append(",");
        b.append("\"raw\":\"").append(esc(raw)).append("\",");
        b.append("\"codes\":[");
        for (int i = 0; i < codes.size(); i++) {
            if (i > 0) b.append(",");
            b.append("\"").append(esc(codes.get(i))).append("\"");
        }
        b.append("]}");
        return b.toString();
    }

    static String esc(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }
}
