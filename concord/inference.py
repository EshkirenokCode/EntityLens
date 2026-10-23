import numpy as np
from concord.features import SCHEMA
def score_pairs(pairs,records,bundle):
 if bundle['schema']!=SCHEMA:raise RuntimeError('Incompatible feature schema')
 embedding={}
 if bundle['mode']=='lexical + SVD':
  ids=sorted(records);z=bundle['svd'].transform(bundle['vectorizer'].transform([(records[k]['name'] or '')+' '+(records[k]['address'] or '') for k in ids]));z/=np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-9);embedding=dict(zip(ids,z))
 x=[]
 for p in pairs:
  f=p['features'];row=f[:5]+f[6:]
  if embedding:row=row+[float(embedding[p['left']]@embedding[p['right']])]
  x.append(row)
 if not x:return
 scores=bundle['model'].predict_proba(np.array(x))[:,1]
 for p,s in zip(pairs,scores):p.update(score=float(s),model=bundle['mode'],feature_schema=SCHEMA,policy='review-only')
