package io.github.chujian596.app.ntv;

import java.util.*;

/** 对账文本生成：不依赖 Android，可单独测试，保证数字与专业版口径一致 */
public class Text {

    static String signed(double v) {
        return (v >= 0 ? "+" : "-") + Calc.fmt(Math.abs(v));
    }

    /** 订单玩法名：特22 / 平特虎 / 三中三34,32,46（与页面、专业版一致） */
    static String labels(Order o) {
        StringBuilder b = new StringBuilder();
        for (String c : o.codes) {
            if (b.length() > 0) b.append(" ");
            if (c.matches("\\d{1,2}")) b.append("特").append(c.length() == 1 ? "0" + c : c);
            else b.append(c.replace(":", ""));
        }
        return b.toString();
    }

    static String kindOf(Order o) {
        if (o.codes.isEmpty()) return "其他";
        String c = o.codes.get(0);
        if (c.matches("\\d{2}")) return "特";
        if (c.startsWith("平特")) return "平";
        if (c.startsWith("连肖")) return "平";
        if (c.startsWith("二中二") || c.startsWith("三中二") || c.startsWith("三中三")) return "二/三";
        return "其他";
    }

    static String line(Draw d) {
        StringBuilder b = new StringBuilder();
        for (int n : d.regular) b.append(String.format("%02d ", n));
        b.append("+ ").append(String.format("%02d", d.special));
        return b.toString().trim();
    }

    /** 客户单：抬头含开奖，下单 / 命中 / 汇总三段 */
    public static String cust(String customer, List<Order> orders, Draw d, double pingteMult) {
        StringBuilder b = new StringBuilder();
        b.append(customer).append("\n");
        if (d.regular.size() == 6) {
            b.append("【澳 ").append(d.period).append(" 期　").append(line(d)).append("】\n");
        }
        b.append("下单：\n");
        double total = 0;
        for (Order o : orders) {
            b.append("  ").append(labels(o)).append(" ").append(Calc.fmt(o.amount())).append("\n");
            total += o.amount();
        }
        b.append("  合计 ").append(Calc.fmt(total)).append("\n");

        if (d.regular.size() == 6) {
            b.append("命中：\n");
            double win = 0;
            for (Order o : orders) {
                Calc.Result r = Calc.win(o, d, pingteMult);
                for (Calc.Line l : r.lines) b.append("  ").append(l.text()).append("\n");
                win += r.total;
            }
            b.append("  合计 ").append(Calc.fmt(win)).append("\n");
            b.append("汇总：\n");
            b.append("  投入 ").append(Calc.fmt(total))
                    .append(" ｜ 命中 ").append(Calc.fmt(win))
                    .append(" ｜ 结余 ").append(signed(win - total)).append("\n");
        }
        return b.toString().trim();
    }

    /** 上家单：只报总数（特 / 平 / 二·三 三类），明细只列命中的 */
    public static String up(List<Order> orders, Draw d, double pingteMult) {
        StringBuilder b = new StringBuilder();
        double total = 0, sp = 0, pt = 0, em = 0;
        for (Order o : orders) {
            for (int i = 0; i < o.codes.size(); i++) {
                String c = o.codes.get(i);
                double amt = o.amtOf(c);
                total += amt;
                if (c.startsWith("平特")) pt += amt;
                else if (c.startsWith("二中二:") || c.startsWith("三中三:") || c.startsWith("三中二:")) em += amt;
                else sp += amt;
            }
        }
        b.append("飞单对账");
        if (d.period > 0) b.append("  ").append(d.period).append(" 期");
        b.append("\n");
        b.append("合计 ").append(Calc.fmt(total)).append(" 元（特 ").append(Calc.fmt(sp))
          .append(" + 平 ").append(Calc.fmt(pt)).append(" + 二/三 ").append(Calc.fmt(em)).append("）");

        if (d.regular.size() == 6) {
            b.append("\n\n明细:");
            double win = 0;
            boolean any = false;
            for (Order o : orders) {
                Calc.Result r = Calc.win(o, d, pingteMult);
                for (Calc.Line l : r.lines) {
                    if (Math.abs(l.win) > 0.001) { b.append("\n  ").append(l.text()); any = true; }
                }
                win += r.total;
            }
            if (!any) b.append("\n  本期没有命中项");
            b.append("\n合计:").append(signed(win));
            b.append("\n\n总账单 ").append(Calc.fmt(total)).append(" - ").append(Calc.fmt(win))
              .append(" = ").append(signed(total - win));
            b.append("\n结算 ").append(signed(win - total));
        } else {
            b.append("\n\n未开奖，结算待定");
        }
        return b.toString().trim();
    }
}
