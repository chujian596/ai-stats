package io.github.chujian596.app.ntv;

import java.util.*;

/** 号码盘面：每个特号收了多少、按阈值自留多少、开出该号时整本账的特号部分盈亏 */
public class Board {

    public Map<Integer, Double> bets = new LinkedHashMap<>();  // 1..49
    public double total = 0;      // 特号注额合计
    public double other = 0;      // 平特/连肖/二三 的注额合计（不进号码表）

    /** 一笔订单里某个玩法的注额（各号金额可能不同，按码取） */
    public static double betOf(Order o, String code) {
        return o.amtOf(code);
    }

    /** 平均每码注额（只用于粗略汇总） */
    public static double betOf(Order o) {
        return o.amount() / Math.max(1, o.codes.size());
    }

    public static Board of(List<Order> orders) {
        Board b = new Board();
        for (int n = 1; n <= 49; n++) b.bets.put(n, 0.0);
        for (Order o : orders) {
            for (String c : o.codes) {
                double bet = betOf(o, c);
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
    /** 专业版排行榜：49 个号全列（没买的也在，金额 0），按金额降序、同额按号码升序 */
    public List<int[]> rank() {
        List<int[]> out = new ArrayList<>();
        for (int n = 1; n <= 49; n++) {
            double v = bets.containsKey(n) ? bets.get(n) : 0;
            out.add(new int[]{n, (int) Math.round(v)});
        }
        out.sort((a, b) -> a[1] != b[1] ? b[1] - a[1] : a[0] - b[0]);
        return out;
    }
}
