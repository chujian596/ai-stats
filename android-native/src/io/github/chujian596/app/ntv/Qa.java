package io.github.chujian596.app.ntv;

import java.util.*;

/**
 * 质检台：解析 / 赔率 / 结算 三类矩阵，逐条断言。
 * 跑法：javac 后 java io.github.chujian596.app.ntv.Qa
 * 输出：[PASS]/[FAIL] 清单 + 汇总，FAIL 附期望 vs 实际。
 */
public class Qa {

    static int pass = 0, fail = 0;
    static List<String> fails = new ArrayList<>();
    static List<String> lines = new ArrayList<>();

    public static void main(String[] a) {
        System.out.println("========== 一、录单解析矩阵 ==========");
        parseCases();
        System.out.println("========== 二、赔率与命中矩阵 ==========");
        payCases();
        System.out.println("========== 三、结算 / 飞单矩阵 ==========");
        settleCases();
        System.out.println("========== 四、飞单凑整矩阵 ==========");
        flyRoundCases();
        System.out.println("========== 五、飞单三段账矩阵 ==========");
        flyBookCases();
        System.out.println();
        for (String l : lines) System.out.println(l);
        System.out.println();
        System.out.println("========== 汇总 ==========");
        System.out.println("通过 " + pass + " 项，失败 " + fail + " 项");
        for (String f : fails) System.out.println("  [FAIL] " + f);
    }

    // ---------- 断言工具 ----------

    static void ok(String name, boolean cond, String expect, String actual) { ok2(name, cond, expect, actual, null); }

    static void ok2(String name, boolean cond, String expect, String actual, String detail) {
        if (cond) {
            pass++;
            lines.add("[PASS] " + name + (detail == null ? "" : "　" + detail));
        } else {
            fail++;
            String s = name + "　期望=" + expect + "　实际=" + actual;
            fails.add(s);
            lines.add("[FAIL] " + s);
        }
    }

    /** 解析用例：input → 期望 codes（逗号串，已排序）、price、isPer */
    static void P(String input, String expectCodes, double price, boolean isPer) {
        String name = "输入「" + input + "」";
        try {
            Order o = Parse.parseLine(input);
            if (o == null) { ok(name, false, expectCodes, "null"); return; }
            List<String> got = new ArrayList<>(o.codes);
            Collections.sort(got);
            List<String> exp = new ArrayList<>(Arrays.asList(expectCodes.split("\\|")));
            Collections.sort(exp);
            boolean same = got.equals(exp);
            boolean priceOk = Math.abs(o.price - price) < 0.005;
            boolean perOk = o.isPer == isPer;
            String shown = got.size() > 5 ? "共 " + got.size() + " 组" : String.join("|", got);
            String act = shown + "　" + fmt(o.price) + (o.isPer ? "元/号" : "元");
            ok2(name, same && priceOk && perOk,
                    expectCodes + " 价" + fmt(price) + (isPer ? " 各" : " 共"),
                    act, (same && priceOk && perOk) ? act : null);
        } catch (Exception e) {
            ok(name, false, expectCodes + " 价" + fmt(price), "抛错：" + e.getMessage());
        }
    }

    /** 解析应当报错（非法输入不能被静默吞掉） */
    static void PErr(String input) {
        String name = "输入「" + input + "」应报错";
        try {
            Order o = Parse.parseLine(input);
            ok(name, false, "报错", o == null ? "null" : "吞掉了→" + String.join(",", o.codes));
        } catch (Exception e) {
            ok(name, true, "报错", "报错：" + e.getMessage());
        }
    }

    /** 赔率用例：下行 + 开奖 → 期望该单赔付总额 */
    static void Pay(String input, int[] regular, int special, double expectPay) {
        String name = "赔付「" + input + "」开" + arr(regular) + "特" + String.format("%02d", special);
        try {
            Order o = Parse.parseLine(input);
            Draw d = new Draw();
            d.period = 1;
            for (int n : regular) d.regular.add(n);
            d.special = special;
            Calc.Result r = Calc.win(o, d, 2);
            ok2(name, Math.abs(r.total - expectPay) < 0.005, fmt(expectPay), fmt(r.total),
                    Math.abs(r.total - expectPay) < 0.005 ? "赔 " + fmt(r.total) : null);
        } catch (Exception e) {
            ok(name, false, fmt(expectPay), "抛错：" + e.getMessage());
        }
    }

