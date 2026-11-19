/* 平特单肖 7 号口径回归：6 个平号 + 特号，任一命中即中。 */
(async()=>{
  const R = { version: (typeof APP_VER !== 'undefined' ? APP_VER : '?'), runner: 'pte-single-v1', cases: [], failures: [] };
  const draw = { period: 321, specialNum: 3, regularNums: [1, 4, 5, 7, 24, 32] }; // 03 龙；01 马、04 兔、05 虎、07 鼠、24 羊、32 猪
  function check(name, code, d, expect) {
    const o = { codes: [code], codeAmts: { [code]: 100 }, price: 100, amount: 100 };
    const r = calcOrderWinDetail(o, d);
    const ok = Math.abs(Number(r.total) - Number(expect)) < 0.01;
    R.cases.push({ name, code, total: r.total, expect, status: ok ? 'PASS' : 'FAIL', lines: r.lines });
    if (!ok) R.failures.push({ name, got: r.total, expect });
  }
  check('平特龙靠特号命中', '平特龙', draw, 200);
  check('平特马靠平号命中并含马1.8', '平特马', draw, 180);
  check('平特龙无龙不中', '平特龙', { period: 321, specialNum: 1, regularNums: [4, 5, 7, 24, 32, 49] }, 0);
  R.pass = R.cases.filter(c => c.status === 'PASS').length;
  R.fail = R.failures.length;
  return JSON.stringify(R);
})()
