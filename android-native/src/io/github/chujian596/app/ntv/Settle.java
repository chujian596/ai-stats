package io.github.chujian596.app.ntv;

import java.util.*;

/** 一期飞单结算：飞出去多少钱、上家赔回多少、净差 */
public class Settle {

    public static class Result {
        public double flyOut = 0;    // 飞给上家的本金
        public double flyBack = 0;   // 上家按命中赔回的
        public double delta = 0;     // flyOut - flyBack，正=你赚
        public List<String> hits = new ArrayList<>();
    }

    /**
     * 口径与专业版一致：
     * - 特号按每号自留上限 cap 飞，超出的部分记 flyOut；开出该号时按 47 倍赔回
     * - 平特/连肖/二三 默认全飞（阈值 0），命中时整笔赔回
     */
    public static Result of(Board b, double cap, List<Order> orders, Draw d, double pingteMult) {
        Result r = new Result();

        // 特号：飞出去的钱
        r.flyOut += b.flown(cap);

        // 平特/连肖/二三：全飞
        for (Order o : orders) {
            for (String c : o.codes) {
                if (!c.matches("\\d{2}")) r.flyOut += Board.betOf(o);
            }
        }

        // 特号命中赔回
        Map<Integer, Double> fly = new HashMap<>();
        for (Map.Entry<Integer, Double> e : b.bets.entrySet()) {
            fly.put(e.getKey(), e.getValue() - Math.min(e.getValue(), cap));
        }
        if (d.special >= 1 && d.special <= 49) {
            double f = fly.getOrDefault(d.special, 0.0);
            if (f > 0) {
                double back = f * Calc.PAY_SPECIAL;
                r.flyBack += back;
                r.hits.add(Calc.shortLabel(String.format("%02d", d.special) + "号")
                        + "　" + Calc.fmt(f) + " ×47 = " + Calc.fmt(back));
            }
        }

        // 平特/连肖/二三 命中赔回
        for (Order o : orders) {
            for (String c : o.codes) {
                if (c.matches("\\d{2}")) continue;
                Calc.Line l = Calc.hit(o, c, d, pingteMult);
                if (l != null) {
                    r.flyBack += l.win;
                    r.hits.add(l.text());
                }
            }
        }

        r.delta = r.flyOut - r.flyBack;
        return r;
    }
}