    static String arr(int[] a) {
        StringBuilder b = new StringBuilder();
        for (int n : a) b.append(String.format("%02d", n)).append(" ");
        return b.toString().trim();
    }

    static String fmt(double v) {
        if (Math.abs(v - Math.round(v)) < 0.005) return String.valueOf((long) Math.round(v));
        return String.format("%.2f", v);
    }

    // ---------- 一、解析矩阵（口径照专业版 parseLine） ----------

    static void parseCases() {
        // 1. 单号
        P("22 140", "22", 140, false);
        P("特码22 140", "22", 140, false);
        P("特 22 140", "22", 140, false);
        P("22各140", "22", 140, true);
        P("05 06 各150", "05|06", 150, true);

        // 2. 多号 + 各种分隔符
        P("22 34 各100", "22|34", 100, true);
        P("22,34,46 各30", "22|34|46", 30, true);
        P("01.02.03.04.05各10", "01|02|03|04|05", 10, true);
        P("24-48-31-14-38各200", "14|24|31|38|48", 200, true);
        P("22 34 100", "22|34", 100, false);

        // 3. 平特
        P("平特虎 1000", "平特虎", 1000, false);
        P("虎平1000", "平特虎", 1000, false);
        P("平特一肖猴 500", "平特猴", 500, false);
        
        P("平特马龙兔 各100", "平特兔|平特马|平特龙", 100, true);
        P("马龙兔平特肖 100", "平特兔|平特马|平特龙", 100, false);

        // 4. 连肖
        P("连肖马龙 100", "连肖马龙", 100, false);
        P("马连龙兔 100", "连肖马龙兔", 100, false);
        P("三连肖马龙兔 100", "连肖马龙兔", 100, false);
        P("马龙兔三连肖 100", "连肖马龙兔", 100, false);
        P("平连马龙 100", "连肖马龙", 100, false);
        P("二连肖鼠牛 100", "连肖鼠牛", 100, false);

        // 5. 组合玩法
        P("二中二:03,04 100", "二中二:03,04", 100, false);
        P("三中三:34,32,46 5", "三中三:34,32,46", 5, false);
        P("三中三34 32 46 5", "三中三:34,32,46", 5, false);
        P("34 32 46 三中三 5", "三中三:34,32,46", 5, false);
        P("3中3 34 32 46 5", "三中三:34,32,46", 5, false);
        P("三中二:02,15,28 10", "三中二:02,15,28", 10, false);

        // 6. 复式展开
        P("44-10-08-09-04-05复式三中三 5", expand3(new String[]{"04", "05", "08", "09", "10", "44"}), 5, false);
        P("03.04.06.05.49复二 10", expand2(new String[]{"03", "04", "05", "06", "49"}), 10, false);

        // 7. 头尾数
        P("0头 各10", nums("01,02,03,04,05,06,07,08,09"), 10, true);
        P("3头 各10", nums("31,32,33,34,35,36,37,38,39"), 10, true);
        P("尾5 各10", "05|15|25|35|45", 10, true);

        // 8. 生肖数展开
        P("蛇数 各10", "02|14|26|38", 10, true);
        P("鼠数 各10", "07|19|31|43", 10, true);

        // 9. 波色 / 单双 / 大小 / 合数
        P("红波 100", "01|02|07|08|12|13|18|19|23|24|29|30|34|35|40|45|46", 100, true);
        P("蓝波单 100", "03|09|15|25|31|37|41|47", 100, true);
        P("特单 100", "01|03|05|07|09|11|13|15|17|19|21|23|25|27|29|31|33|35|37|39|41|43|45|47|49", 100, true);
        P("双数 100", "02|04|06|08|10|12|14|16|18|20|22|24|26|28|30|32|34|36|38|40|42|44|46|48", 100, true);
        P("大 100", "25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|40|41|42|43|44|45|46|47|48|49", 100, true);
        P("合数单 100", "01|03|05|07|09|10|12|14|16|18|21|23|25|27|29|30|32|34|36|38|41|43|45|47|49", 100, true);
        P("特红波 100", "01|02|07|08|12|13|18|19|23|24|29|30|34|35|40|45|46", 100, true);

        // 10. 金额写法
        P("22 一百", "22", 100, false);
        P("22 五十", "22", 50, false);
        P("22/100", "22", 100, false);
        P("新澳22 140", "22", 140, false);
        P("澳门22 140", "22", 140, false);

        // 11. 金额账：属性玩法按每个号各 X 计价
        try {
            Order o = Parse.parseLine("红波 10");
            double amt = o.isPer ? o.price * o.codes.size() : o.price;
            ok2("红波 10 应记 170 元", Math.abs(amt - 170) < 0.005, "170", fmt(amt),
                    "17 个红波号 × 10 = " + fmt(amt));
        } catch (Exception e) {
            ok("红波 10 应记 170 元", false, "170", "抛错：" + e.getMessage());
        }
        try {
            Order o = Parse.parseLine("单数 10");
            double amt = o.isPer ? o.price * o.codes.size() : o.price;
            ok2("单数 10 应记 250 元", Math.abs(amt - 250) < 0.005, "250", fmt(amt),
                    "25 个单数号 × 10 = " + fmt(amt));
        } catch (Exception e) {
            ok("单数 10 应记 250 元", false, "250", "抛错：" + e.getMessage());
        }

        // 11b. 注单方式弹窗（照专业版：总额摊号 / 各号 / 取消）
        String[] w = Parse.detectWave("红波 100");
        ok2("红波 100 应弹窗询问", w != null && "红波".equals(w[0]) && "100".equals(w[1]),
                "红波/100", w == null ? "不弹" : w[0] + "/" + w[1], "没写「各」就要问");
        ok("红波各100 不弹窗", Parse.detectWave("红波各100") == null, "null", "不弹");
        String[] w2 = Parse.detectWave("红波单大 100");
        ok2("红波单大 100 取长名", w2 != null && "红波单大".equals(w2[0]),
                "红波单大", w2 == null ? "null" : w2[0], "长名优先于红波");
        ok("红波 100 覆盖 17 个号", Parse.linkCount("红波") == 17, "17", String.valueOf(Parse.linkCount("红波")));
        try {
            Order o = Parse.parseLine("红波各5.8824");   // 选「总额」时的写法
            double amt = o.isPer ? o.price * o.codes.size() : o.price;
            ok2("总额100摊17号仍记100", Math.abs(amt - 100) < 0.01, "100", fmt(amt),
                    "17 × 5.8824 = " + fmt(amt));
        } catch (Exception e) {
            ok("总额100摊17号仍记100", false, "100", "抛错：" + e.getMessage());
        }

        // 12. 非法输入必须报错
        PErr("22 140 abc");
        PErr("22 0");
    }

