import json,sys
f=sys.argv[1]
s=open(f,encoding='utf-8').read()
a=s.index('function parseLine(text){')
depth=0;i=a
while True:
    if s[i]=='{': depth+=1
    elif s[i]=='}':
        depth-=1
        if depth==0: break
    i+=1
body=s[a:i+1]
i2=s.index('return [{"code": "01"'); j=s.index(';', i2)
prods=s[i2+len('return '):j]
helpers = """
const window = {_waveChoice:'perNum'};
const NUM2ZODIAC_REV={'马':[1,13,25,37,49],'蛇':[2,14,26,38],'龙':[3,15,27,39],'兔':[4,16,28,40],'虎':[5,17,29,41],'牛':[6,18,30,42],'鼠':[7,19,31,43],'猪':[8,20,32,44],'狗':[9,21,33,45],'鸡':[10,22,34,46],'猴':[11,23,35,47],'羊':[12,24,36,48]};
const products = """ + prods + """;
function toPriceNum(x){const n=parseFloat(x);if(!isNaN(n))return n;const cn={零:0,一:1,二:2,两:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};const m=String(x).match(/(十|[一二两三四五六七八九][千百十]?[一二两三四五六七八九]?十?[一二两三四五六七八九]?)/);if(!m)return 0;const t=m[1];let v=0,p=0;while(p<t.length){const c=t[p];if(cn[c]!==undefined){v+=cn[c];p++;}else if(c==='十'){v=(v||1)*10;p++;}else if(c==='百'){v*=100;p++;}else if(c==='千'){v*=1000;p++;}else p++;}return v||0;}
"""
tests=["05-17-29-09-21-33-45各数10米","05 17 29 09 21 33 45各数10米","特5.17.29.9.21.33.45各10",
"05.17.29.09.21.33.45各10","05、17、29各10","05-17-29各10","特 05 17 29 各10","特号05 17 29 10米",
"红波10","特红波10","特红波各10","蓝波单10","绿波小单20","特单50","特双50","特大100",
"特马兔各5","平特马兔各10","马连龙兔10","连肖龙虎兔100","虎平1000",
"19 35二中二10","19 16 35三中三8","二中二19 35 10","三中三19 16 35 8",
"特5 17 29 各10 米","特05 17 29 各数10米","特特05 17 29 各10","特码05 17 29 各10"]
code = helpers + body + "\nconst tests=" + json.dumps(tests, ensure_ascii=False) + ";\nlet pass=0,fail=0;\nfor(const t of tests){try{const r=parseLine(t);if(r&&r.codes&&r.codes.length){pass++;console.log('✔ '+t+' => '+JSON.stringify(r));}else{fail++;console.log('✘ '+t+' => null');}}catch(e){fail++;console.log('✘ '+t+' => '+e.message);}}\nconsole.log('\\n通过 '+pass+' / 失败 '+fail);"
open('/tmp/_rg.js','w',encoding='utf-8').write(code)
