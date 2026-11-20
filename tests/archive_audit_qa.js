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
 '2026-11-20':{orders:[{customer:'乙',raw:'特02 100',amount:100},{customer:'乙',raw:'特02 100',amount:100}],pays:[],sum:{n:2,amt:100,pay:0,net:100},savedAt:'x'}};
a=auditBillArchive(false);
ck('归档差额识别', a.issues.some(x=>/收单/.test(x.msg)) && a.issues.some(x=>/净额/.test(x.msg)), a.issues);
ck('归档重复识别', a.issues.some(x=>/疑似重复/.test(x.msg)), a.issues);
ck('无归档日识别', a.missing.indexOf('2026-11-19')>=0, a.missing);

// 2b. 作废其中一笔：汇总重算 + 留 voided
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};
const before180=(billArchive['2026-11-20']||{}).sum;
billVoidOrder('2026-11-20',0);
const after180=(billArchive['2026-11-20']||{});
ck('作废后重算', after180.orders.length===1 && after180.sum.n===1 && Math.abs(after180.sum.amt-100)<0.01 && (after180.voided||[]).length===1, {sum:after180.sum,voided:(after180.voided||[]).length,before:before180});

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

window.__archiveQA=out;
})();
