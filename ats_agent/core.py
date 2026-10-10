from __future__ import annotations
import copy
import re
from pathlib import Path
from pydantic import BaseModel, Field

# Aliases are equivalences, not permission to invent skills. Regexes avoid Go/SQL substring matches.
SKILLS = {
 'Go': [r'golang',r'go(?:\s+language|\s+developer|\s+services|\s+microservices|\s+sdk|\s+programming)?'],
 'Python':[r'python'], 'REST':[r'rest(?:ful)?(?:\s+apis?)?'], 'gRPC':[r'grpc'],
 'Microservices':[r'microservices?',r'micro-services?'], 'Kubernetes':[r'kubernetes',r'k8s'],
 'Helm':[r'helm'], 'Docker':[r'docker'], 'Kafka':[r'(?:apache\s+)?kafka'],
 'Temporal':[r'temporal'], 'FastAPI':[r'fastapi'], 'Pydantic':[r'pydantic'],
 'Ansible':[r'ansible'], 'Linux':[r'linux'], 'Git':[r'git'],
 'Protocol Buffers':[r'protocol buffers?',r'protobuf'], 'OpenAPI':[r'openapi',r'swagger'],
 'Vault':[r'(?:hashicorp\s+)?vault'], 'JWT':[r'jwt',r'json web tokens?'],
 'OAuth 2.0':[r'oauth(?:\s*2(?:\.0)?)?'], 'OpenID Connect':[r'openid connect',r'oidc'],
 'mTLS':[r'mtls',r'mutual tls'], 'RBAC':[r'rbac',r'role.based access control'],
 'SASL':[r'sasl'], 'VMware':[r'vmware',r'esxi'],
 'AWS':[r'aws',r'amazon web services'], 'GCP':[r'gcp',r'google cloud(?: platform)?'],
 'Azure':[r'azure'], 'Terraform':[r'terraform'], 'PostgreSQL':[r'postgres(?:ql)?'],
 'OpenSearch':[r'opensearch'], 'AI-assisted development':[r'ai.assisted development'], 'AI agent engineering':[r'ai workflow/agent engineering',r'ai agent engineering',r'agentic ai'], 'AI prototyping':[r'prototyping of ai',r'ai prototyping'], 'Certificate lifecycle management':[r'certificate lifecycle management'], 'Cluster lifecycle management':[r'cluster lifecycle management'], 'SQL':[r'sql'], 'Redis':[r'redis'], 'MongoDB':[r'mongodb'],
 'RabbitMQ':[r'rabbitmq'], 'NoSQL':[r'nosql'], 'Data modeling':[r'data model(?:l)?ing'], 'Prometheus':[r'prometheus'], 'Grafana':[r'grafana'], 'OpenTelemetry':[r'opentelemetry',r'otel'],
 'Kubernetes controllers':[r'kubernetes controllers?',r'k8s controllers?',r'controller-runtime',r'kubebuilder'],
 'Kubernetes operators':[r'kubernetes operators?',r'k8s operators?',r'operator sdk'],
 'CRDs':[r'crds?',r'custom resource definitions?'],
 'CI/CD':[r'ci/cd',r'continuous integration',r'continuous delivery'],
 'Jenkins':[r'jenkins'], 'Java':[r'java'], 'C++':[r'c\+\+'], 'Rust':[r'rust'],
 'React':[r'react'], 'JavaScript':[r'javascript'], 'TypeScript':[r'typescript'],
 'System design':[r'system design',r'architecture',r'architecting',r'architectural'],
 'Leadership':[r'leadership',r'led\s+\d',r'mentor(?:ing)?',r'technical lead',r'leading\s+(?:a\s+)?team'],
 'Distributed systems':[r'distributed systems?'], 'Observability':[r'observability'],
 'Authentication':[r'authentication'], 'Authorization':[r'authorization',r'authorisation'],
 'Testing':[r'testing',r'unit tests?',r'pytest',r'test plans?'],
}

def matches(text: str) -> set[str]:
 result=set()
 for name,aliases in SKILLS.items():
  for alias in aliases:
   for m in re.finditer(r'(?<![\w])(?:'+alias+r')(?![\w])',text,re.I):
    prefix=text[max(0,m.start()-65):m.start()]
    if re.search(r'(?:no experience (?:with|in)|not (?:used|familiar with)|do not (?:know|use)|lack(?:ing)? (?:experience (?:with|in) )?|without experience (?:with|in))\s*$',prefix,re.I):continue
    if name=='Go' and re.match(r'\s+(?:to|through|ahead|beyond|above)\b',text[m.end():],re.I):continue
    result.add(name)
 return result

class Experience(BaseModel):
 heading: str
 bullets: list[str]

