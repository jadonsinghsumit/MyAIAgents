"""Run from repository root with the local server running; fail on broken behavior."""
import json,urllib.request,uuid
from pathlib import Path
import fitz
base='http://127.0.0.1:8765'
assert urllib.request.urlopen(base,timeout=10).status==200
boundary='----'+uuid.uuid4().hex
jd=Path('examples/jobs/01_go_backend.txt').read_bytes()
profile=Path('resume/profile.json').read_bytes()
body=(f'--{boundary}\r\nContent-Disposition: form-data; name="company"\r\n\r\nCISCO\r\n'.encode()+f'--{boundary}\r\nContent-Disposition: form-data; name="jd"\r\n\r\n'.encode()+jd+b'\r\n'+
      f'--{boundary}\r\nContent-Disposition: form-data; name="resume"; filename="profile.json"\r\nContent-Type: application/json\r\n\r\n'.encode()+profile+b'\r\n'+f'--{boundary}--\r\n'.encode())
request=urllib.request.Request(base+'/analyze',data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
assert data['score']>90 and data['status']=='internal_target_exceeded'
pdf=urllib.request.urlopen(base+data['downloads']['PDF'],timeout=10).read()
with fitz.open(stream=pdf,filetype='pdf') as doc:
 assert len(doc)==1
 assert 'EDUCATION' in doc[0].get_text() and 'SUMIT' in doc[0].get_text()
assert urllib.request.urlopen(base+data['downloads']['Word']).read().startswith(b'PK')
report=json.load(urllib.request.urlopen(base+data['downloads']['report']))
assert report['pages']==1 and not report['after']['missing']
job=data['downloads']['PDF'].split('/')[2]
with urllib.request.urlopen(urllib.request.Request(base+'/results/'+job,method='DELETE')) as response:assert json.load(response)['deleted']
print('PASS: running HTTP upload, analysis, one-page PDF, Word/report downloads, and cleanup (synthetic JD).')
