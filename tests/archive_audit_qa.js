/* 归档自检 / 录入失败日志 / 重复单日志 验证 */
(async()=>{
const WAIT=ms=>new Promise(r=>setTimeout(r,ms));
try{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}catch(e){}
window.myAlert=m=>{window.__al=(window.__al||[]).concat(String(m));};
window.myConfirm=()=>{};
const out={cases:[],fails:[]};
function ck(name,ok,got){out.cases.push({name,status:ok?'PASS':'FAIL',got:got});if(!ok)out.fails.push(name+':'+JSON.stringify(got));}

// 1. 正数：一天归档，汇总和实际一致
billArchive={'2026-11-18':{orders:[{customer:'甲',raw:'特01 100',amount:100}],pays:[],sum:{n:1,amt:100,pay:0,net:100},savedAt:'x'}};
let a=auditBillArchive(false);
ck('归档汇总一致', a.ok===true && a.days===1 && a.issues.length===0, {ok:a.ok,days:a.days,issues:a.issues});

// 2. 差额 + 重复 + 断档
billArchive={'2026-11-18':{orders:[{customer:'甲',raw:'特01 100',amount:100}],pays:[],sum:{n:1,amt:100,pay:0,net:100},savedAt:'x'},
 '2026-11-20':{orders:[{customer:'乙',raw:'特02 100',amount:100,createdAt:'2026/11/20 12:00:03'},{customer:'乙',raw:'特02 100',amount:100,createdAt:'2026/11/20 12:00:08'}],pays:[],sum:{n:2,amt:100,pay:0,net:100},savedAt:'x'}};
a=auditBillArchive(false);
ck('归档差额识别', a.issues.some(x=>/收单/.test(x.msg)) && a.issues.some(x=>/净额/.test(x.msg)), a.issues);
ck('3分钟内同内容标待核对', a.review.some(x=>/3 分钟内/.test(x.msg)), a.review);
ck('无归档日识别', a.missing.indexOf('2026-11-19')>=0, a.missing);

// 2b. 作废其中一笔：汇总重算 + 留 voided
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};
const before180=(billArchive['2026-11-20']||{}).sum;
billVoidOrder('2026-11-20',0);
const after180=(billArchive['2026-11-20']||{});
ck('作废后重算', after180.orders.length===1 && after180.sum.n===1 && Math.abs(after180.sum.amt-100)<0.01 && (after180.voided||[]).length===1, {sum:after180.sum,voided:(after180.voided||[]).length,before:before180});

// 2c. 日期/时间边界：跨天不合并；同天间隔久按两注；3 分钟内才提示
billArchive={
 '2026-11-15':{orders:[{customer:'叶',raw:'蛇数各10',amount:40,createdAt:'2026/11/15 10:00:01'},{customer:'叶',raw:'蛇数各10',amount:40,createdAt:'2026/11/15 10:00:30'}],pays:[],sum:{n:2,amt:80,pay:0,net:80}},
 '2026-11-16':{orders:[{customer:'叶',raw:'蛇数各10',amount:40,createdAt:'2026/11/16 10:00:01'}],pays:[],sum:{n:1,amt:40,pay:0,net:40}},
 '2026-11-17':{orders:[{customer:'叶',raw:'虎平500',amount:500,createdAt:'2026/11/17 09:00:00'},{customer:'叶',raw:'虎平500',amount:500,createdAt:'2026/11/17 21:00:00'}],pays:[],sum:{n:2,amt:1000,pay:0,net:1000}}
};
a=auditBillArchive(false);
ck('3分钟内同内容提示', a.review.some(x=>x.day==='2026-11-15'), a.review);
ck('同天隔久不判重', !a.review.some(x=>x.day==='2026-11-17'), a.review);
ck('跨天同内容不合并判重', !a.review.some(x=>x.day==='2026-11-16'), a.review);

// 3. 解析失败写日志：带原文 + 账本日（doSave 的失败路径就是写这条记录）
clearErrLog();
logErr('parse','无法识别：「特0X 100」',{line:1,raw:'特0X 100',day:(billBookDate()||billToday())});
let logs=readErrLog(); let last=logs[logs.length-1]||{};
ck('录入失败写日志', last.type==='parse' && /无法识别|没找到|异常/.test(last.msg||''), last);
ck('日志保留原文', String((last.meta||{}).raw||'').indexOf('特0X')>=0, last.meta);
ck('日志带账本日', !!last.day, last.day);

// 4. 重复单写日志
clearErrLog();
const inp=document.getElementById('input'); inp.value='特01 100';
try{handleSave();}catch(e){}
await WAIT(120);
inp.value='特01 100';
window.__lastInputFp=null; window.__lastInputAt=0;
try{handleSave();}catch(e){}
await WAIT(80);
logs=readErrLog(); last=logs[logs.length-1]||{};
ck('重复单写日志', last.type==='dup_order', last);

// 5. 一次多行无法识别：每一行都要进日志，且能汇总成可复制清单
clearErrLog();
inp.value='特0X 100\n特0Y 200';
try{ doSave(); }catch(e){}
await WAIT(150);
logs=readErrLog().filter(function(r){ return r.type==='parse'; });
ck('失败行逐条入日志', logs.length>=2 && logs.some(function(r){ return String((r.meta||{}).raw||'').indexOf('特0X')>=0; }) && logs.some(function(r){ return String((r.meta||{}).raw||'').indexOf('特0Y')>=0; }), logs.map(function(r){ return (r.meta||{}).raw; }));
const pf=parseFailGroups();
ck('失败清单按原文汇总', pf.total>=2 && pf.groups.length>=2, {total:pf.total,groups:pf.groups.length});
const pft=parseFailText();
ck('失败清单文本含原文', pft.indexOf('特0X')>=0 && pft.indexOf('特0Y')>=0, pft.slice(0,160));
ck('失败弹窗有一键复制', !!document.getElementById('pfCopy'), !!document.getElementById('pfCopy'));
ck('复制诊断入口存在', typeof copyDiagnostics==='function', typeof copyDiagnostics);
const _pfClose=document.getElementById('pfClose'); if(_pfClose)_pfClose.click();

// 6. 平龙10 与三中三同行：各自计价，不能把 10 当号码、把组5 套给平龙
orders=[]; hkOrders=[];
window.__previewConfirmed=true;
inp.value='平龙10三中三11.22.33组5';
try{ doSave(); }catch(e){}
const _mixOrder=(orders||[])[0]||{};
ck('平龙10按10计价', (orders||[]).length===1 && Math.abs(_mixOrder.amount-15)<0.01 && _mixOrder.codeAmts && _mixOrder.codeAmts['平特龙']===10 && _mixOrder.codeAmts['三中三:11,22,33']===5 && (_mixOrder.codes||[]).indexOf('10')<0, {amount:_mixOrder.amount,amts:_mixOrder.codeAmts,codes:_mixOrder.codes});
window.__previewConfirmed=false;

// 7. 清除订单：本店账、跨店客户镜像、香港全局池、待补记队列要一起清
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};
orders=[{id:'qa-a',customer:'甲',raw:'特01 100',amount:100,createdAt:'2026/11/20 10:00:00'}];
hkOrders=[{id:'qa-h',customer:'甲',raw:'特02 100',amount:100,createdAt:'2026/11/20 10:00:00',hk:true}];
_writeJSONArr(MAC_GLOBAL_KEY,[{id:'qa-g',customer:'乙',raw:'特03 100',amount:100,createdAt:'2026/11/20 10:00:00'}]);
_writeJSONArr(HK_GLOBAL_KEY,hkOrders.slice());
_writeJSONArr(HK_GLOBAL_PAY_KEY,[{id:'qa-pay'}]);
localStorage.setItem(HK_GLOBAL_FLY_KEY,'{"x":1}');
_writePendingOrders([{id:'qa-pending',customer:'丙',raw:'特04 100',amount:100}]);
clearOrders();
ck('清除订单连跨店镜像一起清', orders.length===0 && hkOrders.length===0 && customerOrders().length===0
  && _readJSONArr(MAC_GLOBAL_KEY).length===0 && _readJSONArr(HK_GLOBAL_KEY).length===0
  && _readPendingOrders().length===0 && localStorage.getItem(HK_GLOBAL_FLY_KEY)==='{}',
  {orders:orders.length,hk:hkOrders.length,cust:(typeof customerOrders==='function'?customerOrders().length:-1),mac:_readJSONArr(MAC_GLOBAL_KEY).length,hkG:_readJSONArr(HK_GLOBAL_KEY).length,pending:_readPendingOrders().length});

