package io.github.chujian596.app.ntv;

import java.util.*;

/** 号码盘面：每个特号收了多少、按阈值自留多少、开出该号时整本账的特号部分盈亏 */
public class Board {

    public Map<Integer, Double> bets = new LinkedHashMap<>();  // 1..49
    public double total = 0;      // 特号注额合计
    public double other = 0;      // 平特/连肖/二三 的注额合计（不进号码表）

    /** 一笔订单里每个玩法实际分摊到的注额 */
    public static double betOf(Order o) {
        return o.isPer ? o.price : o.price / Math.max(1, o.codes.size());
    }

    public static Board of(List<Order> orders) {
        Board b = new Board();
        for (int n = 1; n <= 49; n++) b.bets.put(n, 0.0);
        for (Order o : orders) {
            double bet = betOf(o);
            for (String c : o.codes) {
                if (c.matches("\\d{2}")) {
                    int n = Integer.parseInt(c);
                    if (n >= 1 && n <= 49) {
                        b.bets.put(n, b.bets.get(n) + bet);
                        b.total += bet;
                    }
                } else {
                    b.other += bet;
                }
            }
        }
        return b;
    }

    /** 按阈值 cap 自留，返回自留总额 */
    public double kept(double cap) {
        double k = 0;
        for (double v : bets.values()) k += Math.min(v, cap);
        return k;
    }

    /** 飞出去多少 */
    public double flown(double cap) {
        return total - kept(cap);
    }

    /** 开出 n 号时，特号这块的净盈亏（正=赚） */
    public double netIf(int n, double cap) {
        return kept(cap) - Calc.PAY_SPECIAL * Math.min(bets.get(n), cap);
    }

    /** 最坏情况：开出注额最重的那个号 */
    public double worst(double cap) {
        double k = kept(cap);
        double maxSelf = 0;
        for (double v : bets.values()) maxSelf = Math.max(maxSelf, Math.min(v, cap));
        return k - Calc.PAY_SPECIAL * maxSelf;
    }

    /** 排行榜：按注额从大到小，只列有注的 */
    public List<int[]> rank() {
        List<int[]> out = new ArrayList<>();
        for (Map.Entry<Integer, Double> e : bets.entrySet()) {
            if (e.getValue() > 0) out.add(new int[]{e.getKey(), (int) Math.round(e.getValue())});
        }
        out.sort((a, b) -> b[1] - a[1]);
        return out;
    }
}
