package io.github.chujian596.app.ntv;

import java.util.*;
import java.text.SimpleDateFormat;

/** 上家盈亏累计：本周（周一起）、今日、历史总账。口径与专业版 v58.173 一致 */
public class UpCum {

    /** 一期结算后的账：飞走多少、命中多少，差额正=你赚 */
    public static double settle(double flyOut, double hitBack) {
        return flyOut - hitBack;
    }

    /** 本周标识：本周一的日期 */
    public static String weekKey(Date now) {
        Calendar c = Calendar.getInstance();
        c.setTime(now);
        int day = c.get(Calendar.DAY_OF_WEEK);   // 周日=1
        int back = (day == Calendar.SUNDAY) ? 6 : day - Calendar.MONDAY;
        c.add(Calendar.DAY_OF_MONTH, -back);
        return new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(c.getTime());
    }

    public static String dayKey(Date now) {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA).format(now);
    }

    /** 从总数里切出某个区间：区间值 = 当前总数 - 区间起点 */
    public static double since(double now, double base) {
        return now - base;
    }
}
