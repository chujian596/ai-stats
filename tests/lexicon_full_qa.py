# -*- coding: utf-8 -*-
"""词库全量对拍：客户版 vs 专业版，逐条核「识别对象 + 金额」
覆盖：49个特号、12生肖平特、12生肖各数、三波各号、波色×单双大小、头0-4、尾0-9、
大/小/单/双/合数单双、全部二连肖(66)、三连肖抽样、生肖组合、特马系列、复式。
用法：python3 tests/lexicon_full_qa.py
"""
import itertools, json, sys
from playwright.sync_api import sync_playwright

ZOD = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
# 2026 马年位序：马01起，逆生肖序每 +12
MAP = {
 '马':[1,13,25,37,49], '蛇':[2,14,26,38], '龙':[3,15,27,39], '兔':[4,16,28,40],
 '虎':[5,17,29,41], '牛':[6,18,30,42], '鼠':[7,19,31,43], '猪':[8,20,32,44],
 '狗':[9,21,33,45], '鸡':[10,22,34,46], '猴':[11,23,35,47], '羊':[12,24,36,48],
}
RED=[1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46]
BLUE=[3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48]
GREEN=[5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49]
def nn(x): return '%02d' % x
def tail_nums(d): return [x for x in range(1,50) if x%10==d]
def head_nums(h): return [x for x in range(1,50) if x//10==h]
def big(): return list(range(25,50))
def small(): return list(range(1,25))
def odd(): return [x for x in range(1,50) if x%2==1]
def even(): return [x for x in range(1,50) if x%2==0]
def hesuan_odd():
    return [x for x in range(1,50) if sum(int(c) for c in str(x))%2==1]

cases=[]  # (query, expected_codes(set or list), expected_total, note)
for i in range(1,50):
    cases.append(('特%s 10'%nn(i), [nn(i)], 10, '特号%s'%nn(i)))
for z in ZOD:
    cases.append(('平特%s10'%z, ['平特'+z], 10, '平特'+z))
for z in ZOD:
    nums=[nn(x) for x in MAP[z]]
    cases.append(('%s各数10'%z, nums, len(nums)*10, z+'各数'))
for w,name,nums in [('红波','红波',RED),('蓝波','蓝波',BLUE),('绿波','绿波',GREEN)]:
    cases.append((w+'各10', [name], 10, name+'各(聚合项)'))
    for suf in ['单','双','大','小','单大','单小','双大','双小']:
        cases.append((w+suf+'10', [name+suf], 10, name+suf+'（聚合项）'))
for h in range(0,5):
    nums=[nn(x) for x in head_nums(h)]
    cases.append(('%d头10'%h, nums, 10, '%d头'%h))
for d in range(0,10):
    nums=[nn(x) for x in tail_nums(d)]
    cases.append(('尾%d 10'%d, nums, 10, '尾%d'%d))
for word,codes,total,note in [
    ('大10',['大'],10,'大'),('小10',['小'],10,'小'),('单10',['单数'],10,'单'),
    ('双10',['双数'],10,'双'),('合数单10',['合数单'],10,'合数单'),('合数双10',['合数双'],10,'合数双')]:
    cases.append((word,codes,total,note))
for a,b in itertools.combinations(ZOD,2):
    cases.append(('连%s%s10'%(a,b), ['连肖'+a+b], 10, '二连肖'+a+b))
for combo in [('鼠','牛','虎'),('马','蛇','龙'),('猴','鸡','狗'),('猪','羊','兔')]:
    cases.append(('连%s%s%s10'%combo, ['连肖'+''.join(combo)], 10, '三连肖'+''.join(combo)))
cases.append(('平特马龙各10',['平特马','平特龙'],20,'平特组合各'))
cases.append(('平特马龙兔10',['平特马','平特龙','平特兔'],10,'平特组合共'))
for q,total,note in [('特马5',5,'特马'),('特马各5',25,'特马各'),('特马各数5',25,'特马各数'),('特马各号5',25,'特马各号'),('特马每个5',25,'特马每个')]:
    cases.append((q,None,total,note))
for q,note in [('三中三复式 04.19.37 10','三中三复式'),('二中二 04.19.37 10','二中二复式'),('三中二 04.19.37 10','三中二复式')]:
    cases.append((q,None,None,note))


def run(page_file, cases):
    out=[]
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
        pg=b.new_page(); pg.goto('http://127.0.0.1:8765/%s?nock=1&cb=lexfull'%page_file, wait_until='load'); pg.wait_for_timeout(400)
        res=pg.evaluate("""(qs)=>qs.map(function(q){try{var r=parseLine(q); var total=0; if(r&&r.codes){total = r.isPer ? Number(r.price)*r.codes.length : Number(r.price);} return {ok:true,n:r.codes.length,total:total,per:!!r.isPer,codes:r.codes};}catch(e){return {ok:false,err:e.message};}});""", [c[0] for c in cases])
        b.close()
    return res

R=[]
def chk(name, ok, detail=''):
    R.append((name, ok, detail))

for page,label in [('app-pro.html','专业版'),('app.html','客户版')]:
    res=run(page,cases)
    for (q,exp_codes,total,note),r in zip(cases,res):
        if not r['ok']:
            chk('%s %s：能识别'%(label,note), False, r.get('err')); continue
        ok=True; d={'q':q,'codes':r['codes'][:6],'n':r['n'],'total':r['total']}
        if total is not None and abs(r['total']-total)>0.02: ok=False
        if exp_codes is not None:
            cs=set(r['codes'])
            if not set(exp_codes).issubset(cs) or len(cs)!=len(set(exp_codes)): ok=False
        chk('%s %s（%s）'%(label,note,q.replace('\n','/')), ok, d)

print('总计 %d 项，通过 %d，失败 %d'%(len(R),sum(1 for x in R if x[1]),sum(1 for x in R if not x[1])))
fails=[x for x in R if not x[1]]
for f in fails[:25]: print('FAIL',f[0],str(f[2])[:100])
json.dump([{'name':n,'pass':ok,'detail':d} for n,ok,d in R], open('/tmp/lexicon_full_report.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
sys.exit(0 if not fails else 1)
