"""Acquire bounded immutable public-source snapshots."""
import hashlib,json,datetime,pathlib,urllib.request,urllib.parse,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; RAW.mkdir(parents=True,exist_ok=True)
BOX=(-74.012,40.710,-73.985,40.730)
def manifest(source,path,url,selection):
    payload=path.read_bytes(); digest=hashlib.sha256(payload).hexdigest()
    target=path.with_name(f'{source}-{digest[:12]}{path.suffix}')
    if target.exists(): path.unlink()
    else: path.rename(target)
    doc=dict(source=source,path=str(target.relative_to(ROOT)),sha256=digest,bytes=len(payload),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),url=url,selection=selection,schema_version='source-native-v1')
    (ROOT/f'data/manifests/{source}.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps(doc),flush=True)
if __name__=='__main__':
    query={'$select':'camis,dba,building,street,zipcode,phone,cuisine_description,latitude,longitude,inspection_date,record_date','$where':f"boro='Manhattan' AND latitude between {BOX[1]} and {BOX[3]} AND longitude between {BOX[0]} and {BOX[2]}",'$limit':'50000','$order':'camis,inspection_date DESC'}
    url='https://data.cityofnewyork.us/resource/43nn-pn8j.json?'+urllib.parse.urlencode(query)
    p=RAW/'nyc.json';p.write_bytes(urllib.request.urlopen(url,timeout=120).read());manifest('nyc',p,url,query)
    p=RAW/'overture.geojson'
    subprocess.run([str(ROOT/'.venv/bin/overturemaps'),'download','--bbox',','.join(map(str,BOX)),'-f','geojson','--type','place','--release','2026-10-21.0','-o',str(p)],check=True)
    manifest('overture',p,'https://docs.overturemaps.org/guides/places/',dict(bbox=BOX,type='place',release='2026-10-21.0'))
