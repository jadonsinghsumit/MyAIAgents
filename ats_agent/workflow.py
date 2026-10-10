import json,re,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .core import Profile, requirements, evaluate, tailor, flatten
from .export import export

def run(profile: Profile, jd: str, out: Path, photo: Path|None=None, source='pasted JD', company='TARGET'):
 if photo is None and profile.name.strip().upper()=='SUMIT SINGH JADAUN' and any('sumitsinghjadaun@gmail.com' in c for c in profile.contacts):
  bundled=Path(__file__).resolve().parents[1]/'resume'/'Sumit_photo.jpg'
  if bundled.exists():photo=bundled
 company=re.sub(r'[^A-Za-z0-9_-]','_',company.strip()).strip('_').upper()[:24]
 if not company:raise ValueError('Provide a company short name using letters or numbers.')
 prepared_date=datetime.now(timezone(timedelta(hours=5,minutes=30))).strftime('%Y-%m-%d')
 label=f'Prepared for {company} | {prepared_date}'
 req=requirements(jd);before=evaluate(profile,req)
 out.mkdir(parents=True,exist_ok=True)
 history=[];result=None;candidate=None;after=None
 # Bound retries: first reorder, then trim lower-ranked bullets only to fit one page.
 # Scores are measured on extracted PDF text; discarded evidence earns no credit.
 for step in range(5):
  candidate=tailor(profile,req,step)
  result=export(candidate,out,photo,label)
  after=evaluate(profile,req,result['text'])
  history.append({'iteration':step,'pages':result['pages'],'score':after['score'],'target_exceeded':after['target_exceeded']})
  if result['pages']==1:break
 if result['pages']!=1:
  for name in ['resume.pdf','resume.docx']:(out/name).unlink(missing_ok=True)
  raise ValueError('Cannot fit this profile onto one readable page without excessive deletion. Shorten the reviewed profile and rerun; no final resume was produced.')
 original={t for e in profile.experience for t in e.bullets}
 assert all(t in original for e in candidate.experience for t in e.bullets)
 stem=re.sub(r'[^A-Za-z0-9_-]','_',profile.name).strip('_') or 'Resume'
 stem=f'{stem}_{company}_{prepared_date}_{uuid.uuid4().hex[:8]}'
 files={}
 for ext in ['pdf','docx']:
  target=out/(stem+'.'+ext);(out/('resume.'+ext)).rename(target);files[ext]=target.name
 files.update({'report':stem+'_report.json','review':stem+'_report.md','text':stem+'.txt','jd':stem+'_JD.txt'})
 report={'company_short_name':company,'prepared_date':prepared_date,'date_timezone':'Asia/Kolkata','files':files,'source':source,'before':before,'after':after,'iterations':history,'pages':result['pages'],
         'status':'internal_target_exceeded' if after['target_exceeded'] else 'needs_review_or_missing_evidence',
         'changes':['Reordered existing bullets by detected JD relevance.','Prioritized supported skill names; no new employer claims added.'],
         'removed_bullets':[t for t in original if t not in {b for e in candidate.experience for b in e.bullets}],
         'source_profile':profile.model_dump(),'tailored_profile':candidate.model_dump()}
 (out/files['report']).write_text(json.dumps(report,indent=2,ensure_ascii=False))
 (out/files['text']).write_text(flatten(candidate))
 (out/files['jd']).write_text(jd)
 lines=['# Resume match report','',after['label'],'',f"Before: {before['score']}% | After: {after['score']}% | PDF pages: {result['pages']}",
        f"Status: {report['status']}",'',after['scoring_formula'],'','## Requirement evidence','']
 for r in after['requirements']:
  lines.append(f"- **{r['skill']}** (weight {r['weight']}): {'covered' if r['covered'] else 'missing or not retained'}")
  lines.append('  - JD: '+r['jd_evidence'])
  for e in r['resume_evidence'][:2]:lines.append('  - Resume: '+e)
 lines+=['','## Human review required',*['- '+t for t in after['manual_review_required']],
         '','## Limits',*['- '+t for t in after['limits']],
         '- The matcher does not obtain scores from employer ATS systems or promise a 90% vendor score.',
         '- Unrecognized requirements must be reviewed against the complete JD before applying.',
         '- The bundled Sumit profile retains its photo; other profiles can supply a photo explicitly. Source files and the master resume are not overwritten.']
 (out/files['review']).write_text('\n'.join(lines))
 return report
