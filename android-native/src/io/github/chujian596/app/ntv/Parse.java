package io.github.chujian596.app.ntv;

import java.util.*;
import java.util.regex.*;

/**
 * 录单解析：一行文本 → 一笔订单。
 * 口径照专业版 app-pro.html 的 parseLine，逐条对齐。
 */
public class Parse {

    static final String ZC = "马蛇龙兔虎牛鼠猪狗鸡猴羊";
    /** 波色 / 单双 / 大小 / 合数 这类「买特码属性」的产品 */
    static final String[] ATTR = {
        "红波单大", "红波单小", "红波双大", "红波双小",
        "蓝波单大", "蓝波单小", "蓝波双大", "蓝波双小",
        "绿波单大", "绿波单小", "绿波双大", "绿波双小",
        "红波单", "红波双", "蓝波单", "蓝波双", "绿波单", "绿波双",
        "红波大", "红波小", "蓝波大", "蓝波小", "绿波大", "绿波小",
        "红波", "蓝波", "绿波",
        "合数单", "合数双",
        "单数", "双数", "大", "小"
    };


    /** 属性玩法覆盖的号码（照专业版 products 的 links 表） */
    static final Map<String, String> ATTR_LINKS = new LinkedHashMap<>();
    static {
        ATTR_LINKS.put("红波", "01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46");
        ATTR_LINKS.put("绿波", "05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49");
        ATTR_LINKS.put("蓝波", "03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48");
        ATTR_LINKS.put("单数", "01,03,05,07,09,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49");
        ATTR_LINKS.put("双数", "02,04,06,08,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48");
        ATTR_LINKS.put("大", "25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49");
        ATTR_LINKS.put("小", "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24");
        ATTR_LINKS.put("合数单", "01,03,05,07,09,10,12,14,16,18,21,23,25,27,29,30,32,34,36,38,41,43,45,47,49");
        ATTR_LINKS.put("合数双", "02,04,06,08,11,13,15,17,19,20,22,24,26,28,31,33,35,37,39,40,42,44,46,48");
        ATTR_LINKS.put("红波单", "01,07,13,19,23,29,35,45");
        ATTR_LINKS.put("红波双", "02,08,12,18,24,30,34,40,46");
        ATTR_LINKS.put("绿波单", "05,11,17,21,27,33,39,43,49");
        ATTR_LINKS.put("绿波双", "06,16,22,28,32,38,44");
        ATTR_LINKS.put("蓝波单", "03,09,15,25,31,37,41,47");
        ATTR_LINKS.put("蓝波双", "04,10,14,20,26,36,42,48");
        ATTR_LINKS.put("红波大", "29,30,34,35,40,45,46");
        ATTR_LINKS.put("红波小", "01,02,07,08,12,13,18,19,23,24");
        ATTR_LINKS.put("蓝波大", "25,26,31,36,37,41,42,47,48");
        ATTR_LINKS.put("蓝波小", "03,04,09,10,14,15,20");
        ATTR_LINKS.put("绿波大", "27,28,32,33,38,39,43,44,49");
        ATTR_LINKS.put("绿波小", "05,06,11,16,17,21,22");
        ATTR_LINKS.put("红波单大", "29,35,45");
        ATTR_LINKS.put("红波单小", "01,07,13,19,23");
        ATTR_LINKS.put("红波双大", "30,34,40,46");
        ATTR_LINKS.put("红波双小", "02,08,12,18,24");
        ATTR_LINKS.put("蓝波单大", "25,31,37,41,47");
        ATTR_LINKS.put("蓝波单小", "03,09,15");
        ATTR_LINKS.put("蓝波双大", "26,36,42,48");
        ATTR_LINKS.put("蓝波双小", "04,10,14,20");
        ATTR_LINKS.put("绿波单大", "27,33,39,43,49");
        ATTR_LINKS.put("绿波单小", "05,11,17,21");
        ATTR_LINKS.put("绿波双大", "28,32,38,44");
        ATTR_LINKS.put("绿波双小", "06,16,22");
    }

