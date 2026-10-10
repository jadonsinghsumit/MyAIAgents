from pathlib import Path
import shutil,tempfile,uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI,File,Form,UploadFile,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
from .core import load_profile
from .fetch import fetch_job
from .workflow import run

@asynccontextmanager
async def lifespan(app):
 ROOT.mkdir(parents=True,exist_ok=True)
 try:yield
 finally:
  shutil.rmtree(ROOT,ignore_errors=True)
  JOBS.clear()

app=FastAPI(title='JDMatch Resume Agent',lifespan=lifespan)
# Single-user local application. Outputs live outside the repository; no credential required.
ROOT=Path(tempfile.mkdtemp(prefix='resume-agent-'))
JOBS={}
@app.get('/',response_class=HTMLResponse)
def index():
 return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>JDMatch Resume Agent</title><style>
body{font:16px system-ui;background:#edf2f7;color:#17354f;max-width:900px;margin:40px auto;padding:20px}main{background:white;border-radius:16px;padding:30px}textarea,input,button{font:inherit;box-sizing:border-box;width:100%;padding:12px;margin:10px 0;border:1px solid #b7c6d5;border-radius:7px}button{background:#17354f;color:white;cursor:pointer}textarea{height:230px}.notice{background:#fff5dc;padding:15px;border-radius:8px}a{color:#1260a0}pre{white-space:pre-wrap}label{font-weight:600}</style></head><body><main>
<h1>JDMatch Resume Agent</h1><p>Compare a job description with your actual experience and create a tailored one-page resume.</p>
<p class="notice"><b>This is an internal keyword match score, not an employer ATS score.</b> No invented skills, no guaranteed acceptance, and no applications submitted.</p>
<form id="form"><label>Company short name (e.g. CISCO or PAN)</label><input required name="company" maxlength="24" placeholder="CISCO"><label>Resume (PDF, DOCX, TXT, or reviewed profile JSON)</label><input required type="file" name="resume" accept=".pdf,.docx,.txt,.json">
<label>Paste the complete job description</label><textarea name="jd" placeholder="Requirements, responsibilities, qualifications…"></textarea>
<label>Or enter one public HTTPS job link</label><input type="url" name="url" placeholder="https://…">
<p>Paste the JD if the site requires login, JavaScript, or blocks retrieval. Review the extracted requirements in the report.</p>
<button>Analyze and tailor</button></form><section id="result" aria-live="polite"></section></main>
<script>document.querySelector('#form').onsubmit=async e=>{e.preventDefault();let el=document.querySelector('#result');el.textContent='Analyzing…';try{let r=await fetch('/analyze',{method:'POST',body:new FormData(e.target)});let d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');el.replaceChildren();let h=document.createElement('h2');h.textContent='Internal match: '+d.score+'%';el.append(h);let p=document.createElement('p');p.textContent=d.status+' — missing evidence: '+(d.missing.join(', ')||'none detected')+' — manual checks: '+d.manual_checks;el.append(p);for(let [name,path] of Object.entries(d.downloads)){let a=document.createElement('a');a.href=path;a.textContent='Download '+name;a.style.marginRight='20px';el.append(a)}let pre=document.createElement('pre');pre.textContent=d.review;el.append(pre)}catch(err){el.textContent=err.message}};</script></body></html>'''

@app.post('/analyze')
async def analyze(resume:UploadFile=File(...),jd:str=Form(''),url:str=Form(''),company:str=Form(...)):
 if bool(jd.strip())==bool(url.strip()):raise HTTPException(400,'Provide either a pasted JD or one job link.')
 suffix=Path(resume.filename or '').suffix.lower()
 if suffix not in ('.pdf','.docx','.txt','.json'):raise HTTPException(400,'Unsupported resume format.')
 data=await resume.read(8_000_001)
 if len(data)>8_000_000:raise HTTPException(413,'Resume exceeds 8 MB.')
 job=uuid.uuid4().hex;folder=ROOT/job;folder.mkdir();source=folder/('input'+suffix);source.write_bytes(data)
 try:
  # Run synchronous document/network work outside the event loop.
  from starlette.concurrency import run_in_threadpool
  def work():return run(load_profile(source),fetch_job(url) if url else jd,folder/'output',source=url or 'pasted JD',company=company)
  report=await run_in_threadpool(work)
 except Exception as e:
  shutil.rmtree(folder,ignore_errors=True);raise HTTPException(400,str(e)) from e
 JOBS[job]={'folder':folder/'output','files':{'resume.pdf':report['files']['pdf'],'resume.docx':report['files']['docx'],'report.json':report['files']['report']}}
 return {'score':report['after']['score'],'status':report['status'],'missing':report['after']['missing'],
         'manual_checks':len(report['after']['manual_review_required']),
         'review':(folder/'output'/report['files']['review']).read_text(),
         'downloads':{label:f'/download/{job}/{name}' for label,name in [('PDF','resume.pdf'),('Word','resume.docx'),('report','report.json')]}}

@app.get('/download/{job}/{name}')
def download(job:str,name:str):
 if job not in JOBS or name not in ('resume.pdf','resume.docx','report.json'):raise HTTPException(404,'File not found.')
 actual=JOBS[job]['files'][name]
 return FileResponse(JOBS[job]['folder']/actual,filename=actual)

@app.delete('/results/{job}')
def delete(job:str):
 if job not in JOBS:raise HTTPException(404,'Result not found.')
 shutil.rmtree(JOBS.pop(job)['folder'].parent);return {'deleted':True}