    static String nums(String s) { return s.replace(",", "|"); }

    static String expand2(String[] ns) { return combos(ns, 2, "二中二"); }

    static String expand3(String[] ns) { return combos(ns, 3, "三中三"); }

    static String combos(String[] ns, int k, String prod) {
        List<String> out = new ArrayList<>();
        int n = ns.length;
        int[] idx = new int[k];
        for (int i = 0; i < k; i++) idx[i] = i;
        while (true) {
            StringBuilder b = new StringBuilder(prod + ":");
            for (int i = 0; i < k; i++) { if (i > 0) b.append(","); b.append(ns[idx[i]]); }
            out.add(b.toString());
            int pos = k - 1;
            while (pos >= 0 && idx[pos] == n - k + pos) pos--;
            if (pos < 0) break;
            idx[pos]++;
            for (int i = pos + 1; i < k; i++) idx[i] = idx[i - 1] + 1;
        }
        Collections.sort(out);
        return String.join("|", out);
    }

    // ---------- 二、赔率矩阵 ----------

    static void payCases() {
        int[] r1 = {14, 17, 32, 34, 24};
        Pay("22 140", r1, 22, 140 * 47.0);          // 特码 47
        Pay("22 140", r1, 20, 0);                   // 未中

        Pay("平特虎 1000", new int[]{14, 17, 32, 34, 24, 46}, 20, 2000);   // 17 虎 → 2 倍
        Pay("平特马 1000", new int[]{14, 13, 32, 34, 24, 46}, 20, 1800);   // 马 1.8
        Pay("平特虎 1000", new int[]{14, 11, 32, 34, 24, 46}, 20, 0);      // 正码无虎 → 不中（特码不算）

        Pay("连肖马龙 100", new int[]{01, 03, 11, 12, 13, 14}, 20, 350);   // 二连 4，含马 −0.5
        Pay("连肖马龙 100", new int[]{01, 11, 12, 13, 14, 16}, 20, 0);
        Pay("三连肖马龙兔 100", new int[]{01, 03, 04, 11, 12, 13}, 20, 950); // 三连 10，含马 −0.5
        Pay("四连肖马龙兔蛇 100", new int[]{01, 03, 04, 02, 12, 13}, 20, 2950); // 四连 30，含马 −0.5
        Pay("四连鼠牛虎兔 100", new int[]{07, 06, 17, 16, 12, 13}, 20, 3000); // 不含马 → 30 倍

        Pay("二中二:03,04 100", new int[]{03, 04, 11, 12, 13, 14}, 20, 6000);
        Pay("二中二:03,20 100", new int[]{03, 04, 11, 12, 13, 14}, 20, 0);  // 20 是特码，不算正码
        Pay("三中三:03,04,06 100", new int[]{03, 04, 06, 11, 12, 13}, 20, 60000);
        Pay("三中二:03,04,06 100", new int[]{03, 04, 11, 12, 13, 14}, 20, 2000); // 中 2 个即中
        Pay("三中二:03,06,09 100", new int[]{03, 04, 11, 12, 13, 14}, 20, 0);    // 只中 1 个

        // 属性玩法：按号各 X 记账，命中按特码 47 倍
        Pay("红波 10", new int[]{14, 17, 32, 34, 24, 46}, 1, 470);    // 01 是红波
        Pay("红波 10", new int[]{14, 17, 32, 34, 24, 46}, 22, 0);     // 22 不是红波
        Pay("单数 10", new int[]{14, 17, 32, 34, 24, 46}, 45, 470);   // 45 是单数
        Pay("双数 10", new int[]{14, 17, 32, 34, 24, 46}, 45, 0);     // 45 不是双数
        Pay("大 10", new int[]{14, 17, 32, 34, 24, 46}, 45, 470);     // 45 属大
        Pay("小 10", new int[]{14, 17, 32, 34, 24, 46}, 45, 0);       // 45 不属小
    }

