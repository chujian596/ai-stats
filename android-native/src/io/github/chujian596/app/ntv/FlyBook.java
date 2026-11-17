package io.github.chujian596.app.ntv;

import java.util.*;

/**
 * 飞单三段账：总单 / 已飞 / 待飞 —— 与专业版 getThisRoundFly + realFlyAmount 同口径。
 *
 * 规则（照抄专业版）：
 *  - 特号按「每号自留 cap 特」算该飞额，超出部分为 full；
 *  - 平特按「每肖自留 cap 平」，0 表示全飞；
 *  - 连肖按「自留 cap 连」，0 表示全飞；
 *  - 二中二/三中三/三中二 合并成一笔，全飞；
 *  - 已飞按 key 记累计，本轮应飞 = full - done（done 大于 full+0.5 视为旧记录，归零重算）；
 *  - 凑整只在「本轮应飞」上做（就近 5 元档），已飞是历史事实不改。
 */
public class FlyBook {

    /** 飞单目录一行：同金额的玩法合并成「01 02 各35」 */
    public static class Group {
        public double amt;
        public List<String> keys = new ArrayList<>();
        public String text() {
            StringBuilder b = new StringBuilder();
            for (int i = 0; i < keys.size(); i++) {
                if (i > 0) b.append(" ");
                b.append(keys.get(i));
            }
            b.append(" 各").append(Calc.fmt(amt));
            return b.toString();
        }
    }

    /** 飞单簿的一行：key / 该飞总额 / 已飞 / 本轮应飞 */
    public static class Line {
        public String key;
        public double full, done, round;
        public boolean auto;   // 即飞类（连肖/二三中），不参与分批
        Line(String k, double f, double d, double r, boolean a) { key = k; full = f; done = d; round = r; auto = a; }
        public double pending() { return Math.max(0, full - done); }
    }

    /** 三段账结果 */
    public static class Ledger {
        public double total;       // 总单（特号 + 平特 + 连肖 + 二三）
        public double totalSpec;   // 特号总单
        public double totalPte;    // 平特总单
        public double totalLx;     // 连肖总单
        public double totalEm;     // 二三中总单
        public double flyFull;     // 应飞总额（未凑整）
        public double already;     // 已飞累计
        public double pending;     // 待飞（未凑整）
        public double pendingRound; // 待飞（凑整后，本轮真正要飞的）
        public double sum;         // 合计 = 已飞 + 待飞(凑整后)
        public double keepCash;    // 自留现金 = 总单 - 合计
        public List<Line> lines = new ArrayList<>();
        public List<Group> groups = new ArrayList<>();
    }

    /**
     * @param orders   当日订单
     * @param capSpec  特号每号自留上限
     * @param capPte   平特每肖自留上限（0 = 全飞）
     * @param capLx    连肖自留上限（0 = 全飞）
     * @param roundOn  是否 5 元档凑整
     * @param flown    已飞登记表 key -> 累计飞额
     */
    public static Ledger build(List<Order> orders, double capSpec, double capPte, double capLx,
                               boolean roundOn, Map<String, Double> flown) {
        return build(orders, capSpec, capPte, capLx, roundOn, flown, false);
    }