// 8. 没有开奖信息时，不能拿旧全局缓存算中奖
orders=[{id:'nodraw',customer:'散客',raw:'平特龙10 三中三 11.22.33组5',amount:15,codes:['平特龙','三中三:11,22,33'],codeAmts:{'平特龙':10,'三中三:11,22,33':5},createdAt:'2026/11/20 15:02:30'}];
hkOrders=[];
lastDraw=null;
localStorage.setItem(MAC_DRAW_GLOBAL_KEY,JSON.stringify({period:'323',regularNums:[1,2,3,11,22,33],specialNum:10}));
var _noDrawWin=calcOrderWinDetail(orders[0],macDrawForOrders()).total;
ck('无开奖不计算命中', _noDrawWin===0 && macDrawForOrders()===null, {win:_noDrawWin,draw:macDrawForOrders()});

// 9. 撤销开奖要连全局缓存一起清，列表/复制不能再用旧号码
lastDraw={period:'323',regularNums:[1,2,3,11,22,33],specialNum:10};
saveLastDraw();
ck('开奖写入全局缓存', !!localStorage.getItem(MAC_DRAW_GLOBAL_KEY), !!localStorage.getItem(MAC_DRAW_GLOBAL_KEY));
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};
clearDrawRecord();
ck('撤销开奖清全局缓存', lastDraw===null && !localStorage.getItem(MAC_DRAW_GLOBAL_KEY) && !localStorage.getItem(sk('lastDraw')), {lastDraw:lastDraw,global:!!localStorage.getItem(MAC_DRAW_GLOBAL_KEY),local:!!localStorage.getItem(sk('lastDraw'))});

