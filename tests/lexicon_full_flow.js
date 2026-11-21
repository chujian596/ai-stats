/* 全词库 + 港澳混搭 + 金额/号码/命中/落库 全流程回归
   浏览器执行（app-pro.html），结果 JSON。 */
(async()=>{
const R={version:(typeof APP_VER!=='undefined'?APP_VER:'?'),cases:[],fails:[],summary:{}};
window.prompt=function(){return null;};
window.confirm=function(){return true;};
window.myAlert=function(m){window.__qaAlerts=(window.__qaAlerts||[]).concat(String(m));};
window.myConfirm=function(m,fn){if(fn)fn();};
window.myChoice=function(m,t,opts,cb){if(cb&&opts&&opts.length)cb(0);};
window.__skipAmbig=true; window.__dupConfirmed=true; window.__ambigAbort=false;
window._texiaoChoice='perZod'; window._waveChoice=null; window._waveCanonical=null;
window.PARSE_DEFAULTS={waveAmount:'perNum',teZod:'perZod',pingZod:'perZod',bareNumAmount:'perNum'};
function reset(){
  try{localStorage.clear();}catch(e){}
  try{localStorage.setItem('ai_preview_enabled','0');}catch(e){}
  try{localStorage.setItem('hk_draw_cache_global',JSON.stringify({draw:'123',nums:[49,32,18,12,47,45,41],at:'2026-11-19 21:32'}));}catch(e){}
  shop='A'; orders=[]; hkOrders=[]; window.__qaAlerts=[]; window.__ambigAbort=false; window.__skipAmbig=true; window.__dupConfirmed=true;
  window._texiaoChoice='perZod'; window._waveChoice=null; window._waveCanonical=null;
  var c=document.getElementById('customerName'); if(c)c.value='测试';
}
function flat(list){var out=[];(list||[]).forEach(o=>(o.codes||[]).forEach(c=>out.push(c)));return out;}
function add(name,text,exp,opt){
  opt=opt||{}; reset(); if(opt.shop) shop=opt.shop;
  var ta=document.getElementById('input'); if(ta)ta.value=text;
  var err='';
  try{ doSave(); }catch(e){ err=e.message||String(e); }
  var _pick=opt.pick||opt.pickOptional;
  if(_pick){
    var _ov=document.querySelector('.ai-ov');
    if(_ov){
      var _btns=Array.from(_ov.querySelectorAll('button'));
      var _b=_btns.find(function(b){return (b.innerText||'').indexOf(_pick)>=0;});
      if(_b){ _b.click(); } else if(opt.pick){ err=(err?err+'；':'')+'弹窗未找到按钮'+_pick+':'+_btns.map(function(b){return b.innerText;}).join('|'); }
    } else if(opt.pick){ err=(err?err+'；':'')+'未出现弹窗'; }
  }
  var macAmt=orders.reduce((s,o)=>s+Number(o.amount||0),0);
  var hkAmt=hkOrders.reduce((s,o)=>s+Number(o.amount||0),0);
  var got={mac:orders.length,hk:hkOrders.length,macAmt:macAmt,hkAmt:hkAmt,macCodes:flat(orders),hkCodes:flat(hkOrders),alerts:(window.__qaAlerts||[]).slice()};
  var f=[];
  if(err)f.push('抛错:'+err);
  var badAlert=got.alerts.filter(a=>/无法识别|没找到|本批未保存|请先粘贴|不完整|失败/.test(a));
  if(badAlert.length)f.push('异常提示:'+badAlert.join('|'));
  if((exp.mac||0)!==got.macAmt)f.push('澳门金额 '+got.macAmt+' ≠ '+exp.mac);
  if((exp.hk||0)!==got.hkAmt)f.push('香港金额 '+got.hkAmt+' ≠ '+exp.hk);
  if(exp.macCount!==undefined && exp.macCount!==got.mac)f.push('澳门单数 '+got.mac+' ≠ '+exp.macCount);
  if(exp.hkCount!==undefined && exp.hkCount!==got.hk)f.push('香港单数 '+got.hk+' ≠ '+exp.hkCount);
  if(exp.macCodes && JSON.stringify(exp.macCodes)!==JSON.stringify(got.macCodes))f.push('澳门号码 '+got.macCodes.join(',')+' ≠ '+exp.macCodes.join(','));
  if(exp.hkCodes && JSON.stringify(exp.hkCodes)!==JSON.stringify(got.hkCodes))f.push('香港号码 '+got.hkCodes.join(',')+' ≠ '+exp.hkCodes.join(','));
  R.cases.push({name,text,expect:exp,got,status:f.length?'FAIL':'PASS',fails:f});
  if(f.length)R.fails.push(name+'：'+f.join('；'));
}
const Z={马:[1,13,25,37,49],蛇:[2,14,26,38],龙:[3,15,27,39],兔:[4,16,28,40],虎:[5,17,29,41],牛:[6,18,30,42],鼠:[7,19,31,43],猪:[8,20,32,44],狗:[9,21,33,45],鸡:[10,22,34,46],猴:[11,23,35,47],羊:[12,24,36,48]};
const pad=a=>a.map(n=>String(n).padStart(2,'0'));
// 号码/生肖/平特/连肖
add('号码单','05 10',{mac:10,macCodes:['05']});
add('号码逗号各','05,17,29各10',{mac:30,macCodes:['05','17','29']});
add('特号多号各','特号05 17 29 各10',{mac:30,macCodes:['05','17','29']});
add('裸马','马10',{mac:10,macCodes:pad(Z.马)});
add('裸兔','兔50',{mac:50,macCodes:pad(Z.兔)});
add('平特马','平特马100',{mac:100,macCodes:['平特马']});
add('平马','平马100',{mac:100,macCodes:['平特马']});
add('平牛','平牛100',{mac:100,macCodes:['平特牛']});
add('虎平','虎平100',{mac:100,macCodes:['平特虎']});
// 平特多肖需弹窗选算法，单独在弹窗用例验证
// add('平特马龙兔各','平特马龙兔各100',{mac:300,macCodes:['平特马','平特龙','平特兔']});
// add('马龙兔平特肖','马龙兔平特肖100',{mac:300,macCodes:['平特马','平特龙','平特兔']});
add('连肖二','连肖龙虎100',{mac:100,macCodes:['连肖龙虎']});
add('连肖三','连肖龙虎兔100',{mac:100,macCodes:['连肖龙虎兔']});
add('三连肖词序','龙虎兔三连肖100',{mac:100,macCodes:['连肖龙虎兔']});
add('连肖空格','连肖龙 虎 兔100',{mac:100,macCodes:['连肖龙虎兔']});
// 组合
add('二中二','二中二03,10 100',{mac:100,macCodes:['二中二:03,10']});
add('二中二词在后','19 35二中二10',{mac:10,macCodes:['二中二:19,35']});
add('三中二','三中二03,10,22 100',{mac:100,macCodes:['三中二:03,10,22']});
add('三中三','三中三07,24,32 100',{mac:100,macCodes:['三中三:07,24,32']});
add('三中三横杠','07-24-32三中三100',{mac:100,macCodes:['三中三:07,24,32']});
add('三中三复式','三中三复式01.02.03.04.05.06.07各50',{mac:1750});
add('三中三复式词尾','02，38，13，37，08，20各5三中三复式',{mac:100,macCount:1});
add('三中二复式词尾','02，38，13，37，08，20各5三中二复式',{mac:100,macCount:1});
add('二中二复式词尾','02，38，13，37，08，20各5二中二复式',{mac:75,macCount:1});
// 波色/合数/单双/大小/头尾
add('红波各','红波各10',{mac:170},{pick:'每号'});
add('红波单各','红波单各10',{mac:80},{pick:'每号'});
add('蓝波双各','蓝波双各10',{mac:80},{pick:'每号'});
add('绿波小单各','绿波小单各20',{mac:80});
add('绿波单小各','绿波单小各20',{mac:80});
add('合数单各','合数单各10',{mac:250});
add('合数双各','合数双各10',{mac:240});
add('单数各','单数各10',{mac:250});
add('双数各','双数各10',{mac:240});
add('大各','大各10',{mac:250});
add('小各','小各10',{mac:240});
add('小双各5','小双各5',{mac:60,macCount:1,macCodes:['02','04','06','08','10','12','14','16','18','20','22','24']});
add('大双各5','大双各5',{mac:60,macCount:1});
add('小单各5','小单各5',{mac:60,macCount:1});
add('大单各5','大单各5',{mac:65,macCount:1});
add('头0各','头0各100',{mac:900});
add('尾5各','尾5各100',{mac:500});
add('0头各','0头各100',{mac:900});
add('0尾各','0尾各100',{mac:400});
add('特头0各','特头0各100',{mac:900});
add('特尾5各','特尾5各100',{mac:500});
add('多头范围','头1-4各100',{mac:4000});
// 多肖/各数
add('特肖各数','特肖 龙虎兔各数100',{mac:1200});
add('特肖每肖','特肖 龙虎兔每肖100',{mac:300});
add('特肖每位','特肖 龙虎兔每位100',{mac:1200});
add('猪羊鼠各数','猪羊鼠各数5',{mac:60});
// 混搭
add('分号混搭','11 100；三中二03,10,22 100',{mac:200});
add('空格混搭','07 100 平特鼠100 连肖鼠猪100 三中三07,24,32 100',{mac:400});
add('三玩法混搭','特号01.02.03.04各100；二中二03,10 50；三中三07,24,32 30',{mac:480});
// 18,30,42 20 无「各」会弹「共20/各20」，单独在弹窗用例验证
add('号码组各','18,30,42各20',{mac:60});
// 港澳前缀/行尾/分段
add('香港单行前缀','香港牛50',{hk:50,hkCodes:['06','18','30','42']});
add('香港前缀连段','香港牛50\n06各50\n18,30,42各20',{hk:160});
add('行尾澳门','平牛100澳门',{mac:100,macCodes:['平特牛']});
add('澳门香港双段','澳门：\n42 40 44三中三 5\n22 34 46 各10\n香港：\n25 29 27三中三 5\n40 28 16 各5',{mac:35,hk:20,macCount:1,hkCount:1});
add('香港标题无冒号','香港\n40 28 16 各5\n03 39 15 各10\n43 19 各5',{hk:55,hkCount:1});
add('澳门切回','香港：\n41 50\n澳门：\n18 10',{mac:10,hk:50,macCount:1,hkCount:1});
add('香港店默认港','特05 10',{hk:10,hkCount:1}, {shop:'B'});
add('香港店澳门标题','澳门：\n特05 10',{mac:10,macCount:1}, {shop:'B'});
// ===== 全词库系统扫描：所有非单号产品词 + 12生肖/12平特 + 全部头尾 =====
const ZOD_NAMES=['马','蛇','龙','兔','虎','牛','鼠','猪','狗','鸡','猴','羊'];
ZOD_NAMES.forEach(function(z){ add('生肖全:'+z, z+'10', {mac:10,macCodes:pad(Z[z])}); });
ZOD_NAMES.forEach(function(z){ add('平特全:'+z, '平特'+z+'100', {mac:100,macCodes:['平特'+z]}); });
products.filter(function(p){
  return !/^\d{2}$/.test(p.code) && !p.single && (p.links||[]).length>1 && ZOD_NAMES.indexOf(p.code)<0;
}).forEach(function(p){
  add('产品全:'+p.code, p.code+'各10', {mac:(p.links||[]).length*10,macCount:1}, {pickOptional:'每号'});
});
for(var _h=0;_h<=4;_h++){
  (function(h){
    var cnt=0; for(var n=1;n<=49;n++){ if(Math.floor(n/10)===h) cnt++; }
    add('头全:'+h, '头'+h+'各10', {mac:cnt*10,macCount:1});
  })(_h);
}
for(var _t=0;_t<=9;_t++){
  (function(t){
    var cnt=0; for(var n=1;n<=49;n++){ if(n%10===t) cnt++; }
    add('尾全:'+t, '尾'+t+'各10', {mac:cnt*10,macCount:1});
  })(_t);
}
// 港澳同词对照：同一产品在澳门店与香港店金额、单数应一致
[
 ['红波各10',170],['绿波小单各10',40],['头0各10',90],['尾5各10',50],
 ['马10',10],['平特马100',100],['三中三07,24,32 100',100],['连肖龙虎100',100]
].forEach(function(pair){
  add('澳门对照:'+pair[0], pair[0], {mac:pair[1],macCount:1}, {pickOptional:'每号'});
  add('香港对照:'+pair[0], pair[0], {hk:pair[1],hkCount:1}, {shop:'B',pickOptional:'每号'});
});
// 客户合并/命中/落库
reset();
var ta=document.getElementById('input'); if(ta)ta.value='澳门：\n18 10\n香港：\n41 50';
var c=document.getElementById('customerName'); if(c)c.value='叶';
var e1=''; try{doSave();}catch(e){e1=e.message;}
var macAmt=orders.reduce((s,o)=>s+Number(o.amount||0),0), hkAmt=hkOrders.reduce((s,o)=>s+Number(o.amount||0),0);
var hp=null, hd=null; try{hd=hkDrawObj();hp=hkPayoutInfo();}catch(e){}
var f=[];
if(e1)f.push('抛错:'+e1);
if(macAmt!==10)f.push('澳门金额 '+macAmt);
if(hkAmt!==50)f.push('香港金额 '+hkAmt);
if(!hd||hd.specialNum!==41)f.push('香港开奖对象异常');
if(!hp||hp.pay!==2350)f.push('香港赔付 '+JSON.stringify(hp));
try{renderOrdersList();}catch(e){f.push('列表渲染:'+e.message);}
var listText=document.getElementById('ordersList')?document.getElementById('ordersList').innerText:'';
if(listText.indexOf('2350')<0)f.push('列表未显示2350');
if(listText.indexOf('港1')<0)f.push('列表未显示港单数');
if(listText.indexOf('澳门单目录')<0||listText.indexOf('香港单目录')<0)f.push('明细未分目录');
R.cases.push({name:'同客户港澳合并+命中+落库',expect:{mac:10,hk:50,pay:2350},got:{macAmt,hkAmt,pay:hp&&hp.pay,list:listText.slice(0,300)},status:f.length?'FAIL':'PASS',fails:f});
if(f.length)R.fails.push('同客户港澳合并+命中+落库：'+f.join('；'));
// 落库重读
try{
  var lm=loadOrders().length, lh=loadHKOrders().length;
  R.cases.push({name:'刷新后落库',status:(lm===1&&lh===1)?'PASS':'FAIL',got:{mac:lm,hk:lh},fails:(lm===1&&lh===1)?[]:['落库数量不符']});
  if(lm!==1||lh!==1)R.fails.push('刷新后落库：'+lm+'/'+lh);
}catch(e){R.fails.push('落库异常:'+e.message);}
R.summary={total:R.cases.length,pass:R.cases.filter(c=>c.status==='PASS').length,fail:R.fails.length};
return R;
})();