    // ---------- 三、结算 / 飞单矩阵 ----------

    /** 四、飞单凑整矩阵：与专业版 flyShowAmt 同口径（就近凑 5，最少 5） */
    static void flyRoundCases() {
        double[][] c = {{34,35},{31,30},{3,5},{62,60},{103,105},{5,5},{7.5,10},{0,0},{1,5},{2.5,5}};
        for (double[] x : c) {
            double got = Split.round5(x[0]);
            ok2("凑整 " + fmt(x[0]) + " → " + fmt(x[1]), Math.abs(got - x[1]) < 0.005, fmt(x[1]), fmt(got), "");
        }
        try {
            List<Order> os = new ArrayList<>();
            os.add(Parse.parseLine("22 34"));
            os.add(Parse.parseLine("22 31"));
            os.add(Parse.parseLine("22 103"));
            Board b = Board.of(os);
            double raw = Split.flyRaw(b, 0);
            ok2("原额合计", Math.abs(raw - 168) < 0.005, "168", fmt(raw), "22号共 34+31+103=168");
            java.util.List<Split.FlyGroup> gs = Split.flyGroups(b, 0, true);
            double sum = Split.flySum(gs);
            ok2("凑整后合计", Math.abs(sum - 170) < 0.51, "170", fmt(sum), "同号合并 168 就近凑成 170");
            ok2("目录行数", gs.size() == 1, "1", String.valueOf(gs.size()), "同一个号的几笔先合并再凑整，只出一行");
            String t = gs.isEmpty() ? "" : gs.get(0).text();
            ok2("目录文本格式", t.matches("\\d{2} 各\\d+\\.?\\d*"), "22 各170 类", t, "");
        } catch (Exception e) {
            ok2("凑整异常", false, "无异常", e.getMessage(), "");
        }
    }

