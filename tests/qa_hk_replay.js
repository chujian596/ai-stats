(() => {
  const R = {cases:[], failures:[]};
  const gate = (name, ok, actual) => {
    const c = {name, status: ok ? 'PASS' : 'FAIL', actual};
    R.cases.push(c); if(!ok) R.failures.push(c);
  };
  if(typeof shop === 'undefined' || shop !== 'B'){
    R.failures.push({name:'香港店环境',status:'FAIL',actual:typeof shop}); R.pass=0; R.fail=1; return R;
  }
  lastDraw = null;
  orders = []; hkOrders = [];
  try{ saveOrders(); }catch(e){}
  try{ saveHKOrders(); }catch(e){}
  hkSetDrawCache({draw:122, nums:[30,42,7,4,45,18,36]});
  _hkBarVisible = true;
  localStorage.setItem('rebateOn','0');

  document.getElementById('customerName').value = '港回放';
  window.__previewConfirmed = true;
  doSave('特36 100');
  doSave('二中二30,42 100');

  const hkDetail = hkPayoutInfo();
  const noFly = actualPnL();
  const noFlyToday = todayReconData();
  gate('香港122期开奖读取', hkDrawObj() && hkDrawObj().draw === 122 && hkDrawObj().specialNum === 36, hkDrawObj());
  gate('香港注单赔付', hkDetail && hkDetail.sales === 200 && hkDetail.pay === 10700 && hkDetail.net === -10500, hkDetail);
  gate('无澳门开奖时今日对账仍按港奖', noFlyToday.payout === 10700 && noFlyToday.gross === -10500, {payout:noFlyToday.payout,gross:noFlyToday.gross,localNet:noFlyToday.localNet});

  flownPerPos = {'36':100}; flownReal = {'36':100};
  autoFlyOn = true; splitTakeAll = 0;
  localStorage.setItem('rebateOn','1'); localStorage.setItem('rebateRate','0.03');
  const ap = actualPnL();
  const d = todayReconData();
  gate('香港全飞/赔回/盈亏', ap.flyOut === 200 && ap.flyBack === 10700 && ap.net === 0, ap);
  gate('香港返水/上家结算', Math.abs(ap.rebate - 6) < 0.01 && Math.abs(d.upSettle - 10506) < 0.01, {rebate:ap.rebate,upSettle:d.upSettle});
  R.pass = R.cases.filter(c => c.status === 'PASS').length;
  R.fail = R.cases.filter(c => c.status === 'FAIL').length;
  R.hkDetail = hkDetail;
  R.noFlyToday = {payout:noFlyToday.payout,gross:noFlyToday.gross};
  R.fly = {flyOut:ap.flyOut,flyBack:ap.flyBack,net:ap.net,rebate:ap.rebate,upSettle:d.upSettle};
  return R;
})()
