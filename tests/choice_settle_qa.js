/* 金额算法「需确认」项：真实点选项 + 落单 + 账单合计对账
   覆盖 coverage_check.py 中 23 个弹窗用例的全部分支（取消除外）。
   页面执行后把结果写到 window.__choiceQA。 */
(async()=>{
const WAIT=ms=>new Promise(r=>setTimeout(r,ms));
try{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}catch(e){}
window.__previewConfirmed=true; window.__dupConfirmed=true;
window.myAlert=m=>{window.__al=(window.__al||[]).concat(String(m));};
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};
const cases=[
['特肖各','特马兔各5米',['mzA','mzB','mzC'],0],
['平特肖各','平特马兔各10',['mzA','mzB','mzC'],0],
['多肖三个','特马兔狗各10',['mzA','mzB','mzC'],0],
['裸肖各(需确认)','马兔各5',['mzA','mzB','mzC'],0],
['中文金额-特肖','特马龙兔各一百',['mzA','mzB','mzC'],0],
['大写金额-特肖','特马龙兔各壹佰',['mzA','mzB','mzC'],0],
['中文金额-平特','平特马龙兔各一百',['mzA','mzB','mzC'],0],
['中文金额-波色','红波一百',['mzB','mzC'],0],
['纯波色','红波10',['mzB','mzC'],0],
['波色+特前缀','特红波10',['wvA','wvB'],0],
['波色单','蓝波单10',['mzB','mzC'],0],
['波色大','蓝波大5块',['mzB','mzC'],0],
['波色小单','绿波小单20块',['wvA','wvB'],0],
['波色单大','蓝波单大10',['wvA','wvB'],0],
['合数单','合数单10',['wvA','wvB'],0],
['裸单','特单50',['wvA','wvB'],0],
['裸双','特双50',['wvA','wvB'],0],
['大','特大100',['wvA','wvB'],0],
['号码+生肖两行','05 17 29各10\n特马兔各5',['mzA','mzB','mzC'],30],
['三行混合','05 17 29各10\n特马兔各5\n19 35二中二10',['mzA','mzB','mzC'],40],
['歧义-特肖各','特肖 龙虎兔各100',['txA','txB'],0],
['歧义-特肖每','特肖 龙虎兔每100',['txA','txB'],0],
['歧义-特肖各中文','特肖 龙虎兔各一百',['txA','txB'],0]
];
function money(label){
  let m=label.match(/总额([0-9]+(?:\.[0-9]+)?)/); if(m)return +m[1];
  m=label.match(/=([0-9]+(?:\.[0-9]+)?)元?/); if(m)return +m[1];
  m=label.match(/共([0-9]+(?:\.[0-9]+)?)元/); if(m)return +m[1];
  m=label.match(/([0-9]+(?:\.[0-9]+)?)元/); if(m)return +m[1];
  return NaN;
}
function reset(i){
  try{orders=[];hkOrders=[];shop='A';window.__lastSavedOrderId=null;window.__al=[];window.__failedLines=[];}catch(e){}
  document.querySelectorAll('.ai-ov').forEach(x=>x.remove());
  const cn=document.getElementById('customerName'); if(cn)cn.value='Q'+i;
  const sm=document.getElementById('saveMsg'); if(sm)sm.innerHTML='';
}
const results=[], fails=[];
let tested=0;
for(let ci=0;ci<cases.length;ci++){
 const [name,txt,opts,base]=cases[ci];
 for(const oid of opts){
  reset(ci);
  const inp=document.getElementById('input'); inp.value=txt;
  let err='';
  try{doSave();}catch(e){err=e.message||String(e);}
  await WAIT(180);
  const ov=document.querySelector('.ai-ov');
  if(!ov){fails.push({name,oid,why:'无弹窗',err,msg:document.getElementById('saveMsg').innerText.slice(0,60)});continue;}
  const btn=ov.querySelector('#'+oid);
  if(!btn){fails.push({name,oid,why:'找不到选项',txt:ov.innerText.replace(/\s+/g,' ').slice(0,100)});continue;}
  const label=btn.innerText.trim(), selAmt=money(label), exp=base+selAmt;
  btn.click();
  await WAIT(380);
  const left=document.querySelector('.ai-ov'); if(left) left.remove();
  orders=orders||[];hkOrders=hkOrders||[];
  const n=(orders.length||0)+(hkOrders.length||0);
  const sum=[...orders,...hkOrders].reduce((s,o)=>s+Number(o.amount||0),0);
  const msg=(document.getElementById('saveMsg')||{}).innerText||'';
  const okN=n>0, okAmt=Math.abs(sum-exp)<0.02, okMsg=msg.indexOf(exp.toFixed(2))>=0, okAlert=!(window.__al||[]).length;
  tested++;
  const row={name,oid,label,exp:+exp.toFixed(2),got:+sum.toFixed(2),n,msg:msg.slice(0,50),status:(okN&&okAmt&&okMsg&&okAlert)?'PASS':'FAIL'};
  if(row.status!=='PASS'){row.why=[!okN&&'未落单',!okAmt&&'金额不符',!okMsg&&'账单合计不显示',!okAlert&&'有告警:'+window.__al.join('|')].filter(Boolean).join('；');fails.push(row);}
  results.push(row);
 }
}
window.__choiceQA={tested,pass:results.filter(r=>r.status==='PASS').length,fail:fails.length,fails:fails.slice(0,10),results};
})();