    /** 检测「属性玩法 + 金额」但没写「各」，需要弹窗问：总额摊号 还是 各号 */
    static String[] detectWave(String line) {
        if (line == null) return null;
        String t = line.trim();
        if (t.isEmpty() || t.contains("各") || t.contains("每")) return null;
        java.util.List<String> keys = new java.util.ArrayList<>(ATTR_LINKS.keySet());
        keys.sort((a, b) -> b.length() - a.length());   // 长名优先：红波单大 先于 红波
        for (String k : keys) {
            java.util.regex.Matcher m = java.util.regex.Pattern
                .compile(java.util.regex.Pattern.quote(k) + "\\s*([0-9]+(?:\\.[0-9]+)?)\\s*元?\\s*$")
                .matcher(t);
            if (m.find()) return new String[]{k, m.group(1)};
        }
        return null;
    }

    /** 该属性覆盖多少个号 */
    static int linkCount(String attr) {
        String links = ATTR_LINKS.get(attr);
        return links == null ? 0 : links.split(",").length;
    }

    /** 本次解析是否展开过属性玩法（展开后按「各号」计价） */
    static boolean expanded = false;

    public static Order parseLine(String raw) throws Exception {
        expanded = false;
        String text = raw == null ? "" : raw.trim();
        text = text.replaceAll("[\\s,，、;；.。]+$", "");
        if (text.isEmpty()) return null;

        // ---- 快速通道：整行就是「一串号码 + 各/每个 + 金额」 ----
        String SEP = "[\\s\\-\\u2010-\\u2015\\uFF0D、.。+·]+";
        Matcher fast = Pattern.compile("^((?:\\d{1,2}" + SEP + ")+\\d{1,2})\\s*(?:各(?:数|号|个|件|样|款|肖|组|注|码|只)?|每(?:组|个|号|肖|注|码|只)?|个)\\s*([0-9]+(?:\\.[0-9]+)?)\\s*元?\\s*$").matcher(text);
        if (fast.find()) {
            String[] raw2 = fast.group(1).split(SEP);
            List<String> codes = new ArrayList<>();
            for (String n : raw2) if (!n.isEmpty()) codes.add(pad2(n));
            if (!codes.isEmpty()) return build(codes, Double.parseDouble(fast.group(2)), true, raw);
        }

        // ---- 中文金额 ----
        text = cnAmount(text);

        // ---- 简写 ----
        text = text.replace("3中3", "三中三").replace("2中2", "二中二").replace("3中2", "三中二");
        text = text.replace("/", " ");

        // ---- 保护「产品:号,号」不被价格提取和分隔符打散 ----
        List<String> kept = new ArrayList<>();
        text = protect(text, kept);

        // ---- 去掉地名前缀 ----
        text = text.replaceAll("^(新澳|澳门|香港|澳|港|新)", "");

        // ---- 取价格 ----
        String numRe = "([0-9]+(?:\\.[0-9]+)?)";
        String unitRe = "(?:\\s*(?:元|米|块|钱|块钱|圆|RMB|rmb))?";
        boolean isPer;
        double price;
        String codeText;
        Matcher mPer = Pattern.compile("(?:各(?:数|号|个|件|样|款|肖|组)?|每(?:组|个|号|肖)?|个)\\s*" + numRe + unitRe + "\\s*$").matcher(text);
        Matcher mTot = Pattern.compile(numRe + unitRe + "\\s*$").matcher(text);
        if (mPer.find()) {
            isPer = true;
            price = Double.parseDouble(mPer.group(1));
            codeText = text.substring(0, mPer.start()).trim();
        } else if (mTot.find()) {
            isPer = false;
            price = Double.parseDouble(mTot.group(1));
            codeText = text.substring(0, mTot.start()).trim();
        } else {
            throw new Exception("没找到价格：" + text);
        }
        if (!(price > 0)) throw new Error0("价格必须大于0");

        // ---- 分隔符统一（在还原保护串之前做，别把「产品:号,号」的逗号打散）----
        String pre = codeText.replaceAll("[–—―·+、]+", " ").replaceAll("([0-9])\\.([0-9])", "$1 $2");
        pre = pre.replaceAll("([0-9]),([0-9])", "$1 $2");
        text = restore(pre, kept);

        // ---- 产品归一化 ----
        // 特号/特碼 → 特；连续特折叠
        text = text.replace("特号", "特").replace("特碼", "特").replace("特码", "特");
        text = text.replaceAll("特{2,}", "特");

        // 平特先占位
        text = text.replace("平特", "『PT』");
        // 「特22」→ 22
        text = text.replaceAll("特(?=\\s*\\d)", " ");

        // 「特单」「特红波」「特大」→ 去掉特，属性产品本身就是买特码
        text = text.replaceAll("特(?=红波|蓝波|绿波|合数|单数|双数|单|双|大|小)", "");

        // 裸「单」「双」补全（放在去特之后，才能处理「特单」）
        text = text.replaceAll("(?<![红蓝绿波合数])单(?=\\s*[0-9]|\\s*$|\\s)", "单数");
        text = text.replaceAll("(?<![红蓝绿波合数])双(?=\\s*[0-9]|\\s*$|\\s)", "双数");

        // 特X（一串生肖）→ X数
        Matcher mTS = Pattern.compile("特肖?([" + ZC + "]+)").matcher(text);
        StringBuffer sb = new StringBuffer();
        while (mTS.find()) {
            StringBuilder b = new StringBuilder(" ");
            for (char c : mTS.group(1).toCharArray()) b.append(c).append("数 ");
            mTS.appendReplacement(sb, b.toString());
        }
        mTS.appendTail(sb);
        text = sb.toString();

        // 虎平 → 平特虎
        text = text.replaceAll("([" + ZC + "])平", "『PT』$1");
        // 平肖X / 平X
        text = text.replaceAll("平肖([" + ZC + "])", "『PT』$1");
        text = text.replaceAll("平(?!特)([" + ZC + "])", "『PT』$1");
        // 「马龙兔平特肖」→ 逐肖
        text = expandPingteSuffix(text);
        // 平特一肖X / 平特肖X → 平特X
        text = text.replaceAll("『PT』一肖\\s*([" + ZC + "])", "『PT』$1");
        text = text.replaceAll("『PT』肖\\s*([" + ZC + "])", "『PT』$1");
        // 平特马龙兔 → 逐肖
        text = expandPingte(text);

        // 连肖：平连 / X连YZ / 连XY / 三连肖 / XY三连肖
        text = text.replaceAll("平连([" + ZC + "]{2,4})", " 连肖$1 ");
        text = text.replaceAll("([" + ZC + "])连([" + ZC + "]{1,4})", " 连肖$1$2 ");
        text = text.replaceAll("[二三四]连肖?([" + ZC + "]{2,4})", " 连肖$1 ");
        text = text.replaceAll("连肖?([" + ZC + "]{2,4})", " 连肖$1 ");
        text = text.replaceAll("([" + ZC + "]{2,4})[二三四]连肖?", " 连肖$1 ");

        // 头数 / 尾数
        Matcher mHead = Pattern.compile("(\\d)头").matcher(text);
        sb = new StringBuffer();
        while (mHead.find()) {
            int h = Integer.parseInt(mHead.group(1));
            StringBuilder b = new StringBuilder(" ");
            for (int i = 1; i <= 9; i++) {
                int n = h * 10 + i;
                if (n >= 1 && n <= 49) b.append(String.format("%02d", n)).append(" ");
            }
            mHead.appendReplacement(sb, b.toString());
        }
        mHead.appendTail(sb);
        text = sb.toString();

        Matcher mTail = Pattern.compile("尾(\\d)").matcher(text);
        sb = new StringBuffer();
        while (mTail.find()) {
            int t = Integer.parseInt(mTail.group(1));
            StringBuilder b = new StringBuilder(" ");
            for (int h = 0; h <= 4; h++) {
                int n = h * 10 + t;
                if (n >= 1 && n <= 49) b.append(String.format("%02d", n)).append(" ");
            }
            mTail.appendReplacement(sb, b.toString());
        }
        mTail.appendTail(sb);
        text = sb.toString();

        // 生肖数 → 展开号码
        text = text.replaceAll("([" + ZC + "])数", "  $1肖  ");

        // 「三中三34 32 46」「34 32 46三中三」→ 三中三:34,32,46
        text = groupCombo(text);

        // ---- 复式展开 ----
        text = expandFushi(text);

        // ---- 组装 ----
        List<String> codes = new ArrayList<>();
        // 生肖肖标记展开
        Matcher mZX = Pattern.compile("([" + ZC + "])肖").matcher(text);
        sb = new StringBuffer();
        while (mZX.find()) {
            StringBuilder b = new StringBuilder(" ");
            for (int n : Z.nums(mZX.group(1))) b.append(String.format("%02d", n)).append(" ");
            mZX.appendReplacement(sb, b.toString());
        }
        mZX.appendTail(sb);
        text = sb.toString();

        // 裸生肖：单个 → 特肖展开；多个连续 → 报歧义
        text = restore(text, kept);
        text = text.replaceAll("(『PT』|连肖)([" + ZC + "]+)", "$1$2 ");

        text = scan(text, codes);

        if (codes.isEmpty()) throw new Exception("没认出任何玩法：" + raw);
        if (expanded) isPer = true;   // 红波/单双/大小这类按「每个号各 X」记账
        return build(codes, price, isPer, raw);
    }

