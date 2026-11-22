from pathlib import Path
import hashlib,json,ast
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed'
OUT=DATA/'hidden_meta_verified'
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def export_candidates(rules, config):
 OUT.mkdir(exist_ok=True)
 frame=rules.copy()
 for c in ['antecedents','consequents']:frame[c]=frame[c].map(lambda x:json.dumps(sorted(x)))
 frame.to_csv(OUT/'candidate_rules.csv',index=False)
 manifest={'source_sha256':digest(DATA/'tft_processed.csv'),'rules_sha256':digest(OUT/'candidate_rules.csv'),'config':config,'candidate_rules':len(frame)}
 (OUT/'candidate_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print('Exported actual candidate rules:',len(frame))
def export_communities(louvain,leiden,threshold):
 OUT.mkdir(exist_ok=True)
 (OUT/'communities.json').write_text(json.dumps({'source_sha256':digest(DATA/'tft_processed.csv'),'cooc_sha256':digest(DATA/'cooc_winrate.pkl'),'min_weight':threshold,'Louvain':{str(k):int(v) for k,v in louvain.items()},'Leiden':{str(k):int(v) for k,v in leiden.items()}},indent=2),encoding='utf-8')
def wilson_lower(w,n):
 if not n:return np.nan
 z=1.96;p=w/n
 return (p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
def measure_sets(frame,rules,communities,max_frequency=.05,min_winrate=.60,min_count=100):
 """Descriptive evaluation on ALL outcomes, not independent holdout validation."""
 teams=frame.champions.map(lambda x:set(ast.literal_eval(x)) if isinstance(x,str) else set(x))
 names=sorted(set().union(*teams))
 index={c:i for i,c in enumerate(names)}
 X=np.zeros((len(frame),len(names)),dtype=bool)
 for i,team in enumerate(teams):X[i,[index[c] for c in team]]=True
 packed={c:np.packbits(X[:,j]) for j,c in enumerate(names)}
 del X,teams
 win=frame.placement.le(4).to_numpy();win_bits=np.packbits(win)
 tiers=frame.tier.fillna('Unknown').astype(str) if 'tier' in frame else pd.Series(['Unknown']*len(frame))
 rank_bits={t:np.packbits(tiers.eq(t).to_numpy()) for t in sorted(tiers.unique())}
 rank_n=tiers.value_counts().to_dict()
 countbits=np.array([i.bit_count() for i in range(256)],dtype=np.uint8)
 def count(a):return int(countbits[a].sum())
 unique={}
 for r in rules.itertuples():
  both=r.antecedents|r.consequents
  if not all(c.startswith('Champ_') for c in both):continue
  key=tuple(sorted(c.removeprefix('Champ_') for c in both))
  if key not in unique or r.lift>unique[key].lift:unique[key]=r
 rows=[];by_rank=[]
 for team,r in unique.items():
  bits=np.zeros_like(win_bits) if any(c not in packed for c in team) else packed[team[0]].copy()
  if all(c in packed for c in team):
   for c in team[1:]:bits &= packed[c]
  n=count(bits);w=count(bits&win_bits);freq=n/len(frame);wr=w/n if n else np.nan
  flags={}
  for alg in ['Louvain','Leiden']:
   labels=[communities[alg].get(c) for c in team]
   flags['same_'+alg.lower()]=None not in labels and len(set(labels))==1
  rows.append({'champions':' | '.join(team),'size':len(team),'observations':n,'top4_count':w,'pick_rate':freq,'top4_rate':wr,'wilson_lower_95':wilson_lower(w,n),'representative_lift_win_sample':float(r.lift),'candidate':bool(n>=min_count and freq<=max_frequency and wr>=min_winrate),**flags})
  for tier,tbits in rank_bits.items():
   bn=count(bits&tbits);bw=count(bits&tbits&win_bits)
   by_rank.append({'champions':' | '.join(team),'tier':tier,'observations':bn,'top4_count':bw,'pick_rate':bn/rank_n[tier],'top4_rate':bw/bn if bn else np.nan})
 cols=['champions','size','observations','top4_count','pick_rate','top4_rate','wilson_lower_95','representative_lift_win_sample','candidate','same_louvain','same_leiden']
 result=pd.DataFrame(rows,columns=cols).sort_values(['top4_rate','observations'],ascending=False)
 return result,pd.DataFrame(by_rank)
def run_verification(max_frequency=.05,min_winrate=.60,min_count=100):
 manifest=json.loads((OUT/'candidate_manifest.json').read_text())
 communities=json.loads((OUT/'communities.json').read_text())
 source=digest(DATA/'tft_processed.csv')
 if source!=manifest['source_sha256'] or source!=communities['source_sha256']:raise RuntimeError('Data changed: rerun 05 and 07')
 if digest(OUT/'candidate_rules.csv')!=manifest['rules_sha256']:raise RuntimeError('Candidate rules changed: rerun 05')
 if digest(DATA/'cooc_winrate.pkl')!=communities['cooc_sha256']:raise RuntimeError('Graph input changed: rerun 07')
 rules=pd.read_csv(OUT/'candidate_rules.csv')
 for c in ['antecedents','consequents']:rules[c]=rules[c].map(lambda x:frozenset(json.loads(x)))
 frame=pd.read_csv(DATA/'tft_processed.csv',usecols=['champions','placement','tier'])
 result,by_rank=measure_sets(frame,rules,communities,max_frequency,min_winrate,min_count)
 candidates=result[result.candidate].copy()
 result.to_csv(OUT/'all_candidate_measurements.csv',index=False)
 candidates.to_csv(OUT/'hidden_meta_candidates.csv',index=False)
 by_rank.to_csv(OUT/'measurements_by_rank.csv',index=False)
 summary={'records':len(frame),'baseline_top4':float(frame.placement.le(4).mean()),'input_rules':len(rules),'unique_sets':len(result),'candidates':len(candidates),'max_pick_rate':max_frequency,'min_top4_rate':min_winrate,'min_observations':min_count,'graph_min_weight':communities['min_weight'],'source_sha256':source,'scope':'Descriptive full-data screening; no independent holdout; candidate subset from TV1 mining; not exhaustive discovery or causal evidence'}
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps(summary,indent=2))
 return result,candidates,by_rank
