# 广覆盖测试：用完整保存流程(doSave)跑各种真实写法，统计一次过/需确认/真失败
import sys,json,re
f=sys.argv[1]
s=open(f,encoding='utf-8').read()
def grab(pat, optional=False):
    m=re.search(pat,s)
    if not m:
        if optional: return None
        raise ValueError('未找到 '+pat)
    a=m.start();d=0;i=a
    while i<len(s):
        if s[i]=='{': d+=1
        elif s[i]=='}':
            d-=1
            if d==0: break
        i+=1
    return s[a:i+1]
doSave=grab(r'function doSave\('); parseLine=grab(r'function parseLine\(text\)')
fix=grab(r'function showFixDialog\(rawLine, msg\)', optional=True) or 'function showFixDialog(){return false;}'
i2=s.index('return [{"code": "01"')
_b=i2+s[i2:].index('['); _d=0; _k=_b
while _k<len(s):
    if s[_k]=='[': _d+=1
    elif s[_k]==']':
        _d-=1
        if _d==0: break
    _k+=1
prods=s[_b:_k+1]

pre = """
const window={}; const els={};
let _popupCount=0;
function _el(id){ if(!els[id]) els[id]={id:id,value:'',innerHTML:'',textContent:'',style:{},appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}},addEventListener:function(){}}; return els[id]; }
const document={getElementById:_el,createElement:function(){_popupCount++;return {style:{},innerHTML:'',appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}}}},body:{appendChild:function(){}},addEventListener:function(){}};
const localStorage={getItem:function(){return null;},setItem:function(){},removeItem:function(){}};
function myAlert(m){ console.log('[ALERT] '+m); } function prompt(){ return null; }
var orders=[],roster=[],storageOK=true,lastPrice=null,_texiaoChoice=null,mode='normal',pendingProduct=null;
function saveOrders(){} function saveRoster(){} function restoreIfNeeded(){} function renderAll(){} function switchTab(){} function exportBackup(){} function autoPayout(){}
const NUM2ZODIAC_REV={'马':[1,13,25,37,49],'蛇':[2,14,26,38],'龙':[3,15,27,39],'兔':[4,16,28,40],'虎':[5,17,29,41],'牛':[6,18,30,42],'鼠':[7,19,31,43],'猪':[8,20,32,44],'狗':[9,21,33,45],'鸡':[10,22,34,46],'猴':[11,23,35,47],'羊':[12,24,36,48]};
const products = """ + prods + """;
function toPriceNum(x){const n=parseFloat(x);if(!isNaN(n))return n;const cn={零:0,一:1,二:2,两:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};const m=String(x).match(/(十|[一二两三四五六七八九][千百十]?[一二两三四五六七八九]?十?[一二两三四五六七八九]?)/);if(!m)return 0;const t=m[1];let v=0,p=0;while(p<t.length){const c=t[p];if(cn[c]!==undefined){v+=cn[c];p++;}else if(c==='十'){v=(v||1)*10;p++;}else if(c==='百'){v*=100;p++;}else if(c==='千'){v*=1000;p++;}else p++;}return v||0;}
"""