    /**
     * @param autoDone  即飞开关：连肖/二中二/三中三 整块直接算已飞（专业版「即飞产品自动复制」）
     */
    public static Ledger build(List<Order> orders, double capSpec, double capPte, double capLx,
                               boolean roundOn, Map<String, Double> flown, boolean autoDone) {
        Ledger L = new Ledger();
        if (flown == null) flown = new HashMap<>();

        // ---------- 特号：按号汇总 ----------
        Map<Integer, Double> bet = new TreeMap<>();
        for (int i = 1; i <= 49; i++) bet.put(i, 0.0);
        for (Order o : orders) {
            for (String c : o.codes) {
                if (c.matches("\\d{2}")) {
                    int n = Integer.parseInt(c);
                    if (n >= 1 && n <= 49) bet.put(n, bet.get(n) + Board.betOf(o, c));
                }
            }
        }
        for (Map.Entry<Integer, Double> e : bet.entrySet()) {
            double v = e.getValue();
            if (v <= 0) continue;
            L.totalSpec += v;
            double full = Math.max(0, v - capSpec);
            if (full < 0.01) continue;
            String k = String.format("%02d", e.getKey());
            double done = flown.containsKey(k) ? flown.get(k) : 0;
            if (done > full + 0.5) done = 0;   // 旧记录不算今天
            L.lines.add(new Line(k, full, done, Math.max(0, full - done), false));
        }

        // ---------- 平特：按肖汇总 ----------
        Map<String, Double> pte = new LinkedHashMap<>();
        for (Order o : orders) {
            for (String c : o.codes) {
                if (c.startsWith("平特")) pte.put(c, (pte.get(c) == null ? 0 : pte.get(c)) + Board.betOf(o, c));
            }
        }
        for (Map.Entry<String, Double> e : pte.entrySet()) {
            L.totalPte += e.getValue();
            double full = capPte > 0 ? Math.max(0, e.getValue() - capPte) : e.getValue();
            if (full < 0.01) continue;
            double done = flown.containsKey(e.getKey()) ? flown.get(e.getKey()) : 0;
            if (done > full + 0.5) done = 0;
            L.lines.add(new Line(e.getKey(), full, done, Math.max(0, full - done), false));
        }

        // ---------- 连肖：整块算 ----------
        double lx = 0;
        for (Order o : orders) {
            for (String c : o.codes) if (c.startsWith("连肖")) lx += Board.betOf(o, c);
        }
        if (lx > 0.005) {
            L.totalLx = lx;
            double full = capLx > 0 ? Math.max(0, lx - capLx) : lx;
            if (full > 0.01) {
                double done = flown.containsKey("连肖") ? flown.get("连肖") : 0;
                if (done > full + 0.5) done = 0;
                if (autoDone) done = full;   // 即飞：整块默认已飞
                L.lines.add(new Line("连肖", full, done, Math.max(0, full - done), autoDone));
            }
        }

        // ---------- 二中二 / 三中二 / 三中三：合并一笔，全飞 ----------
        double em = 0;
        for (Order o : orders) {
            for (String c : o.codes) {
                if (c.startsWith("二中二") || c.startsWith("三中二") || c.startsWith("三中三")) em += Board.betOf(o, c);
            }
        }
        if (em > 0.005) {
            L.totalEm = em;
            double done = flown.containsKey("_em_total") ? flown.get("_em_total") : 0;
            if (done > em + 0.5) done = 0;
            if (autoDone) done = em;     // 即飞：整块默认已飞
            L.lines.add(new Line("二中二/三中三合计", em, done, Math.max(0, em - done), autoDone));
        }

        // ---------- 汇总 ----------
        L.total = L.totalSpec + L.totalPte + L.totalLx + L.totalEm;
        for (Line ln : L.lines) {
            L.flyFull += ln.full;
            L.already += ln.done;
            L.pending += ln.round;
            double show = roundOn ? Split.round5(ln.round) : ln.round;
            if (ln.round > 0.005) L.pendingRound += show;
        }
        L.sum = L.already + L.pendingRound;
        L.keepCash = L.total - L.sum;

        // ---------- 目录：按凑整后金额分桶 ----------
        if (roundOn) {
            Map<Double, Group> m = new LinkedHashMap<>();
            for (Line ln : L.lines) {
                if (ln.round < 0.01) continue;
                double show = Split.round5(ln.round);
                Group g = m.get(show);
                if (g == null) {
                    g = new Group();
                    g.amt = show;
                    m.put(show, g);
                }
                g.keys.add(ln.key);
            }
            for (Group g : m.values()) L.groups.add(g);
        } else {
            Map<Double, Group> m = new LinkedHashMap<>();
            for (Line ln : L.lines) {
                if (ln.round < 0.01) continue;
                Group g = m.get(ln.round);
                if (g == null) { g = new Group(); g.amt = ln.round; m.put(ln.round, g); }
                g.keys.add(ln.key);
            }
            for (Group g : m.values()) L.groups.add(g);
        }
        return L;
    }

    /**
     * 点「确认飞单」时把本轮应飞累加进已飞登记表。
     * 记的是**未凑整的原额**（与专业版 flownPerPos 一致）：
     * 凑整只是显示口径，如果记凑整后的数（49→50），下次算会把 50 当成「比该飞 49 还多的旧记录」清零。
     */
    public static void commit(Ledger L, Map<String, Double> flown, boolean roundOn) {
        for (Line ln : L.lines) {
            if (ln.round < 0.01) continue;
            double old = flown.containsKey(ln.key) ? flown.get(ln.key) : 0;
            flown.put(ln.key, old + ln.round);
        }
    }
}
