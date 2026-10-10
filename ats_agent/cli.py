import argparse,json,sys
from pathlib import Path
from .core import load_profile
from .fetch import fetch_job
from .workflow import run

def main():
 p=argparse.ArgumentParser(description='Truthful one-page resume tailoring with an internal JD match metric.')
 p.add_argument('--resume',type=Path,required=True,help='PDF/DOCX/TXT or reviewed profile JSON')
 g=p.add_mutually_exclusive_group(required=True);g.add_argument('--jd',type=Path);g.add_argument('--url')
 p.add_argument('--company',required=True,help='Company short name, e.g. CISCO or PAN')
 p.add_argument('--out',type=Path,required=True);p.add_argument('--photo',type=Path)
 a=p.parse_args()
 try:
  profile=load_profile(a.resume);jd=fetch_job(a.url) if a.url else a.jd.read_text()
  if a.out.exists() and any(a.out.iterdir()):raise ValueError('Output directory is not empty. Choose a new directory to preserve earlier results.')
  report=run(profile,jd,a.out,a.photo,source=a.url or str(a.jd),company=a.company)
  print(json.dumps({'status':report['status'],'score':report['after']['score'],'pages':report['pages'],'output':str(a.out)},indent=2))
 except (ValueError,OSError) as e:print(str(e),file=sys.stderr);return 2
 return 0

if __name__=='__main__':raise SystemExit(main())