class Profile(BaseModel):
 name: str
 headline: str
 contacts: list[str] = Field(default_factory=list)
 summary: str
 skills: list[str]
 experience: list[Experience]
 education: list[str] = Field(default_factory=list)
 # Exact source is retained locally for traceability, never sent to a model.
 source_text: str = ''

 def evidence(self) -> dict[str, list[str]]:
  evidence={}
  # Titles/headlines and summaries alone do not establish technical work.
  for i, text in enumerate(self.skills):
   for k in matches(text): evidence.setdefault(k,[]).append(f'skills[{i}]: {text}')
  for i, exp in enumerate(self.experience):
   for j, text in enumerate(exp.bullets):
    for k in matches(text):evidence.setdefault(k,[]).append(f'experience[{i}].bullets[{j}]: {text}')
  return evidence


def extract_resume(path: Path) -> str:
 suffix=path.suffix.lower()
 if path.stat().st_size > 8_000_000: raise ValueError('Resume exceeds 8 MB.')
 if suffix=='.pdf':
  import fitz
  with fitz.open(path) as doc:
   if doc.is_encrypted: raise ValueError('Use an unencrypted resume.')
   text='\n'.join(p.get_text(sort=True) for p in doc)
 elif suffix=='.docx':
  from docx import Document
  d=Document(path)
  text='\n'.join(p.text for p in d.paragraphs)
  text+='\n'+'\n'.join(c.text for t in d.tables for r in t.rows for c in r.cells)
 elif suffix in ('.txt','.md'):text=path.read_text(encoding='utf-8')
 else:raise ValueError('Supported resume formats: PDF, DOCX, TXT, JSON profile.')
 if len(text.strip())<100:raise ValueError('No usable resume text. Scanned PDFs need OCR first; upload DOCX/TXT instead.')
 return text


def load_profile(path: Path) -> Profile:
 if path.suffix.lower()=='.json':return Profile.model_validate_json(path.read_text())
 text=extract_resume(path)
 # Supports our standard one-page format. Never silently guess employment for arbitrary resumes.
 headings=['PROFESSIONAL SUMMARY','TECHNICAL SKILLS','PROFESSIONAL EXPERIENCE','EDUCATION']
 upper=text.upper()
 if not all(h in upper for h in headings):
  raise ValueError('Could not safely identify resume sections. Use the supplied structured profile JSON, or a resume with PROFESSIONAL SUMMARY, TECHNICAL SKILLS, PROFESSIONAL EXPERIENCE, EDUCATION headings.')
 parts={}
 for i,h in enumerate(headings):
  a=upper.index(h)+len(h);b=upper.index(headings[i+1]) if i+1<len(headings) else len(text)
  parts[h]=text[a:b].strip()
 top=text[:upper.index(headings[0])].strip().splitlines()
 exp=[];current=None
 lines=parts['PROFESSIONAL EXPERIENCE'].splitlines()
 for i,line in enumerate(lines):
  line=line.strip()
  if not line:continue
  # One-line TXT/DOCX employer+title+date or two-line PDF employer/title.
  if ' | ' in line and re.search(r'\b(?:20\d\d|19\d\d|Present)\b',line):
   previous=lines[i-1].strip() if i else ''
   title=previous+' | '+line if previous and ' | ' not in previous and not previous.startswith(('•','-')) and len(previous)<65 else line
   current=Experience(heading=title,bullets=[]);exp.append(current)
  elif i+1<len(lines) and ' | ' in lines[i+1] and re.search(r'\b20\d\d\b',lines[i+1]):continue
  elif current:
   if line.startswith(('•','-','*')) or not current.bullets:current.bullets.append(line.lstrip('•-* '))
   elif path.suffix.lower() in ('.txt','.docx'):current.bullets.append(line)
   else:current.bullets[-1]+=' '+line
 if not exp:raise ValueError('Employment headings could not be parsed safely. Use a reviewed profile JSON.')
 education=[x.strip() for x in parts['EDUCATION'].splitlines() if x.strip()]
 return Profile(name=top[0],headline=top[1],contacts=top[2:],summary=' '.join(parts['PROFESSIONAL SUMMARY'].split()),skills=[parts['TECHNICAL SKILLS']],experience=exp,education=education,source_text=text)


OPTIONAL=re.compile(r'\b(preferred|nice.to.have|bonus|optional|a plus|desirable)\b',re.I)
REQUIRED=re.compile(r'\b(required|must|essential|mandatory|minimum|requirements|qualifications)\b',re.I)

def unrecognized_requirement(line: str) -> bool:
 residue=line
 aliases=sorted((a for v in SKILLS.values() for a in v),key=len,reverse=True)
 for a in aliases:residue=re.sub(r'(?<!\w)(?:'+a+r')(?!\w)',' ',residue,flags=re.I)
 boilerplate={'required','must','essential','mandatory','minimum','requirements','qualifications','skills','skill','experience','with','in','and','of','knowledge','familiarity','proficiency','proficient','strong','hands','on','working','expertise','have','be','using','use','the','a','an','technical','technologies','technology','development','programming','language','languages','apis','api'}
 return any(w.lower() not in boilerplate for w in re.findall(r'[A-Za-z0-9]+',residue))


