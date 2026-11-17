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
    /**
     * 每个号码各自的金额（与 codes 一一对应）。
     * 专业版一行里可以写多段（04.06各10元 11.21各5元），每段单价不同，
     * 只靠 price/isPer 表达不了，所以单独存一份。为空时回退 price 口径。
     */
    public List<Double> amts = new ArrayList<>();

    /** 某个号码在这笔单里的注额 */
    public double amtOf(String code) {
        int i = codes.indexOf(code);
        if (!amts.isEmpty() && i >= 0 && i < amts.size()) return amts.get(i);
        return isPer ? price : price / Math.max(1, codes.size());
    }

    /** 这笔单的总金额 */
    public double amount() {
        if (!amts.isEmpty()) {
            double s = 0;
            for (double a : amts) s += a;
            return s;
        }
        return isPer ? price * codes.size() : price;
    }

    /** 是不是各号金额都一样（一样就按统一单价显示） */
    public boolean uniformAmt() {
        if (amts.isEmpty()) return true;
        for (double a : amts) if (Math.abs(a - amts.get(0)) > 0.005) return false;
        return true;
    }

    /** 统一单价（各号不一时返回第一段的金额） */
    public double unitPrice() {
        if (!amts.isEmpty()) return amts.get(0);
        return price;
    }

    public String toJson() {
        StringBuilder b = new StringBuilder("{");
        b.append("\"id\":\"").append(esc(id)).append("\",");
        b.append("\"customer\":\"").append(esc(customer)).append("\",");
        b.append("\"shop\":\"").append(esc(shop)).append("\",");
        b.append("\"price\":").append(price).append(",");
        b.append("\"isPer\":").append(isPer).append(",");
        if (!amts.isEmpty()) {
            b.append("\"amts\":[");
            for (int i = 0; i < amts.size(); i++) {
                if (i > 0) b.append(",");
                b.append(amts.get(i));
            }
            b.append("],");
        }
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
