package io.github.chujian596.app.ntv;

import java.util.*;

/** 赔付计算：口径与专业版一致 */
public class Calc {

    public static final int PAY_SPECIAL = 47;      // 特码
    public static final int PAY_PINGTE = 2;        // 平特单肖（马 1.8）
    public static final double PAY_PINGTE_MA = 1.8;   // 兼容用
    public static final int PAY_EM2 = 60;          // 二中二
    public static final int PAY_EM3 = 600;         // 三中三
    public static final int PAY_ZM2 = 20;          // 三中二

    public static class Line {
        public String label;
        public double bet;
        public double mult;
        public double win;
        Line(String l, double b, double m, double w) { label = l; bet = b; mult = m; win = w; }
        public String text() {
            return label + "　" + fmt(bet) + " ×" + fmt(mult) + " = " + fmt(win);
        }
    }

    public static class Result {
        public double total = 0;
        public List<Line> lines = new ArrayList<>();
    }

    public static String fmt(double v) {
        if (Math.abs(v - Math.round(v)) < 0.005) return String.valueOf((long) Math.round(v));
        return String.format("%.2f", v);
    }

    /** 单个 code 的中奖金额与说明；没中返回 null */
    public static Line hit(Order o, String code, Draw d, double pingteMult) {
        // 每个 code 对应的实际注额：各数时用单价，否则把总金额平摊到每个玩法
        double bet = o.amtOf(code);
        if (code.startsWith("连肖")) {
            String zs = code.substring(2);
            Set<String> hit = Z.hitZodiacs(d.regular, d.special);
            boolean all = true;
            for (char c : zs.toCharArray()) if (!hit.contains(String.valueOf(c))) { all = false; break; }
            if (all) {
                int n = zs.length();
                double base = n == 2 ? 4 : (n == 3 ? 10 : 30);
                double mult = zs.indexOf('马') >= 0 ? base - 0.5 : base;
                return new Line(shortLabel(code), bet, mult, bet * mult);
            }
            return null;
        }
        if (code.startsWith("平特")) {
            String z = code.substring(2);
            boolean hitP = false;
            for (int n : d.regular) if (z.equals(Z.of(n))) { hitP = true; break; }
            if (hitP) {
                double mult = code.equals("平特马") ? 1.8 : pingteMult;
                return new Line(shortLabel(code), bet, mult, bet * mult);
            }
            return null;
        }
        if (code.startsWith("二中二:") || code.startsWith("三中三:") || code.startsWith("三中二:")) {
            // 口径同专业版：二中二/三中三 要求所选号全在【正码】里；三中二 中两个及以上即中
            String[] parts = code.split(":")[1].split(",");
            List<Integer> reg = new ArrayList<>();
            for (int n : d.regular) reg.add(n);
            int hitCount = 0;
            for (String p : parts) if (reg.contains(Integer.valueOf(p.trim()))) hitCount++;
            boolean ok;
            if (code.startsWith("三中二:")) ok = hitCount >= 2;
            else ok = hitCount == parts.length;
            if (ok) {
                double mult = code.startsWith("二中二:") ? PAY_EM2 : (code.startsWith("三中三:") ? PAY_EM3 : PAY_ZM2);
                return new Line(shortLabel(code), bet, mult, bet * mult);
            }
            return null;
        }
        if (code.matches("\\d{2}")) {
            if (Integer.parseInt(code) == d.special) {
                return new Line(shortLabel(code + "号"), bet, PAY_SPECIAL, bet * PAY_SPECIAL);
            }
            return null;
        }
        return null;
    }

    /** 展示名与专业版一致：平特虎 / 连肖虎龙 / 三中三42,43,48 / 特码22 */
    public static String shortLabel(String c) {
        if (c.startsWith("平特")) return c;
        if (c.startsWith("连肖")) return c;
        if (c.startsWith("二中二:") || c.startsWith("三中二:") || c.startsWith("三中三:")) {
            return c.split(":")[0] + c.split(":")[1].replace(",", ",");
        }
        if (c.matches("\\d{2}号")) return "特码" + c.substring(0, 2);
        return c;
    }

    public static Result win(Order o, Draw d, double pingteMult) {
        Result r = new Result();
        Set<String> seen = new HashSet<>();
        for (String code : o.codes) {
            if (!seen.add(code)) continue;
            Line l = hit(o, code, d, pingteMult);
            if (l != null) { r.total += l.win; r.lines.add(l); }
        }
        return r;
    }
}
