"""Local daily LinkedIn/Naukri discovery and conditional browser applications.
No passwords are accepted by this module. Sessions stay in a gitignored folder.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sqlite3,time,uuid
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from pydantic import BaseModel,Field,ConfigDict
from .core import load_profile,requirements,evaluate
from .workflow import run

IST=timezone(timedelta(hours=5,minutes=30))
def now():return datetime.now(IST).isoformat(timespec='seconds')

def job_key(url):
 p=urlsplit(url)
 if p.hostname in ('www.linkedin.com','linkedin.com'):
  m=re.search(r'(?:/view/|currentJobId=)(\d+)',url)
  if m:return 'linkedin:'+m.group(1)
 return (p.hostname or '')+p.path.rstrip('/')

class Settings(BaseModel):
 model_config=ConfigDict(extra="forbid",hide_input_in_errors=True)
 portals:list[str]=Field(default_factory=lambda:['linkedin','naukri'])
 query:str='Golang Python lead backend cloud native'
 location:str='India'
 minimum_match:float=Field(default=70,ge=0,le=100)
 maximum_match:float=Field(default=100,ge=0,le=100)
 daily_limit:int=Field(default=10,ge=1,le=100)
 max_jobs_per_portal:int=Field(default=30,ge=1,le=100)
 # No salary/work preference inferred; those controls can be added after user clarification.
 allowed_locations:list[str]=Field(default_factory=lambda:['india','bangalore','bengaluru','hyderabad','pune','chennai','mumbai','delhi','gurgaon','gurugram','noida'])
 allow_unknown_location:bool=False
 profile_path:str='resume/profile.json'
 private_dir:str='.jobpilot'
 browser_executable:str|None=None
 headless:bool=False
 answers:dict[str,str|bool]=Field(default_factory=dict)

 def validate_portals(self):
  if any(p not in ('linkedin','naukri') for p in self.portals):raise ValueError('Only LinkedIn and Naukri are supported.')
  if self.maximum_match<self.minimum_match:raise ValueError('Maximum match must be at least minimum match.')
  if not self.location.strip():raise ValueError('Set a search location.')

class Ledger:
 def __init__(self,path):
  self.conn=sqlite3.connect(path,timeout=30)
  self.conn.execute('CREATE TABLE IF NOT EXISTS applications (job_key TEXT PRIMARY KEY,url TEXT,portal TEXT,state TEXT,updated TEXT,attempt_day TEXT,details TEXT)')
  self.conn.commit()
 def get(self,key):
  row=self.conn.execute('SELECT state,details FROM applications WHERE job_key=?',(key,)).fetchone()
  return {'state':row[0],'details':json.loads(row[1])} if row else None
 def record(self,key,url,portal,state,details=None):
  old=self.get(key)
  if old and old['state'] in ('submitted','submission_unknown','submitting') and state not in ('submitted','submission_unknown'):
   return
  self.conn.execute('INSERT INTO applications VALUES (?,?,?,?,?,?,?) ON CONFLICT(job_key) DO UPDATE SET state=excluded.state,updated=excluded.updated,details=excluded.details',(key,url,portal,state,now(),None,json.dumps(details or {})))
  self.conn.commit()
 def reserve(self,key,url,portal,limit):
  day=now()[:10]
  self.conn.execute('BEGIN IMMEDIATE')
  try:
   row=self.conn.execute('SELECT state FROM applications WHERE job_key=?',(key,)).fetchone()
   if row and row[0] in ('submitted','submission_unknown','submitting'):
    self.conn.rollback();return False
   count=self.conn.execute('SELECT count(*) FROM applications WHERE attempt_day=?',(day,)).fetchone()[0]
   if count>=limit:self.conn.rollback();return False
   self.conn.execute('INSERT INTO applications VALUES (?,?,?,?,?,?,?) ON CONFLICT(job_key) DO UPDATE SET state=excluded.state,updated=excluded.updated,attempt_day=excluded.attempt_day',(key,url,portal,'submitting',now(),day,'{}'))
   self.conn.commit();return True
  except Exception:self.conn.rollback();raise
 def close(self):self.conn.close()

@contextmanager
def run_lock(folder):
 path=folder/'running.lock'
 try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError:raise ValueError('Another run is active, or a crash left running.lock. Verify no run is active before removing it.')
 try:
  os.write(fd,str(os.getpid()).encode());os.close(fd);yield
 finally:path.unlink(missing_ok=True)

def browser_context(pw,settings,portal):
 path=Path(settings.private_dir)/'sessions'/portal;path.mkdir(parents=True,exist_ok=True);os.chmod(path,0o700)
 kwargs={'headless':settings.headless,'viewport':{'width':1366,'height':900}}
 if settings.browser_executable:kwargs['executable_path']=settings.browser_executable
 return pw.chromium.launch_persistent_context(str(path),**kwargs)


def interrupted(page):
 url=page.url.lower()
 if any(x in url for x in ['/login','/checkpoint','/authwall','/challenge']):return 'Sign in locally, or complete the site challenge before rerunning.'
 # Visible challenge only; do not infer from hidden CAPTCHA script inclusion.
 for selector in ['iframe[title*="challenge" i]','iframe[title*="captcha" i]']:
  if page.locator(selector).count() and page.locator(selector).first.is_visible():return 'Site challenge needs user action.'
 return None


def discover(page,settings,portal):
 if portal=='linkedin':
  page.goto('https://www.linkedin.com/jobs/search/?'+urlencode({'keywords':settings.query,'location':settings.location,'f_TPR':'r86400'}),wait_until='domcontentloaded',timeout=45000)
  page.wait_for_timeout(2000)
  if interrupted(page):raise ValueError(interrupted(page))
  selector='li[data-occludable-job-id], .base-card'
 else:
  page.goto('https://www.naukri.com/'+re.sub('[^a-z0-9]+','-',settings.query.lower()).strip('-')+'-jobs',wait_until='domcontentloaded',timeout=45000)
  page.wait_for_timeout(2000)
  if interrupted(page):raise ValueError(interrupted(page))
  selector='.srp-jobtuple-wrapper, article.jobTuple'
 records={}
 # Bounded scrolling; this is not an unrestricted crawl.
 for _ in range(4):
  cards=page.locator(selector)
  for i in range(min(cards.count(),settings.max_jobs_per_portal)):
   card=cards.nth(i)
   link=card.locator('a[href*="/jobs/view/"]' if portal=='linkedin' else 'a.title').first
   if not link.count():continue
   url=link.get_attribute('href') or ''
   if url.startswith('/'):url=('https://www.linkedin.com' if portal=='linkedin' else 'https://www.naukri.com')+url
   if urlsplit(url).scheme!='https':continue
   records[job_key(url)]={'url':url,'title':link.inner_text().strip(),'portal':portal}
  if len(records)>=settings.max_jobs_per_portal:break
  page.mouse.wheel(0,1200);page.wait_for_timeout(750)
 if not records and not page.get_by_text(re.compile(r'(no jobs found|no matching jobs|0 jobs)',re.I)).count():raise ValueError('No recognizable job cards or explicit zero-results message. Check login/access and portal selectors.')
 return list(records.values())[:settings.max_jobs_per_portal]


def read_job(page,job):
 if urlsplit(job['url']).hostname not in (('www.linkedin.com','linkedin.com') if job['portal']=='linkedin' else ('www.naukri.com','naukri.com')):raise ValueError('External application URL requires manual handling.')
 page.goto(job['url'],wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(1200)
 if interrupted(page):raise ValueError(interrupted(page))
 if urlsplit(page.url).hostname not in (('www.linkedin.com','linkedin.com') if job['portal']=='linkedin' else ('www.naukri.com','naukri.com')):raise ValueError('Application redirected outside the supported portal.')
 selectors=['.jobs-description__container','.show-more-less-html__markup'] if job['portal']=='linkedin' else ['.job-desc','.job-description','section.job-desc']
 jd=None
 for s in selectors:
  loc=page.locator(s)
  if loc.count():jd=loc.first.inner_text();break
 if not jd or len(jd)<120:raise ValueError('Complete JD could not be identified; portal layout may have changed. No application sent.')
 locations=page.locator('.job-details-jobs-unified-top-card__primary-description-container, .topcard__flavor--bullet' if job['portal']=='linkedin' else '.loc, .location')
 location=' '.join(locations.all_text_contents()).strip()
 companies=page.locator('.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, .topcard__org-name-link' if job['portal']=='linkedin' else '.jd-header-comp-name, .comp-name')
 company=companies.first.inner_text().strip() if companies.count() else ''
 return jd,location,company


def normalized(s):return ' '.join(re.sub(r'[^\w]+',' ',s.lower()).split())

def fill_known_fields(scope,answers,resume):
 """Fill only labeled fields with explicitly supplied answers. Return unresolved required labels."""
 known={normalized(k):v for k,v in answers.items()};unresolved=[]
 inputs=scope.locator('input,select,textarea')
 for i in range(inputs.count()):
  field=inputs.nth(i)
  if not field.is_visible() or not field.is_enabled():continue
  kind=(field.get_attribute('type') or '').lower()
  if kind in ('submit','button','hidden'):continue
  if kind=='password':unresolved.append('Sign in directly; passwords are not application answers.');continue
  label=field.evaluate('(e)=>((e.labels&&[...e.labels].map(x=>x.innerText).join(" "))||e.getAttribute("aria-label")||e.getAttribute("placeholder")||"")')
  key=normalized(label);value=known.get(key)
  required=field.get_attribute('required') is not None or field.get_attribute('aria-required')=='true'
  if kind=='file':
   if 'resume' in key or 'cv' in key:field.set_input_files(str(resume))
   elif required:unresolved.append(label or 'unlabeled file upload')
   continue
  if value is not None:
   if kind in ('checkbox','radio'):
    if isinstance(value,bool):field.set_checked(value)
    else:unresolved.append(label+' (requires explicit boolean answer)')
   elif field.evaluate('(e)=>e.tagName')=='SELECT':field.select_option(label=str(value))
   else:field.fill(str(value))
  # Do not trust prefilled answers: account answers may be stale or unrelated.
  elif required:unresolved.append(label or 'unlabeled required field')
 return unresolved


def submit(page,job,resume,answers,before_submit,confirmation_timeout=20000):
 """Conditional portal flow. Success is recorded only after an explicit confirmation."""
 from playwright.sync_api import TimeoutError as BrowserTimeout
 if interrupted(page):return 'needs_action',interrupted(page)
 if urlsplit(page.url).hostname not in (('www.linkedin.com','linkedin.com') if job['portal']=='linkedin' else ('www.naukri.com','naukri.com')):return 'needs_action','Application left the supported portal.'
 if job['portal']=='linkedin':
  buttons=page.get_by_role('button',name=re.compile(r'^Easy Apply(?: to .*)?$',re.I))
  if buttons.count()!=1:return 'needs_action','No unambiguous Easy Apply flow; external application or changed layout.'
  buttons.click();scope=page.get_by_role('dialog')
  if scope.count()!=1:return 'needs_action','Application dialog could not be uniquely identified.'
 else:
  # Naukri one-click Apply often uses a stored account resume. Never assume it matches the tailored file.
  scope=page.locator('form').filter(has=page.locator('input[type=file]'))
  if scope.count()!=1:return 'needs_action','Naukri uses a stored account resume or another application flow; upload/review the tailored resume manually.'
 clicked=False;uploaded=False
 try:
  for _ in range(8):
   if interrupted(page):return ('submission_unknown' if clicked else 'needs_action'),interrupted(page)
   files=scope.locator('input[type=file]')
   for i in range(files.count()):
    field=files.nth(i)
    label=field.evaluate('(e)=>((e.labels&&[...e.labels].map(x=>x.innerText).join(" "))||e.getAttribute("aria-label")||"")')
    if re.search(r'resume|cv',label,re.I):field.set_input_files(str(resume));uploaded=True
   missing=fill_known_fields(scope,answers,resume)
   if missing:return 'needs_action','Required answers unavailable: '+', '.join(missing)
   error=scope.locator('[role=alert], .artdeco-inline-feedback--error, .error')
   if any(t.strip() for t in error.all_text_contents()):return 'needs_action','Form validation error; no submission attempted.'
   final=scope.get_by_role('button',name=re.compile(r'^(Submit application|Submit|Apply)$',re.I))
   if final.count()==1 and final.is_visible():
    if not uploaded:return 'needs_action','Could not verify that this job uses the newly tailored resume.'
    if not before_submit():return 'skipped','Duplicate, pending submission, or daily limit reached.'
    clicked=True;final.click(timeout=15000)
    page.get_by_text(re.compile(r'(application (?:was )?(?:sent|submitted)|successfully applied)',re.I)).first.wait_for(state='visible',timeout=confirmation_timeout)
    return 'submitted','Portal displayed application confirmation.'
   next_button=scope.get_by_role('button',name=re.compile(r'^(Next|Review)$',re.I))
   if next_button.count()!=1:return 'needs_action','Unknown application step; no submission attempted.'
   next_button.click();page.wait_for_timeout(500)
  return 'needs_action','Application exceeded the supported number of steps.'
 except Exception as e:
  # Never automatically retry a final click whose outcome is unknown.
  return ('submission_unknown' if clicked else 'needs_action'),type(e).__name__+' during application; inspect the portal before retrying.'


def run_daily(settings:Settings,live=False):
 settings.validate_portals();private=Path(settings.private_dir);private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
 from playwright.sync_api import sync_playwright
 profile=load_profile(Path(settings.profile_path));ledger=Ledger(private/'applications.sqlite3')
 folder=private/'runs'/(now()[:10]+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
 result={'date':now(),'mode':'submit' if live else 'prepare','score_type':'internal evidence-based keyword match, not vendor ATS','jobs':[],'portal_errors':{}}
 try:
  with run_lock(private),sync_playwright() as pw:
   for portal in settings.portals:
    context=None
    try:
     context=browser_context(pw,settings,portal);page=context.new_page()
     jobs=discover(page,settings,portal)
     for job in jobs:
      key=job_key(job['url']);previous=ledger.get(key)
      if previous and previous['state'] in ('submitted','submission_unknown','submitting'):
       result['jobs'].append({**job,'state':'skipped_duplicate_or_pending'});continue
      try:
       jd,location,company=read_job(page,job)
       score=evaluate(profile,requirements(jd))
       row={**job,'company':company,'location':location,'score':score['score'],'missing_evidence':score['missing'],'requirement_review':score['manual_review_required']}
       if not settings.minimum_match<=score['score']<=settings.maximum_match:
        row['state']='below_match_range';result['jobs'].append(row);continue
       if not settings.allow_unknown_location and not any(x.lower() in location.lower() for x in settings.allowed_locations):
        row.update(state='needs_action',reason='Could not verify target location/eligibility.');result['jobs'].append(row);continue
       output=folder/re.sub(r'[^A-Za-z0-9_-]','_',key)
       if not company:
        row.update(state='needs_action',reason='Could not identify company for the named resume.');result['jobs'].append(row);continue
       words=re.findall(r'[A-Za-z0-9]+',company)
       abbreviation=(''.join(w[0] for w in words) if len(words)>1 else company).upper()[:24]
       report=run(profile,jd,output,source=job['url'],company=abbreviation)
       row['resume']=str(output/report['files']['pdf'])
       if not live:row['state']='prepared'
       else:
        state,reason=submit(page,job,Path(row['resume']),settings.answers,lambda:ledger.reserve(key,job['url'],portal,settings.daily_limit))
        row.update(state=state,reason=reason)
       ledger.record(key,job['url'],portal,row['state'],row)
       result['jobs'].append(row)
      except Exception as e:result['jobs'].append({**job,'state':'needs_action','reason':type(e).__name__+': '+str(e)})
      time.sleep(1)
    except Exception as e:result['portal_errors'][portal]=type(e).__name__+': '+str(e)
    finally:
     if context:context.close()
 finally:
  ledger.close();(folder/'daily_report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
 return result,folder


def login(settings,portal):
 from playwright.sync_api import sync_playwright
 settings.validate_portals();settings.headless=False
 with sync_playwright() as pw:
  context=browser_context(pw,settings,portal)
  try:
   page=context.new_page();page.goto('https://www.linkedin.com/login' if portal=='linkedin' else 'https://www.naukri.com/nlogin/login')
   input('Sign in directly in the browser. Complete any verification, then press Enter here. No password is read by this command. ')
  finally:context.close()


def next_daily_time(current,clock):
 hour,minute=(int(x) for x in clock.split(':'))
 if not 0<=hour<24 or not 0<=minute<60:raise ValueError('Daily time must be HH:MM (India time).')
 local=current.astimezone(IST);target=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
 return target if target>local else target+timedelta(days=1)


def schedule(settings,live,clock):
 # Runs only while this local process/machine remains available. No chat scheduling is implied.
 while True:
  target=next_daily_time(datetime.now(IST),clock)
  print('Next run:',target.isoformat(),flush=True)
  while datetime.now(IST)<target:time.sleep(min(60,max(0,(target-datetime.now(IST)).total_seconds())))
  try:
   result,path=run_daily(settings,live)
   print('Run finished; report:',path,flush=True)
  except Exception as e:print(type(e).__name__+': '+str(e),flush=True)


def main():
 p=argparse.ArgumentParser(description='JobPilot India: local LinkedIn/Naukri discovery and conditional applications.')
 p.add_argument('--config',type=Path,required=True)
 p.add_argument('--daily-at',help='Repeat daily at HH:MM Asia/Kolkata while this process stays running')
 g=p.add_mutually_exclusive_group();g.add_argument('--login',choices=['linkedin','naukri']);g.add_argument('--submit',action='store_true')
 a=p.parse_args()
 try:
  settings=Settings.model_validate_json(a.config.read_text())
  if a.login:
   if a.daily_at:raise ValueError('Login is interactive and cannot be scheduled.')
   login(settings,a.login)
  elif a.daily_at:schedule(settings,a.submit,a.daily_at)
  else:
   result,path=run_daily(settings,a.submit)
   print(json.dumps({'mode':result['mode'],'report_folder':str(path),'states':{s:sum(j['state']==s for j in result['jobs']) for s in {j['state'] for j in result['jobs']}},'portal_errors':result['portal_errors']},indent=2))
 except Exception as e:print(type(e).__name__+': '+str(e));return 2
 return 0

if __name__=='__main__':raise SystemExit(main())