CASES = [
 # 号码类：各种分隔符
 ("点分隔+各数", "05.17.29.09.21.33.45各数10米"),
 ("横杠+特", "特05-17-29-09-21-33-45各10米"),
 ("空格分隔", "05 17 29 09 21 33 45 各10米"),
 ("顿号分隔", "05、17、29各10"),
 ("斜杠分隔", "05/17/29各10"),
 ("逗号分隔", "05,17,29各10"),
 ("两个号", "05 17各10"),
 ("单个号", "特05各10"),
 ("带标题+汇总", "澳特：\n05-17-29-09-21-33-45各数10米\n共70米"),
 ("三组重复", "05-17-29-09-21-33-45各数10米\n05-17-29-09-21-33-45各数10米\n05-17-29-09-21-33-45各数10米"),
 ("一行两注", "05 17各10，21 33各5"),
 ("中文金额", "05 17 29各十米"),
 ("元单位", "05 17 29各10元"),
 ("块单位", "05 17 29各10块"),
 # 生肖类
 ("特肖各", "特马兔各5米"),
 ("平特肖各", "平特马兔各10"),
 ("多肖三个", "特马兔狗各10"),
 ("裸肖各(需确认)", "马兔各5"),
 ("单肖", "特马各10"),
 # 连肖
 ("X连YZ", "马连龙兔10块"),
 ("连肖二", "连肖龙虎兔100"),
 ("三连肖", "龙虎兔三连肖100"),
 ("平连", "平连龙虎100"),
 # 中特
 ("二中二", "19 35二中二10"),
 ("三中三", "19 16 35三中三8"),
 # 波色类
 ("纯波色", "红波10"),
 ("波色+特前缀", "特红波10"),
 ("波色单", "蓝波单10"),
 ("波色大", "蓝波大5块"),
 ("波色小单", "绿波小单20块"),
 ("波色单大", "蓝波单大10"),
 ("合数单", "合数单10"),
 ("裸单", "特单50"),
 ("裸双", "特双50"),
 ("大", "特大100"),
 # 混合
 ("号码+生肖两行", "05 17 29各10\n特马兔各5"),
 ("三行混合", "05 17 29各10\n特马兔各5\n19 35二中二10"),
 ("带共字行", "05 17 29各10\n共30米"),
 # ===== 金额断言：不该弹的必须直接算对 =====
 ("断言-平特单肖", "平特马80", 80),
 ("断言-单号", "05 10", 10),
 ("断言-连肖", "连马龙兔10", 10),
 ("断言-二中二", "02 15二中二10", 10),
 ("断言-三中三", "19 16 35三中三8", 8),
 ("断言-特马各5", "特马各5", 25),
 ("断言-特马各数5", "特马各数5", 25),
 ("断言-特马各号5", "特马各号5", 25),
 ("断言-特马每个5", "特马每个5", 25),
 ("断言-狗各数5", "狗各数5", 20),
 ("断言-09各5", "09各5", 5),
 ("断言-平龙马各号5", "平龙马各号5", 10),
 ("断言-平特一肖猴", "平特一肖猴200", 200),
 ("断言-平特肖兔", "平特肖兔100", 100),
 ("断言-特猴各50", "特猴各50", 200),
 ("断言-特猴各5+平特一肖", "特猴各50\n平特一肖猴200", 400),

]

runner = pre + parseLine + "\n" + fix + "\n" + doSave + "\n" + """
const CASES = """ + json.dumps(CASES, ensure_ascii=False) + """;
let ok=0, needConfirm=0, fail=0;
for(const [name, text, expAmt] of CASES){
  orders=[]; _popupCount=0; _texiaoChoice=null; window._waveChoice=null; window._failedLines=[];
  let alertMsg='';
  const _origAlert = myAlert; myAlert = function(m){ alertMsg=m; };
  _el('input').value = text;
  let threw=null;
  try{ doSave(); }catch(e){ threw=e.message; }
  myAlert = _origAlert;
  if(orders.length > 0 && expAmt !== undefined && Math.abs(orders.reduce(function(a,o){return a+o.amount;},0) - expAmt) > 0.01){
    fail++; console.log('❌ '+name+' ⇒ 金额不符：期望 '+expAmt+'，实得 '+orders.reduce(function(a,o){return a+o.amount;},0));
  } else if(orders.length > 0){
    ok++; console.log('✅ '+name+' ⇒ '+orders.length+'单 共'+orders[0].amount+'米 '+orders[0].qty+'号'+(expAmt!==undefined?'（期望 '+expAmt+' ✓）':''));
  } else if(_popupCount > 0){
    needConfirm++; console.log('🟡 '+name+' ⇒ 弹窗需确认（正常流程）');
  } else {
    fail++; console.log('❌ '+name+' ⇒ '+(alertMsg||threw||'无输出'));
  }
}
console.log('\\n结果：一次过 '+ok+' / 需确认 '+needConfirm+' / 失败 '+fail+'（共'+CASES.length+'）');
"""
open('/tmp/_cov.js','w',encoding='utf-8').write(runner)
