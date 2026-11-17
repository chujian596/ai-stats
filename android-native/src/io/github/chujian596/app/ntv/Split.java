package io.github.chujian596.app.ntv;

import java.util.*;

/** 削峰：按每号自留上限把超出部分飞给上家，算自留、最坏、以及刚好不亏的档位 */
public class Split {

    /** 一行：号 / 原注额 / 自留 / 飞 / 开出该号的净盈亏 */
    public static class Row {
        public int no; public double nb, self, fly, net;
        Row(int n, double a, double b, double c, double d) { no = n; nb = a; self = b; fly = c; net = d; }
    }

    public static List<Row> rows(Board b, double cap) {
        List<Row> out = new ArrayList<>();
        double kept = b.kept(cap);
        for (int n = 1; n <= 49; n++) {
            double nb = b.bets.get(n);
            if (nb <= 0) continue;
            double self = Math.min(nb, cap);
            double fly = nb - self;
            double net = kept - Calc.PAY_SPECIAL * self;
            out.add(new Row(n, nb, self, fly, net));
        }
        out.sort((x, y) -> Double.compare(y.fly, x.fly));
        return out;
    }

    /** 凑整：就近凑到 5 的倍数，最少 5（34→35、31→30、3→5），与专业版 flyShowAmt 同口径 */
    public static double round5(double amt) {
        if (amt <= 0) return 0;
        return Math.max(5, Math.round((amt + 1e-9) / 5) * 5);
    }

    /** 飞单目录一行：几个号同金额合并成「01 02 各35」 */
    public static class FlyGroup {
        public double amt;
        public List<Integer> nos = new ArrayList<>();
        public String text() {
            StringBuilder b = new StringBuilder();
            for (int i = 0; i < nos.size(); i++) {
                if (i > 0) b.append(" ");
                b.append(String.format("%02d", nos.get(i)));
            }
            b.append(" 各").append(Calc.fmt(amt));
            return b.toString();
        }
    }

    /** 按号汇总要飞的钱 → 凑整 → 同金额并成一行；round=true 时按 5 元档凑整 */
    public static List<FlyGroup> flyGroups(Board b, double cap, boolean round) {
        Map<Double, FlyGroup> map = new LinkedHashMap<>();
        for (Row r : rows(b, cap)) {
            if (r.fly < 0.01) continue;
            double show = round ? round5(r.fly) : r.fly;
            FlyGroup g = map.get(show);
            if (g == null) { g = new FlyGroup(); g.amt = show; map.put(show, g); }
            g.nos.add(r.no);
        }
        List<FlyGroup> out = new ArrayList<>(map.values());
        for (FlyGroup g : out) java.util.Collections.sort(g.nos);
        return out;
    }

    /** 目录合计（凑整后） */
    public static double flySum(List<FlyGroup> gs) {
        double t = 0;
        for (FlyGroup g : gs) t += g.amt * g.nos.size();
        return t;
    }

    /** 目录原额合计（不凑整） */
    public static double flyRaw(Board b, double cap) {
        double t = 0;
        for (Row r : rows(b, cap)) if (r.fly > 0.01) t += r.fly;
        return t;
    }

    /** 该 cap 下的最坏盈亏 */
    public static double worst(Board b, double cap) {
        return b.worst(cap);
    }

    /** 二分找「刚好不亏」的最小 cap（越小飞得越多、越安全）；全盘都亏也返回最小值 */
    public static double breakEvenCap(Board b, double lo, double hi) {
        if (worst(b, lo) < 0) return 0;        // 留一点就亏 → 只能全飞
        if (worst(b, hi) >= 0) return hi;
        for (int i = 0; i < 40; i++) {
            double mid = (lo + hi) / 2;
            if (worst(b, mid) >= 0) lo = mid; else hi = mid;
        }
        return Math.round(hi);
    }

    /** 档位扫描：几个整数 cap 各算一次最坏，给一张对照表 */
    public static List<double[]> scan(Board b, int[] caps) {
        List<double[]> out = new ArrayList<>();
        for (int c : caps) {
            double kept = b.kept(c);
            out.add(new double[]{c, kept, b.total - kept, b.worst(c)});
        }
        return out;
    }
}
