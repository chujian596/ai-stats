#!/usr/bin/env python3
# 站点真实成绩：只取 316 期以后有本地快照的台账，按站/维度汇总。
# 输出 data/site-performance.json，供 sources.html「成绩」页读取。
import json, math, os
from datetime import datetime
from collections import defaultdict

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(ROOT,'data')
START=316

DIMS=[
 ('kill3','杀三肖',0.75,'3肖/12肖 = 75%'),
 ('max-zodiac','九肖',0.75,'9肖/12肖 = 75%'),
 ('pingte','平特',7/12,'7肖/12肖 ≈ 58.3%'),
 ('wave','波色',0.66,'2波覆盖约 65–67%'),
 ('tail','尾数',None,'尾数位数结构不同，仅观察'),
 ('head','头数',None,'头数位数结构不同，仅观察'),
 ('size','大小',0.50,'25–49 为大，1–24 为小'),
 ('parity','单双',0.50,'奇数为单，偶数为双'),
]

def wilson(k,n,z=1.96):
    if n<=0: return None,None
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return max(0.0,center-half), min(1.0,center+half)

def load_registry():
    try:
        reg=json.load(open(os.path.join(DATA,'source-registry.json'),encoding='utf-8'))
        by={s.get('siteId'):s for s in reg.get('sites',[]) if s.get('siteId')}
        return by
    except Exception:
        return {}

def reg_site(sid,by):
    if sid in by: return by[sid]
    # 聚合站台账写作 bdmijg:bdmijg-64，名单写作 bdmijg:js-64：按系统+末段编号兜底。
    if ':' in sid:
        sysp,code=sid.split(':',1); code=code.split('-')[-1]
        for k,v in by.items():
            if k.startswith(sysp+':') and k.split(':')[-1].split('-')[-1]==code:
                return v
    return {}

def main():
    reg=load_registry()
    now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out={}
    latest=0
    for fn,label,base,note in DIMS:
        path=os.path.join(DATA,f'{fn}-ledger.json')
        if not os.path.exists(path): continue
        d=json.load(open(path,encoding='utf-8'))
        window=defaultdict(lambda:{'n':0,'h':0,'last':[]})
        full=defaultdict(lambda:{'n':0,'h':0})
        for per,p in d.get('periods',{}).items():
            try: pi=int(per)
            except Exception: continue
            latest=max(latest,pi)
            for key,v in p.get('stations',{}).items():
                if v.get('hit') is None: continue
                sid=v.get('siteId') or key
                full[sid]['n']+=1; full[sid]['h']+=bool(v['hit'])
                if pi>=START:
                    r=window[sid]; r['n']+=1; r['h']+=bool(v['hit']); r['last'].append((pi,bool(v['hit'])))
                    if not r.get('name'):
                        r['name']=v.get('displayName') or v.get('siteName') or key
        sites=[]
        total_h=total_n=0
        for sid,r in window.items():
            total_n+=r['n']; total_h+=r['h']
            name=reg_site(sid,reg).get('name') or r.get('name') or sid
            f=full[sid]
            lo,hi=wilson(r['h'],r['n'])
            tier='full' if r['n']>=9 else ('watch' if r['n']>=6 else 'short')
            sites.append({
                'siteId':sid,'name':name,'system':reg_site(sid,reg).get('system'),
                'coreKill':bool(reg_site(sid,reg).get('coreKill')),
                'n':r['n'],'hits':r['h'],'rate':round(r['h']/r['n'],4) if r['n'] else None,
                'lastN':r['n'],'lastHits':r['h'],'lastRate':round(r['h']/r['n'],4) if r['n'] else None,
                'ciLow':round(lo,4) if lo is not None else None,
                'ciHigh':round(hi,4) if hi is not None else None,
                'sampleTier':tier,
                'fullN':f['n'],'fullHits':f['h'],'fullRate':round(f['h']/f['n'],4) if f['n'] else None,
                'fullTier':'long' if f['n']>=20 else ('watch' if f['n']>=9 else 'short'),
            })
        sites.sort(key=lambda x:(-(x['rate'] or 0),-x['n'],x['name']))
        out[fn]={
            'label':label,'baseline':base,'baselineNote':note,
            'overall':{'n':total_n,'hits':total_h,'rate':round(total_h/total_n,4) if total_n else None},
            'sites':sites,
        }
    doc={
        'schema':'site-performance/v1',
        'generatedAt':now,
        'dataThrough':latest,
        'window':{'from':START,'to':latest,'nPeriods':latest-START+1},
        'note':'316 期起有本地快照；293–315 无快照回填，不纳入。成绩为历史统计，不代表未来。',
        'dimensions':out,
    }
    os.makedirs(DATA,exist_ok=True)
    with open(os.path.join(DATA,'site-performance.json'),'w',encoding='utf-8') as f:
        json.dump(doc,f,ensure_ascii=False,indent=1)
    print(f"PERF_OK through={latest} dims={len(out)} sites=" + ','.join(f"{k}:{len(v['sites'])}" for k,v in out.items()))

if __name__=='__main__': main()
