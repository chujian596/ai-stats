package io.github.chujian596.app.ntv;

import java.util.*;

/** 纯 Java 自测，不需要 Android 运行时 */
public class Test {

    static int pass = 0, fail = 0;

    static void eq(String name, Object got, Object want) {
        if (String.valueOf(got).equals(String.valueOf(want))) { pass++; }
        else { fail++; System.out.println("FAIL " + name + "  got=" + got + "  want=" + want); }
    }

    public static void main(String[] a) {
        try { run(); } catch (Exception e) { e.printStackTrace(); fail++; }
        System.out.println("\n通过 " + pass + " 项，失败 " + fail + " 项");
        if (fail > 0) System.exit(1);
    }

    static void run() throws Exception {
        // ---------- 解析 ----------
        Order o1 = Parse.parseLine("特码22 120");
        eq("特码22", o1.codes, "[22]");
        eq("特码22价", o1.price, "120.0");

        Order o2 = Parse.parseLine("04 25");
        eq("裸号04", o2.codes, "[04]");

        Order o3 = Parse.parseLine("平特虎 1000");
        eq("平特虎", o3.codes, "[平特虎]");

        Order o4 = Parse.parseLine("平虎 500");
        eq("平虎简称", o4.codes, "[平特虎]");

        Order o5 = Parse.parseLine("虎平1000");
        eq("虎平", o5.codes, "[平特虎]");

        Order o6 = Parse.parseLine("三中三:34,32,46 5");
        eq("三中三冒号", o6.codes, "[三中三:34,32,46]");

        Order o7 = Parse.parseLine("三中三 34 32 46 5");
        eq("三中三空格", o7.codes, "[三中三:34,32,46]");

        Order o8 = Parse.parseLine("22 04 15 各50");
        eq("各数三码", String.join(",", o8.codes), "22,04,15");
        eq("各数标记", o8.isPer + " 总额=" + o8.amount(), "true 总额=150.0");

        Order o9 = Parse.parseLine("连肖马龙 10");
        eq("连肖", o9.codes, "[连肖马龙]");

        // ---------- 赔付 ----------
        Draw d = new Draw(320, Arrays.asList(14, 17, 32, 34, 24, 46), 20);

        Calc.Result r = Calc.win(o3, d, 2);       // 平特虎 500
        eq("平特虎命中", r.total, "2000.0");   // 1000 ×2

        Calc.Result r2 = Calc.win(o6, d, 2);      // 三中三 5
        eq("三中三命中", r2.total, "3000.0");

        Order o10 = Parse.parseLine("20号 35");
        Calc.Result r3 = Calc.win(o10, d, 2);
        eq("特码20命中", r3.total, "1645.0");

        Order o11 = Parse.parseLine("22号 100");
        Calc.Result r4 = Calc.win(o11, d, 2);
        eq("特码22不中", r4.total, "0.0");

        // 叶的三笔合计应为 4000（平特虎 1000 + 三中三 3000）
        Order ye1 = Parse.parseLine("平特虎 500");
        Order ye2 = Parse.parseLine("三中三:34,32,46 5");
        Order ye3 = Parse.parseLine("特码22 120");   // 22 不中
        double sum = Calc.win(ye1, d, 2).total + Calc.win(ye2, d, 2).total + Calc.win(ye3, d, 2).total;
        eq("叶三笔合计", sum, "4000.0");   // 平特虎1000 + 三中三3000，特码22不中

        // 连肖：龙鸡命中（龙 32、鸡 34 都在），二连 4 倍
        Order o12 = Parse.parseLine("连肖鸡猪 10");   // 鸡34/46、猪32/20 都在
        Calc.Result r5 = Calc.win(o12, d, 2);
        eq("连肖鸡猪命中", r5.total, "40.0");

        // 连肖含马：马没中，应为 0
        Order o13 = Parse.parseLine("连肖马鸡 10");
        eq("连肖马鸡不中", Calc.win(o13, d, 2).total, "0.0");

        // 平特马 1.8
        Order o14 = Parse.parseLine("平特马 100");
        Draw d2 = new Draw(321, Arrays.asList(1, 2, 3, 4, 5, 6), 7);
        eq("平特马1.8", Calc.win(o14, d2, 2).total, "180.0");

        // 简称
        eq("简称平特", Calc.shortLabel("平特虎"), "平特虎");
        eq("简称连肖", Calc.shortLabel("连肖马龙"), "连肖马龙");
        eq("简称组合", Calc.shortLabel("三中三:34,32,46"), "三中三34,32,46");
        eq("简称特码", Calc.shortLabel("22号"), "特码22");

        // ---------- 对账文本 ----------
        List<Order> ye = new ArrayList<>();
        ye.add(Parse.parseLine("特码22 120"));
        ye.add(Parse.parseLine("平特虎 500"));
        ye.add(Parse.parseLine("三中三:34,32,46 5"));
        ye.add(Parse.parseLine("三中三:42,43,48 5"));
        ye.add(Parse.parseLine("三中三:25,27,29 5"));
        ye.add(Parse.parseLine("三中三:17,19,21 5"));
        String cs = Text.cust("叶", ye, d, 2);
        System.out.println("---- 客户单 ----\n" + cs);
        eq("客户单含投入", cs.contains("投入 640"), "true");
        eq("客户单含命中4000", cs.contains("命中 4000"), "true");
        eq("客户单含结余", cs.contains("结余 +3360"), "true");

        String us = Text.up(ye, d, 2);
        System.out.println("---- 上家单 ----\n" + us);
        eq("上家单合计640", us.contains("合计 640 元"), "true");
        eq("上家单结算", us.contains("结算 +3360"), "true");
        eq("上家单无逐号明细", us.contains("特码22"), "false");

        // ---------- 盘面 ----------
        List<Order> bdOrders = new ArrayList<>();
        bdOrders.add(Parse.parseLine("22 140"));
        bdOrders.add(Parse.parseLine("34 90"));
        bdOrders.add(Parse.parseLine("45 85"));
        bdOrders.add(Parse.parseLine("22 04 15 各50"));
        Board bd = Board.of(bdOrders);
        eq("22号注额", Calc.fmt(bd.bets.get(22)), "190");       // 140 + 各50
        eq("04号注额", Calc.fmt(bd.bets.get(4)), "50");
        eq("特号合计", Calc.fmt(bd.total), "465");               // 140+90+85+150
        eq("自留cap100", Calc.fmt(bd.kept(100)), "375");         // 22号100 + 90 + 85 + 04/15 各50
        eq("飞", Calc.fmt(bd.flown(100)), "90");
        eq("排行第一", bd.rank().get(0)[0], "22");

        // ---------- 削峰 ----------
        double w100 = Split.worst(bd, 100);
        eq("最坏cap100", Calc.fmt(w100), "-4325");   // 自留375 - 47*100
        double be = Split.breakEvenCap(bd, 1, 465);
        System.out.println("刚好不亏的 cap = " + be + "（自留 " + Calc.fmt(bd.kept(be)) + "，最坏 " + Calc.fmt(bd.worst(be)) + "）");
        eq("留一点就亏时返回0", be, "0.0");
        eq("飞单行数", Split.rows(bd, 100).stream().filter(x -> x.fly > 0).count(), "1");

        // ---------- 飞单结算 ----------
        List<Order> st = new ArrayList<>();
        st.add(Parse.parseLine("特码22 120"));
        st.add(Parse.parseLine("平特虎 500"));
        st.add(Parse.parseLine("三中三:34,32,46 5"));
        st.add(Parse.parseLine("三中三:42,43,48 5"));
        st.add(Parse.parseLine("三中三:25,27,29 5"));
        st.add(Parse.parseLine("三中三:17,19,21 5"));
        Board sb = Board.of(st);
        Settle.Result sr = Settle.of(sb, 0, st, d, 2);   // cap=0 全飞
        eq("飞走", Calc.fmt(sr.flyOut), "640");
        eq("赔回", Calc.fmt(sr.flyBack), "4000");
        eq("净差", Calc.fmt(sr.delta), "-3360");
        eq("上家赔", Calc.fmt(-sr.delta), "3360");

        // 本周标识
        java.util.Calendar cal = java.util.Calendar.getInstance();
        cal.set(2026, java.util.Calendar.NOVEMBER, 17);   // 周二
        eq("本周一", UpCum.weekKey(cal.getTime()), "2026-11-16");
        cal.set(2026, java.util.Calendar.NOVEMBER, 22);   // 周日
        eq("周日仍算本周", UpCum.weekKey(cal.getTime()), "2026-11-16");
        cal.set(2026, java.util.Calendar.NOVEMBER, 23);   // 下周一
        eq("下周一换周", UpCum.weekKey(cal.getTime()), "2026-11-23");
    }
}