    /** 扫描：产品名优先（长名先），其次号码；认不出的文本直接报错 */
    static String scan(String text, List<String> codes) throws Exception {
        // 把「平特X」「连肖XYZ」从占位还原并单独抠出
        text = text.replaceAll("『PT』([" + ZC + "]+)", " 平特$1 ");

        String rest = text;
        while (true) {
            rest = rest.replaceAll("^[\\s,，、;；.。号]+", "");
            if (rest.isEmpty()) break;
            // 组合产品：二中二:号,号
            Matcher em = Pattern.compile("^(二中二|三中三|三中二)[:：](\\d{2}(?:,\\d{2})+)").matcher(rest);
            if (em.find()) { codes.add(em.group(1) + ":" + em.group(2)); rest = rest.substring(em.end()); continue; }
            // 平特 / 连肖
            Matcher pt = Pattern.compile("^(平特[" + ZC + "])").matcher(rest);
            if (pt.find()) { codes.add(pt.group(1)); rest = rest.substring(pt.end()); continue; }
            Matcher lx = Pattern.compile("^(连肖[" + ZC + "]{2,4})").matcher(rest);
            if (lx.find()) { codes.add(lx.group(1)); rest = rest.substring(lx.end()); continue; }
            // 属性产品（长名优先）
            String hitAttr = null;
            for (String a : ATTR) if (rest.startsWith(a)) { if (hitAttr == null || a.length() > hitAttr.length()) hitAttr = a; }
            if (hitAttr != null) {
                String links = ATTR_LINKS.get(hitAttr);
                if (links != null) {
                    for (String x : links.split(",")) codes.add(x);
                    expanded = true;
                } else {
                    codes.add(hitAttr);
                }
                rest = rest.substring(hitAttr.length());
                continue;
            }
            // 号码
            Matcher nu = Pattern.compile("^(\\d{1,2})(?!\\d)").matcher(rest);
            if (nu.find()) {
                int n = Integer.parseInt(nu.group(1));
                if (n >= 1 && n <= 49) codes.add(String.format("%02d", n));
                rest = rest.substring(nu.end());
                continue;
            }
            // 认不出来 → 报错，不静默丢
            Matcher bad = Pattern.compile("^([^\\d\\s]+)").matcher(rest);
            if (bad.find()) throw new Exception("无法识别：「" + bad.group(1).trim() + "」");
            Matcher bad3 = Pattern.compile("^(\\d{3,})").matcher(rest);
            if (bad3.find()) throw new Exception("无法识别的数字："
                    + bad3.group(1) + "（三位以上请写成「各" + bad3.group(1) + "」或「共" + bad3.group(1) + "」）");
            rest = rest.substring(1);
        }
        return rest;
    }