def requirements(jd: str) -> dict:
 if len(jd)>100_000:raise ValueError('JD exceeds 100,000 characters.')
 if len(jd.strip()) < 120:raise ValueError('Paste a complete JD (at least 120 characters).')
 # Section-aware importance; original text remains visible for review.
 entries={};section='general';review=[];groups={}
 for line in jd.splitlines():
  line=line.strip()
  if not line:continue
  if OPTIONAL.search(line):section='preferred'
  elif REQUIRED.search(line):section='required'
  elif re.match(r'^(responsibilities|about (us|the company)|benefits|what we offer)',line,re.I):section='general'
  weight=1 if OPTIONAL.search(line) else (3 if REQUIRED.search(line) or section=='required' else (1 if section=='preferred' else 2))
  found=matches(line)
  alternatives=set()
  if re.search(r'\bor\b|and/or',line,re.I):
   for family in [{'Go','Java','Python','Rust','C++','JavaScript','TypeScript'},{'AWS','GCP','Azure'}]:
    choices=sorted(found & family)
    if len(choices)>=2:
     alternatives.update(choices);key=' / '.join(choices)+' (one sufficient)'
     if key not in groups or weight>groups[key]['weight']:groups[key]={'skill':key,'choices':choices,'weight':weight,'jd_evidence':line}
  for k in found-alternatives:
   if k not in entries or weight>entries[k]['weight']:entries[k]={'skill':k,'weight':weight,'jd_evidence':line}
  if (REQUIRED.search(line) or section=='required') and len(line)>30:
   if not found or unrecognized_requirement(line) or re.search(r'\b(?:years?|degree|bachelor|master|citizen|visa|authorization to work|location|relocat|remote|hybrid|onsite|on-site|certification|certified|expert|advanced|production|at scale|or)\b',line,re.I):review.append(line)
 if not entries and not groups:raise ValueError('No supported skill requirements detected. Use a technical JD and review the vocabulary limitations.')
 for group in groups.values():
  for k in group['choices']:
   if k in entries and entries[k]['weight']<=group['weight']:entries.pop(k)
 return {'items':list(entries.values())+list(groups.values()),'manual_review':review,'jd_text':jd}


def evaluate(profile: Profile, req: dict, emitted_text: str|None=None) -> dict:
 evidence=profile.evidence();present=matches(emitted_text) if emitted_text is not None else set(evidence)
 rows=[]
 for item in req['items']:
  k=item['skill'];choices=item.get('choices',[k]);supported=any(c in evidence for c in choices);covered=any(c in evidence and c in present for c in choices)
  rows.append({**item,'supported':supported,'covered':covered,'resume_evidence':[e for c in choices for e in evidence.get(c,[])]})
 total=sum(r['weight'] for r in rows);covered=sum(r['weight'] for r in rows if r['covered'])
 raw=100*covered/total if total else 0
 manual=req['manual_review']
 return {'label':'Internal evidence-based keyword match — NOT a vendor ATS score', 'score':round(raw,1),
         'target_exceeded':raw>90 and not manual and len(rows)>=5,
         'requirements':rows,'manual_review_required':manual,
         'missing':[r['skill'] for r in rows if not r['supported']],
         'scoring_formula':'100 × covered requirement weights / all detected requirement weights. Required=3, general=2, preferred=1. No credit for unsupported skills. >90 requires at least five detected skills and no unresolved requirement lines.',
         'limits':['Finite skill vocabulary; not an exhaustive semantic assessment.','Years, location, work authorization, credentials, scope and compound requirements need human review.','A high score does not predict interviews or acceptance.']}


def flatten(profile: Profile) -> str:
 return '\n'.join([profile.name,profile.headline,*profile.contacts,'PROFESSIONAL SUMMARY',profile.summary,'TECHNICAL SKILLS',*profile.skills,'PROFESSIONAL EXPERIENCE',*[t for e in profile.experience for t in [e.heading,*e.bullets]],'EDUCATION',*profile.education])


def tailor(profile: Profile, req: dict, iteration: int=0) -> Profile:
 result=profile.model_copy(deep=True);weights={c:x['weight'] for x in req['items'] for c in x.get('choices',[x['skill']])}
 def relevance(t):return sum(weights.get(k,0) for k in matches(t))
 # Only reorders existing facts. Keywords are never inserted into an employer's history.
 for e in result.experience:
  e.bullets.sort(key=lambda t:(t.startswith('Led ') and 'Atlas' in t,-relevance(t)))
  if iteration:e.bullets=e.bullets[:max(2,7-iteration)]
 # Canonical names already supported by skill declarations or experience.
 supported=profile.evidence()
 ordered=sorted(supported,key=lambda k:(-weights.get(k,0),k))
 result.skills=[', '.join(ordered)]
 return result