// 10. 历史归档要存“自留盘”：总盘扣飞走、加上家赔回
lastDraw={period:'323',regularNums:[1,2,3,11,22,33],specialNum:10};
orders=[{id:'own-arch',customer:'散客',raw:'平特龙10 三中三 11.22.33组5',amount:15,codes:['平特龙','三中三:11,22,33'],codeAmts:{'平特龙':10,'三中三:11,22,33':5},createdAt:'2026/11/20 15:02:30'}];
hkOrders=[];
pays=[{product:'自动结算',amount:20,note:'平特龙×2'}];
custpays=[];
flownPerPos={'平特龙':10};
flownReal={};
const _archDay=billBookDate()||billToday();
const _archSaved=billArchiveNow(true);
const _arch=billArchive[_archDay]||{};
const _archOwn=billOwnFigures(_arch.sum||{},_arch.own);
ck('历史归档保存自留盘', _archSaved && _arch.own && Math.abs(Number(_arch.own.flyOut)-10)<0.01 && Math.abs(Number(_arch.own.flyBack)-20)<0.01 && _archOwn && Math.abs(_archOwn.net-5)<0.01, {saved:_archSaved,own:_arch.own,fig:_archOwn,sum:_arch.sum});

// 11. 历史账单页面要能看到总盘/自留两行
billOpenHistory();
const _histTxt=(document.getElementById('billHistMask')||{}).innerText||'';
ck('历史账单显示总盘与自留', _histTxt.indexOf('总盘')>=0 && _histTxt.indexOf('自留')>=0 && _histTxt.indexOf('上家赔回')>=0, _histTxt.slice(0,180));
billCloseHistory();

// 12. 失败诊断：脱敏、原文、完整输入
const _oldRoster=(typeof roster!=='undefined'&&Array.isArray(roster))?roster.slice():[];
try{
  roster=['张三','叶','龙'];
  ck('诊断脱敏-两字客户名', diagMaskText('张三 平特龙10')==='[客户] 平特龙10', diagMaskText('张三 平特龙10'));
  ck('诊断脱敏-单字不误抹平特龙', diagMaskText('叶 香港 平特龙 20')==='[客户] 香港 平特龙 20', diagMaskText('叶 香港 平特龙 20'));
  ck('诊断脱敏-手机号', diagMaskText('张三 13800138000')==='[客户] [手机]', diagMaskText('张三 13800138000'));
  const _db=diagBuildBatch([{idx:1,raw:'张三 各10 尾数a',msg:'无法识别：「张三」'}],[],'张三 各10 尾数a');
  ck('诊断批次含脱敏完整输入', _db.failures[0].raw.indexOf('张三')<0 && _db.failures[0].msg.indexOf('张三')<0 && _db.rawInput.indexOf('张三')<0 && _db.rawInput.indexOf('尾数a')>=0, _db);
}finally{ roster=_oldRoster; }

window.__archiveQA=out;
})();