    static Order build(List<String> codes, double price, boolean isPer, String raw) {
        Order o = new Order();
        o.price = price;
        o.isPer = isPer;
        o.raw = raw;
        for (String c : codes) if (!o.codes.contains(c)) o.codes.add(c);
        return o;
    }

    static String pad2(String n) {
        try { return String.format("%02d", Integer.parseInt(n.trim())); } catch (Exception e) { return n; }
    }

    /** 「马龙兔『PT』肖」→ 逐肖 */
    static String expandPingteSuffix(String text) {
        Matcher m = Pattern.compile("([" + ZC + "]{1,4})『PT』(肖)?(?![马蛇龙兔虎牛鼠猪狗鸡猴羊])").matcher(text);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            StringBuilder b = new StringBuilder(" ");
            for (char c : m.group(1).toCharArray()) b.append("『PT』").append(c).append(' ');
            m.appendReplacement(sb, b.toString());
        }
        m.appendTail(sb);
        return sb.toString();
    }

    /** 把「『PT』马龙兔」拆成「『PT』马 『PT』龙 『PT』兔」 */
    static String expandPingte(String text) {
        StringBuilder out = new StringBuilder();
        int i = 0;
        String marker = "『PT』";
        while (true) {
            int k = text.indexOf(marker, i);
            if (k < 0) { out.append(text.substring(i)); break; }
            out.append(text, i, k);
            int j = k + marker.length();
            int end = j;
            while (end < text.length() && ZC.indexOf(text.charAt(end)) >= 0) end++;
            String zs = text.substring(j, end);
            if (zs.isEmpty()) { out.append(marker); i = j; continue; }
            for (char c : zs.toCharArray()) out.append(marker).append(c).append(' ');
            i = end;
        }
        return out.toString();
    }

    /** 组合玩法：产品名与号码分开写时合起来 */
    static String groupCombo(String text) {
        String[] prods = {"二中二", "三中三", "三中二"};
        for (String p : prods) {
            int need = p.equals("二中二") ? 2 : 3;
            // 产品在前：三中三 34 32 46
            Pattern a = Pattern.compile(p + "\\s*(\\d{2})(?:\\s+(\\d{2}))?(?:\\s+(\\d{2}))?");
            Matcher ma = a.matcher(text);
            StringBuffer sb = new StringBuffer();
            while (ma.find()) {
                List<String> ns = new ArrayList<>();
                for (int g = 1; g <= 3; g++) if (ma.group(g) != null) ns.add(ma.group(g));
                if (ns.size() == need) ma.appendReplacement(sb, " " + p + ":" + String.join(",", ns) + " ");
                else ma.appendReplacement(sb, " " + p + " ");
            }
            ma.appendTail(sb);
            text = sb.toString();
            // 产品在后：34 32 46 三中三
            Pattern b = Pattern.compile("(\\d{2})(?:\\s+(\\d{2}))?(?:\\s+(\\d{2}))?\\s?" + p);
            Matcher mb = b.matcher(text);
            sb = new StringBuffer();
            while (mb.find()) {
                List<String> ns = new ArrayList<>();
                for (int g = 1; g <= 3; g++) if (mb.group(g) != null) ns.add(mb.group(g));
                if (ns.size() == need) mb.appendReplacement(sb, " " + p + ":" + String.join(",", ns) + " ");
                else mb.appendReplacement(sb, " ");
            }
            mb.appendTail(sb);
            text = sb.toString();
        }
        return text;
    }

    // ---------- 复式 ----------

    static String expandFushi(String text) throws Exception {
        Matcher m = Pattern.compile("((?:\\d{2}[-.、\\s])+\\d{2})\\s*复(?:式)?\\s*(?:(三中三|二中二|三中二)|([二三]))").matcher(text);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String numStr = m.group(1);
            List<String> ns = new ArrayList<>();
            for (String x : numStr.split("[-.、\\s]+")) if (x.matches("\\d{2}")) ns.add(x);
            Collections.sort(ns);
            boolean is2 = "二中二".equals(m.group(2)) || "二".equals(m.group(3));
            String prod = is2 ? "二中二" : "三中三";
            int k = is2 ? 2 : 3;
            StringBuilder b = new StringBuilder(" ");
            if (ns.size() < k) { m.appendReplacement(sb, " "); continue; }
            for (List<Integer> c : combosOf(ns.toArray(new String[0]), k)) {
                b.append(prod).append(":");
                for (int i = 0; i < c.size(); i++) { if (i > 0) b.append(","); b.append(ns.get(c.get(i))); }
                b.append(" ");
            }
            m.appendReplacement(sb, b.toString());
        }
        m.appendTail(sb);
        return sb.toString();
    }

    // ---------- 中文金额 ----------

    static String cnAmount(String t) {
        String[][] map = {
            {"一百二十", "120"}, {"一百五十", "150"}, {"两百五十", "250"},
            {"一百", "100"}, {"两百", "200"}, {"三百", "300"}, {"四百", "400"}, {"五百", "500"},
            {"二十", "20"}, {"三十", "30"}, {"四十", "40"}, {"五十", "50"},
            {"六十", "60"}, {"七十", "70"}, {"八十", "80"}, {"九十", "90"},
            {"壹佰", "100"}, {"贰佰", "200"}, {"叁佰", "300"},
            {"一十", "10"}
        };
        for (String[] m : map) t = t.replace(m[0], m[1]);
        // 单独的「十」
        t = t.replaceAll("(?<![0-9一二三四五六七八九])十(?![0-9])", "10");
        return t;
    }

    // ---------- 「产品:号,号」保护 ----------

    static String protect(String text, List<String> kept) {
        Matcher m = Pattern.compile("(二中二|三中三|三中二)\\s*[:：]?\\s*(\\d{2}(?:,\\d{2})+)").matcher(text);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            kept.add(m.group(1) + ":" + m.group(2));
            m.appendReplacement(sb, " 『K" + (kept.size() - 1) + "』 ");
        }
        m.appendTail(sb);
        return sb.toString();
    }

    static String restore(String text, List<String> kept) {
        for (int i = 0; i < kept.size(); i++) {
            text = text.replace("『K" + i + "』", " " + kept.get(i) + " ");
        }
        return text;
    }

    /** 复式：从 n 个号码里挑 k 个的全部组合（返回下标） */
    static List<List<Integer>> combosOf(String[] arr, int k) {
        List<List<Integer>> out = new ArrayList<>();
        int n = arr.length;
        if (n < k) return out;
        int[] idx = new int[k];
        for (int i = 0; i < k; i++) idx[i] = i;
        while (true) {
            List<Integer> one = new ArrayList<>();
            for (int i : idx) one.add(i);
            out.add(one);
            int pos = k - 1;
            while (pos >= 0 && idx[pos] == n - k + pos) pos--;
            if (pos < 0) break;
            idx[pos]++;
            for (int i = pos + 1; i < k; i++) idx[i] = idx[i - 1] + 1;
        }
        return out;
    }

    /** 代码转生肖：纯数字按号码转，带生肖字的按包含判定；都不是就返回 null */
    public static String zodiacOf(String code) {
        if (code == null || code.isEmpty()) return null;
        if (code.matches("\\d{1,2}")) {
            try { return Z.zodiacOf(Integer.parseInt(code)); } catch (Exception e) { return null; }
        }
        for (String z : Z.ZODIAC) if (code.contains(z)) return z;
        return null;
    }

    /** 内部异常：价格非法 */
    static class Error0 extends Exception {
        Error0(String m) { super(m); }
    }
}
