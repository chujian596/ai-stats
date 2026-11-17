package io.github.chujian596.app.ntv;

import java.util.*;

/** 一期开奖 */
public class Draw {
    public int period = 0;
    public List<Integer> regular = new ArrayList<>();
    public int special = 0;
    public String lottery = "澳";

    public Draw() {}
    public Draw(int period, List<Integer> regular, int special) {
        this.period = period; this.regular = regular; this.special = special;
    }

    public List<Integer> all() {
        List<Integer> l = new ArrayList<>(regular);
        l.add(special);
        return l;
    }

    public String line() {
        StringBuilder b = new StringBuilder();
        for (int n : regular) b.append(String.format("%02d ", n));
        b.append("+ ").append(String.format("%02d", special));
        return b.toString();
    }
}
