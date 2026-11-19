"""Fetch official Qwen model files to the server and verify repository SHA-256."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,time,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'artifacts/runtime/target_live/model_comparison_models'
MODELS=['Qwen3.5-9B','Qwen3-VL-8B-Instruct']

def get_json(url):
 with urllib.request.urlopen(url,timeout=30) as f:return json.load(f)

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def fetch(model,entry):
 path=entry['Path'];size=int(entry['Size']);expected=entry.get('Sha256')
 target=DEST/model/path;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and target.stat().st_size==size and (not expected or sha(target)==expected):
  print('verified-existing',model,path,flush=True);return
 partial=target.with_name(target.name+'.part')
 url='https://www.modelscope.cn/api/v1/models/Qwen/'+model+'/repo?'+urllib.parse.urlencode({'Revision':'master','FilePath':path})
 for attempt in range(8):
  try:
   start=partial.stat().st_size if partial.exists() else 0
   if start>size: raise ValueError('partial larger than expected')
   if start<size:
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-','User-Agent':'target-evaluation/1.0'})
    with urllib.request.urlopen(req,timeout=90) as response:
     content_range=response.headers.get('Content-Range','')
     if response.status not in (200, 206) or not content_range.startswith(f'bytes {start}-'):
      raise ValueError(f'unexpected range {response.status} {content_range}')
     with partial.open('ab') as f:
      while True:
       chunk=response.read(4*1024*1024)
       if not chunk:break
       f.write(chunk)
   if partial.stat().st_size!=size:raise ValueError(f'incomplete {partial.stat().st_size}/{size}')
   if expected and sha(partial)!=expected:raise ValueError('sha256 mismatch')
   partial.replace(target);print('verified',model,path,size,flush=True);return
  except Exception as e:
   print('retry',model,path,attempt+1,str(e)[:180],flush=True)
   if 'sha256 mismatch' in str(e):partial.unlink(missing_ok=True)
   time.sleep(min(2**attempt,30))
 raise RuntimeError('download failed: '+model+'/'+path)

jobs=[]
for model in MODELS:
 url='https://www.modelscope.cn/api/v1/models/Qwen/'+model+'/repo/files?Revision=master&Recursive=True'
 data=get_json(url);assert data.get('Code')==200
 entries=[e for e in data['Data']['Files'] if e.get('Type')=='blob' and not e['Path'].startswith('.')]
 (DEST/model).mkdir(parents=True,exist_ok=True)
 (DEST/model/'official_file_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
 jobs.extend((model,e) for e in entries)
 print('manifest',model,len(entries),sum(e['Size'] for e in entries),flush=True)
with ThreadPoolExecutor(max_workers=8) as pool:
 futures=[pool.submit(fetch,*job) for job in jobs]
 for future in as_completed(futures):future.result()
(DEST/'DOWNLOAD_COMPLETE').write_text('verified\n')
print('DOWNLOAD_COMPLETE',flush=True)