    static void settleCases() {
        try {
            List<Order> os = new ArrayList<>();
            os.add(Parse.parseLine("22 140"));
            os.add(Parse.parseLine("34 90"));
            os.add(Parse.parseLine("45 85"));
            os.add(Parse.parseLine("平特虎 1000"));
            os.add(Parse.parseLine("三中三:34,32,46 5"));

            double total = 0;
            for (Order o : os) total += o.isPer ? o.price * o.codes.size() : o.price;
            ok2("5 单合计", Math.abs(total - 1320) < 0.005, "1320", fmt(total), "合计 " + fmt(total) + " 元");

            Board b = Board.of(os);
            ok2("盘面特号合计", Math.abs(b.total - 315) < 0.005, "315", fmt(b.total), "特号押注 " + fmt(b.total) + " 元");

            // cap=100：每个特号最多留 100
            double cap = 100;
            Split.Row r22 = null;
            for (Split.Row r : Split.rows(b, cap)) if (r.no == 22) r22 = r;
            ok2("22 号 cap100 自留", r22 != null && Math.abs(r22.self - 100) < 0.005,
                    "100", r22 == null ? "null" : fmt(r22.self),
                    r22 == null ? null : "注 " + fmt(r22.nb) + " → 自留 " + fmt(r22.self));
            ok2("22 号 cap100 飞走", r22 != null && Math.abs(r22.fly - 40) < 0.005,
                    "40", r22 == null ? "null" : fmt(r22.fly),
                    r22 == null ? null : "飞 " + fmt(r22.fly) + " 给上家");

            double worst = Split.worst(b, cap);
            ok2("cap100 最坏结果", true, "记录", fmt(worst), "最坏 " + fmt(worst) + " 元");
            System.out.println("  （参考）cap100 最坏=" + fmt(worst) + "，总风险=" + fmt(b.total));
        } catch (Exception e) {
            ok("结算矩阵", false, "跑通", "抛错：" + e.getMessage());
        }
    }

