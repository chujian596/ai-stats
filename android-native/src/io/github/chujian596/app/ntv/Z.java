package io.github.chujian596.app.ntv;

import java.util.*;

/** 生肖与号码互查：全部基于一张表，避免各处硬编码 */
public class Z {
    public static final String[] ZODIAC = {"马","蛇","龙","兔","虎","牛","鼠","猪","狗","鸡","猴","羊"};

    // 号码 -> 生肖
    private static final String[] N2Z = new String[50];
    // 生肖 -> 号码列表
    private static final Map<String, List<Integer>> Z2N = new LinkedHashMap<>();

    static {
        Object[][] t = {
            {"马", new int[]{1,13,25,37,49}},
            {"蛇", new int[]{2,14,26,38}},
            {"龙", new int[]{3,15,27,39}},
            {"兔", new int[]{4,16,28,40}},
            {"虎", new int[]{5,17,29,41}},
            {"牛", new int[]{6,18,30,42}},
            {"鼠", new int[]{7,19,31,43}},
            {"猪", new int[]{8,20,32,44}},
            {"狗", new int[]{9,21,33,45}},
            {"鸡", new int[]{10,22,34,46}},
            {"猴", new int[]{11,23,35,47}},
            {"羊", new int[]{12,24,36,48}}
        };
        for (Object[] row : t) {
            String z = (String) row[0];
            int[] nums = (int[]) row[1];
            List<Integer> list = new ArrayList<>();
            for (int n : nums) { N2Z[n] = z; list.add(n); }
            Z2N.put(z, list);
        }
    }

    // 波色：1 红 2 蓝 3 绿（专业版号码色标同色）
    private static final java.util.Set<Integer> RED = new java.util.HashSet<>(java.util.Arrays.asList(
            1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46));
    private static final java.util.Set<Integer> BLUE = new java.util.HashSet<>(java.util.Arrays.asList(
            3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48));

    public static int wave(int n) {
        if (RED.contains(n)) return 1;
        if (BLUE.contains(n)) return 2;
        return 3;
    }

    public static String of(int n) {
        return (n >= 1 && n <= 49) ? N2Z[n] : "";
    }

    public static List<Integer> nums(String zodiac) {
        List<Integer> l = Z2N.get(zodiac);
        return l == null ? new ArrayList<Integer>() : l;
    }

    public static boolean isZodiac(String s) {
        return Z2N.containsKey(s);
    }

    /** 该期开奖涉及的生肖集合（含特码） */
    public static Set<String> hitZodiacs(List<Integer> regular, int special) {
        Set<String> s = new HashSet<>();
        for (int n : regular) { String z = of(n); if (!z.isEmpty()) s.add(z); }
        String z = of(special);
        if (!z.isEmpty()) s.add(z);
        return s;
    }

    /** 号码 → 生肖（与专业版 NUM2ZODIAC 一致） */
    public static String zodiacOf(int n) {
        if (n < 1 || n > 49) return null;
        String[] order = {"马", "蛇", "龙", "兔", "虎", "牛", "鼠", "猪", "狗", "鸡", "猴", "羊"};
        return order[(n - 1) % 12];
    }
}
