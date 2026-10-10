"""Public HTTPS JD retrieval. No login automation, executable HTML, or resume upload."""
import ipaddress,json,re,socket,urllib.request,urllib.parse
from html.parser import HTMLParser

class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','nav','footer'):self.hidden+=1
  if tag in ('p','div','li','br','h1','h2','h3'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style','nav','footer'):self.hidden=max(0,self.hidden-1)
 def handle_data(self,data):
  if not self.hidden:self.parts.append(data)

def html_text(raw):
 p=TextParser();p.feed(raw)
 return '\n'.join(' '.join(x.split()) for x in ''.join(p.parts).splitlines() if x.strip())

def validate_url(url):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise ValueError('Use a public HTTPS job URL without credentials or custom ports.')
 try:addrs=socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)
 except OSError as e:raise ValueError('Job hostname could not be resolved; paste the JD instead.') from e
 if not addrs or any(not ipaddress.ip_address(a[4][0]).is_global for a in addrs):raise ValueError('Local/private network job URLs are not allowed.')
 return u

class CheckedRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  validate_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_job(url):
 u=validate_url(url)
 # Greenhouse links often require JavaScript; retrieve the public posting API instead.
 parts=u.path.strip('/').split('/')
 if u.hostname in ('boards.greenhouse.io','job-boards.greenhouse.io') and len(parts)>=3 and parts[-2]=='jobs' and parts[-1].isdigit():
  url=f'https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(parts[0],safe="")}/jobs/{parts[-1]}?content=true'
  validate_url(url)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ResumeMatchAgent/0.1 (public job description reader)'})
  with urllib.request.build_opener(CheckedRedirect()).open(req,timeout=25) as r:
   raw=r.read(2_000_001)
   if len(raw)>2_000_000:raise ValueError('Job page exceeds 2 MB; paste the JD.')
   mime=r.headers.get_content_type();text=raw.decode('utf-8',errors='replace')
 except (OSError,urllib.error.URLError) as e:raise ValueError('Could not read the job link (network policy, login or site restriction). Paste the complete JD instead. '+str(e)) from e
 if mime=='application/json':
  d=json.loads(text)
  if 'content' not in d:raise ValueError('URL is not an individual job posting.')
  return d.get('title','')+'\n'+html_text(d['content'])
 if mime not in ('text/html','text/plain'):raise ValueError('Link did not return a readable job page. Paste the JD.')
 # Prefer JobPosting JSON-LD so navigation and unrelated vacancies don't affect scoring.
 for block in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',text,re.S|re.I):
  try:
   data=json.loads(block);nodes=data if isinstance(data,list) else [data]
   nodes+=[n for x in list(nodes) if isinstance(x,dict) for n in x.get('@graph',[])]
   for n in nodes:
    if isinstance(n,dict) and n.get('@type')=='JobPosting':return n.get('title','')+'\n'+html_text(n.get('description',''))
  except (ValueError,TypeError):continue
 result=html_text(text)
 if len(result)<120:raise ValueError('No complete JD extracted; paste the JD.')
 return result