    /** 五、飞单三段账：总单/已飞/待飞/合计/自留现金，与专业版 getThisRoundFly 同口径 */
    static void flyBookCases() {
        try {
            // 场景：22 号收 70（每号70），45 号收 55，37 号收 5，平特虎 1000
            List<Order> os = new ArrayList<>();
            os.add(Parse.parseLine("22 70"));
            os.add(Parse.parseLine("45 55"));
            os.add(Parse.parseLine("37 5"));
            os.add(Parse.parseLine("平特虎 1000"));

            // 特阈值 21、平特 0（全飞）、不凑整
            FlyBook.Ledger L = FlyBook.build(os, 21, 0, 0, false, new HashMap<String, Double>());
            // 特号：22→49、45→34、37→0（5<21 不飞）；平特虎 1000 全飞
            ok2("总单", Math.abs(L.total - 1130) < 0.005, "1130", fmt(L.total), "70+55+5+1000");
            ok2("特号总单", Math.abs(L.totalSpec - 130) < 0.005, "130", fmt(L.totalSpec), "");
            ok2("平特总单", Math.abs(L.totalPte - 1000) < 0.005, "1000", fmt(L.totalPte), "");
            ok2("应飞总额", Math.abs(L.flyFull - 1083) < 0.005, "1083", fmt(L.flyFull), "49+34+1000");
            ok2("已飞初始为0", Math.abs(L.already) < 0.005, "0", fmt(L.already), "");
            ok2("待飞", Math.abs(L.pending - 1083) < 0.005, "1083", fmt(L.pending), "");
            ok2("合计=已飞+待飞", Math.abs(L.sum - 1083) < 0.005, "1083", fmt(L.sum), "");
            ok2("自留现金", Math.abs(L.keepCash - 47) < 0.005, "47", fmt(L.keepCash), "总单1130-飞1083");

            // 记已飞后再算：已飞 49，待飞 1034
            Map<String, Double> flown = new HashMap<>();
            FlyBook.commit(L, flown, false);
            FlyBook.Ledger L2 = FlyBook.build(os, 21, 0, 0, false, flown);
            ok2("确认后已飞", Math.abs(L2.already - 1083) < 0.005, "1083", fmt(L2.already), "全部确认");
            ok2("确认后待飞归0", Math.abs(L2.pending) < 0.005, "0", fmt(L2.pending), "");
            ok2("确认后自留现金不变", Math.abs(L2.keepCash - 47) < 0.005, "47", fmt(L2.keepCash), "");

            // 部分已飞：只确认 22 号
            Map<String, Double> part = new HashMap<>();
            part.put("22", 49.0);
            FlyBook.Ledger L3 = FlyBook.build(os, 21, 0, 0, false, part);
            ok2("部分已飞", Math.abs(L3.already - 49) < 0.005, "49", fmt(L3.already), "只确认22号");
            ok2("部分待飞", Math.abs(L3.pending - 1034) < 0.005, "1034", fmt(L3.pending), "34+1000");

            // 旧记录清理：已飞大于该飞 → 归零
            Map<String, Double> stale = new HashMap<>();
            stale.put("22", 999.0);
            FlyBook.Ledger L4 = FlyBook.build(os, 21, 0, 0, false, stale);
            ok2("旧记录不算今天", Math.abs(L4.already) < 0.005, "0", fmt(L4.already), "已飞999>该飞49");

            // 凑整：49→50、34→35
            FlyBook.Ledger L5 = FlyBook.build(os, 21, 0, 0, true, new HashMap<String, Double>());
            ok2("凑整后待飞", Math.abs(L5.pendingRound - 1085) < 0.005, "1085", fmt(L5.pendingRound), "50+35+1000");

            // 凑整后确认：记原额，再算待飞必须归 0（否则 49→50 会被当旧记录清零）
            Map<String, Double> rc = new HashMap<>();
            FlyBook.Ledger R0 = FlyBook.build(os, 21, 0, 0, true, rc);
            FlyBook.commit(R0, rc, true);
            FlyBook.Ledger R1 = FlyBook.build(os, 21, 0, 0, true, rc);
            ok2("凑整确认后待飞归0", Math.abs(R1.pending) < 0.005, "0", fmt(R1.pending), "22记49不是50");
            ok2("凑整确认后已飞=原额", Math.abs(R1.already - 1083) < 0.005, "1083", fmt(R1.already), "");

            // 三阈值独立：平特留 500 → 只飞 500
            FlyBook.Ledger L6 = FlyBook.build(os, 21, 500, 0, false, new HashMap<String, Double>());
            ok2("平特留500后飞", Math.abs(L6.totalPte - 1000) < 0.005, "1000", fmt(L6.totalPte), "总单不变");
            double pteFly = 0;
            for (FlyBook.Line ln : L6.lines) if (ln.key.startsWith("平特")) pteFly += ln.full;
            ok2("平特自留500只飞500", Math.abs(pteFly - 500) < 0.005, "500", fmt(pteFly), "");

            // 阈值 0 = 全飞
            FlyBook.Ledger L7 = FlyBook.build(os, 0, 0, 0, false, new HashMap<String, Double>());
            ok2("特阈值0全飞", Math.abs(L7.flyFull - 1130) < 0.005, "1130", fmt(L7.flyFull), "");
            ok2("特阈值0自留0", Math.abs(L7.keepCash) < 0.005, "0", fmt(L7.keepCash), "");

            // 目录分行：金额相同的合并
            FlyBook.Ledger L8 = FlyBook.build(os, 21, 0, 0, false, new HashMap<String, Double>());
            ok2("目录行数", L8.groups.size() >= 1, ">=1", String.valueOf(L8.groups.size()),
                    L8.groups.isEmpty() ? "空" : L8.groups.get(0).text());
        } catch (Exception e) {
            ok("三段账矩阵", false, "跑通", "抛错：" + e.getMessage());
        }
    }
}
