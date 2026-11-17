package io.github.chujian596.app.ntv;

import java.util.*;

/** 补号模拟：给注额最少的几个号补钱，看能把最坏情况拉回来多少 */
public class SimAdd {

    public static class Result {
        public double added;      // 这次补进去多少钱
        public double worst;      // 补完后的最坏盈亏
        public List<int[]> picks = new ArrayList<>();   // {号, 补前, 补后}
    }

    /**
     * 把注额最少的 nAdd 个号补到 amtEach。
     * 已经是 amtEach 或更高的号不动，所以实际补的钱可能少于 nAdd*amtEach。
     */
    public static Result run(Board b, double cap, int nAdd, double amtEach) {
        Result r = new Result();
        List<Integer> order = new ArrayList<>();
        for (int n = 1; n <= 49; n++) order.add(n);
        // 按当前注额从小到大排；同额时小号优先，避免每次结果跳
        order.sort((x, y) -> {
            double a = b.bets.get(x), c = b.bets.get(y);
            if (a != c) return a < c ? -1 : 1;
            return x - y;
        });

        Map<Integer, Double> bets2 = new HashMap<>(b.bets);
        int picked = 0;
        for (int n : order) {
            if (picked >= nAdd) break;
            double before = bets2.get(n);
            if (before >= amtEach) continue;   // 已经够了，跳过
            double after = amtEach;
            bets2.put(n, after);
            r.added += after - before;
            r.picks.add(new int[]{n, (int) Math.round(before), (int) Math.round(after)});
            picked++;
        }

        // 补完重算最坏
        double kept = 0, maxSelf = 0;
        for (double v : bets2.values()) {
            double s = Math.min(v, cap);
            kept += s;
            maxSelf = Math.max(maxSelf, s);
        }
        r.worst = kept - Calc.PAY_SPECIAL * maxSelf;
        return r;
    }

    /** 当前注额最少的 n 个号，用于提示「补这些最划算」 */
    public static List<int[]> lowest(Board b, double cap, int n) {
        List<int[]> out = new ArrayList<>();
        List<Integer> order = new ArrayList<>();
        for (int no = 1; no <= 49; no++) order.add(no);
        order.sort((x, y) -> {
            double a = Math.min(b.bets.get(x), cap), c = Math.min(b.bets.get(y), cap);
            if (a != c) return a < c ? -1 : 1;
            return x - y;
        });
        for (int i = 0; i < Math.min(n, order.size()); i++) {
            int no = order.get(i);
            out.add(new int[]{no, (int) Math.round(Math.min(b.bets.get(no), cap))});
        }
        return out;
    }

    /** 要收的号清单：按目标最坏反推每个号该收到多少 */
    public static List<int[]> needList(Board b, double cap, double targetWorst, double amtEach) {
        List<int[]> out = new ArrayList<>();
        Map<Integer, Double> bets2 = new HashMap<>(b.bets);
        // 反复补最少的号，直到最坏达标或用完 49 个号
        for (int guard = 0; guard < 49; guard++) {
            double kept = 0, maxSelf = 0;
            for (double v : bets2.values()) {
                double s = Math.min(v, cap);
                kept += s;
                maxSelf = Math.max(maxSelf, s);
            }
            double worst = kept - Calc.PAY_SPECIAL * maxSelf;
            if (worst >= targetWorst) break;
            int best = -1;
            double bestVal = Double.MAX_VALUE;
            for (int n = 1; n <= 49; n++) {
                double v = bets2.get(n);
                if (v >= amtEach) continue;
                if (v < bestVal) { bestVal = v; best = n; }
            }
            if (best < 0) break;
            double before = bets2.get(best);
            bets2.put(best, Math.min(amtEach, Math.max(before, amtEach)));
            out.add(new int[]{best, (int) Math.round(before), (int) Math.round(amtEach)});
        }
        return out;
    }
}
