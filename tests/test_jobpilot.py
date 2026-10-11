import json
from pathlib import Path
import pytest
from ats_agent.jobpilot import next_daily_time,IST,Ledger,Settings,job_key,run_lock,fill_known_fields,submit,read_job,run_daily


def test_keys_ignore_tracking():
 assert job_key('https://www.linkedin.com/jobs/view/123/?tracking=x')==job_key('https://www.linkedin.com/jobs/view/123/?tracking=y')
 assert job_key('https://www.naukri.com/job-listings-go-developer-123?src=x')==job_key('https://www.naukri.com/job-listings-go-developer-123?src=y')

def test_ledger_no_duplicate_unknown_or_over_limit(tmp_path):
 l=Ledger(tmp_path/'db')
 assert l.reserve('a','https://test/a','linkedin',2)
 assert not l.reserve('a','https://test/a','linkedin',2)
 l.record('a','https://test/a','linkedin','submitted')
 assert not l.reserve('a','https://test/a','linkedin',2)
 assert l.reserve('b','https://test/b','linkedin',2)
 l.record('b','https://test/b','linkedin','submission_unknown')
 assert not l.reserve('b','https://test/b','linkedin',2)
 assert not l.reserve('c','https://test/c','linkedin',2)
 l.record('a','https://test/a','linkedin','prepared')
 assert l.get('a')['state']=='submitted'
 l.close()

def test_run_lock(tmp_path):
 with run_lock(tmp_path):
  with pytest.raises(ValueError):
   with run_lock(tmp_path):pass
 assert not (tmp_path/'running.lock').exists()

def test_config_rejects_password_without_printing_it():
 with pytest.raises(ValueError) as e:Settings.model_validate({'password':'private-value-test'})
 assert 'private-value-test' not in str(e.value)

@pytest.fixture
def browser():
 pytest.importorskip('playwright.sync_api')
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  import os,shutil
  executable=os.environ.get('JOBPILOT_BROWSER') or shutil.which('chromium')
  b=p.chromium.launch(executable_path=executable,headless=True)
  try:yield b
  finally:b.close()

HTML='''<button onclick="document.querySelector('[role=dialog]').style.display='block'">Easy Apply</button>
<div role="dialog" style="display:none"><label>Email address<input id="email" required></label>
<label>Resume<input id="resume" type="file"></label>
<button onclick="window.sent=(window.sent||0)+1;document.querySelector('#confirmation').style.display='block'">Submit application</button>
</div><p id="confirmation" style="display:none">Application submitted</p>'''

def mock_page(browser,html=HTML):
 page=browser.new_page();page.route('https://www.linkedin.com/**',lambda route:route.fulfill(body=html,content_type='text/html'))
 page.goto('https://www.linkedin.com/jobs/view/123/');return page


def test_browser_submit_and_deduplicate_on_local_fixture(browser,tmp_path):
 page=mock_page(browser);resume=tmp_path/'resume.pdf';resume.write_bytes(b'%PDF mock')
 l=Ledger(tmp_path/'db');job={'url':page.url,'portal':'linkedin'}
 reserve=lambda:l.reserve(job_key(page.url),page.url,'linkedin',10)
 state,reason=submit(page,job,resume,{'Email address':'candidate@example.com'},reserve)
 assert state=='submitted' and page.evaluate('window.sent')==1
 l.record(job_key(page.url),page.url,'linkedin',state)
 assert not reserve()
 assert page.locator('#resume').evaluate('(e)=>e.files[0].name')=='resume.pdf'
 l.close();page.close()


def test_unknown_required_question_blocks_click(browser,tmp_path):
 page=mock_page(browser,HTML.replace('<label>Resume', '<label>Current salary<input required></label><label>Resume'))
 resume=tmp_path/'resume.pdf';resume.write_bytes(b'%PDF mock')
 state,reason=submit(page,{'url':page.url,'portal':'linkedin'},resume,{'Email address':'candidate@example.com'},lambda:True)
 assert state=='needs_action' and 'Current salary' in reason
 assert page.evaluate('window.sent||0')==0
 page.close()


