# 无头跑完整 doSave(预处理→parseLine→订单)，验证真实写法能否录入
# 用法: python3 full_save_check.py <页面文件> <文本文件|->
import sys,json,re
f=sys.argv[1]
text=open(sys.argv[2],encoding='utf-8').read() if len(sys.argv)>2 and sys.argv[2]!='-' else sys.stdin.read()
s=open(f,encoding='utf-8').read()

def grab(pat, optional=False):
    m=re.search(pat, s)
    if not m:
        if optional: return None
        raise ValueError('未找到 '+pat)
    a=m.start(); d=0; i=a
    while i<len(s):
        if s[i]=='{': d+=1
        elif s[i]=='}':
            d-=1
            if d==0: break
        i+=1
    return s[a:i+1]

doSave=grab(r'function doSave\(')
parseLine=grab(r'function parseLine\(text\)')
fix=grab(r'function showFixDialog\(rawLine, msg\)', optional=True) or 'function showFixDialog(){ return false; }'

i2=s.index('return [{"code": "01"'); j=s.index(';', i2); prods=s[i2+len('return '):j]

pre = """
const window={}; const els={};
function _el(id){ if(!els[id]) els[id]={id:id,value:'',innerHTML:'',textContent:'',style:{},appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}},addEventListener:function(){}}; return els[id]; }
const document={getElementById:_el,createElement:function(){return {style:{},innerHTML:'',appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}}}},body:{appendChild:function(){}},addEventListener:function(){}};
const localStorage={getItem:function(){return null;},setItem:function(){},removeItem:function(){}};
function myAlert(m){ console.log('[ALERT] '+m); } function prompt(){ return null; }
var orders=[],roster=[],storageOK=true,lastPrice=null,_texiaoChoice=null,mode='normal',pendingProduct=null;
function saveOrders(){} function saveRoster(){} function restoreIfNeeded(){} function renderAll(){} function switchTab(){} function exportBackup(){} function autoPayout(){}
const NUM2ZODIAC_REV={'马':[1,13,25,37,49],'蛇':[2,14,26,38],'龙':[3,15,27,39],'兔':[4,16,28,40],'虎':[5,17,29,41],'牛':[6,18,30,42],'鼠':[7,19,31,43],'猪':[8,20,32,44],'狗':[9,21,33,45],'鸡':[10,22,34,46],'猴':[11,23,35,47],'羊':[12,24,36,48]};
const products = """ + prods + """;
function toPriceNum(x){const n=parseFloat(x);if(!isNaN(n))return n;const cn={零:0,一:1,二:2,两:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};const m=String(x).match(/(十|[一二两三四五六七八九][千百十]?[一二两三四五六七八九]?十?[一二两三四五六七八九]?)/);if(!m)return 0;const t=m[1];let v=0,p=0;while(p<t.length){const c=t[p];if(cn[c]!==undefined){v+=cn[c];p++;}else if(c==='十'){v=(v||1)*10;p++;}else if(c==='百'){v*=100;p++;}else if(c==='千'){v*=1000;p++;}else p++;}return v||0;}
"""
runner = pre + parseLine + "\n" + fix + "\n" + doSave + "\n" + """
_el('input').value = """ + json.dumps(text, ensure_ascii=False) + """;
doSave();
console.log('订单数:', orders.length);
orders.forEach(function(o,n){ console.log('  单'+(n+1)+' 金额'+o.amount+' 号码数'+o.qty+' codes='+o.codes.join(',')); });
"""
open('/tmp/_full.js','w',encoding='utf-8').write(runner)