def test_no_resume_upload_blocks_submission(browser,tmp_path):
 page=mock_page(browser,HTML.replace('<label>Resume<input id="resume" type="file"></label>',''))
 state,reason=submit(page,{'url':page.url,'portal':'linkedin'},tmp_path/'resume.pdf',{'Email address':'candidate@example.com'},lambda:True)
 assert state=='needs_action' and 'tailored resume' in reason
 assert page.evaluate('window.sent||0')==0
 page.close()


def test_password_field_is_never_filled(browser,tmp_path):
 page=mock_page(browser,'<form><label>Password<input type="password" required></label></form>')
 missing=fill_known_fields(page.locator('form'),{'Password':'private-test-value'},tmp_path/'resume.pdf')
 assert missing and page.locator('input').input_value()==''
 page.close()


def test_daily_preparation_creates_named_resume_without_submission(monkeypatch,tmp_path):
 pytest.importorskip('playwright.sync_api')
 import ats_agent.jobpilot as jp
 root=Path(__file__).resolve().parents[1]
 jd=(root/'examples/jobs/01_go_backend.txt').read_text()
 class Context:
  def new_page(self):return object()
  def close(self):pass
 monkeypatch.setattr(jp,'browser_context',lambda *a:Context())
 monkeypatch.setattr(jp,'discover',lambda *a:[{'portal':'linkedin','url':'https://www.linkedin.com/jobs/view/123/','title':'Go Lead'}])
 monkeypatch.setattr(jp,'read_job',lambda *a:(jd,'Bangalore, India','Example Company'))
 monkeypatch.setattr(jp,'submit',lambda *a:pytest.fail('Preparation mode must not submit'))
 s=Settings(portals=['linkedin'],profile_path=str(root/'resume/profile.json'),private_dir=str(tmp_path/'private'))
 result,folder=run_daily(s,live=False)
 assert result['jobs'][0]['state']=='prepared'
 assert '_EC_' in result['jobs'][0]['resume']
 assert Path(result['jobs'][0]['resume']).exists()
 assert (folder/'daily_report.json').exists()


def test_naukri_account_resume_is_not_assumed(browser,tmp_path):
 page=browser.new_page();page.route('https://www.naukri.com/**',lambda route:route.fulfill(body='<button>Apply</button>',content_type='text/html'));page.goto('https://www.naukri.com/job-listings-test')
 state,reason=submit(page,{'url':page.url,'portal':'naukri'},tmp_path/'resume.pdf',{},lambda:True)
 assert state=='needs_action' and 'stored account resume' in reason
 page.close()


def test_confirmation_timeout_is_unknown_not_safe_to_retry(browser,tmp_path):
 page=mock_page(browser,HTML.replace("document.querySelector('#confirmation').style.display='block'", "document.querySelector('#confirmation').style.display='none'"))
 resume=tmp_path/'resume.pdf';resume.write_bytes(b'%PDF mock')
 ledger=Ledger(tmp_path/'db');key=job_key(page.url)
 state,reason=submit(page,{'url':page.url,'portal':'linkedin'},resume,{'Email address':'candidate@example.com'},lambda:ledger.reserve(key,page.url,'linkedin',10),confirmation_timeout=100)
 assert state=='submission_unknown'
 ledger.record(key,page.url,'linkedin',state)
 assert not ledger.reserve(key,page.url,'linkedin',10)
 ledger.close();page.close()


def test_india_daily_schedule():
 from datetime import datetime,timezone
 before=datetime(2026,10,11,2,0,tzinfo=timezone.utc) # 07:30 India
 assert next_daily_time(before,'09:00').isoformat()=='2026-10-11T09:00:00+05:30'
 after=datetime(2026,10,11,10,0,tzinfo=IST)
 assert next_daily_time(after,'09:00').isoformat()=='2026-10-12T09:00:00+05:30'
 with pytest.raises(ValueError):next_daily_time(before,'25:00')
