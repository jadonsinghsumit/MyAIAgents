from pathlib import Path
from html import escape
import re
from .core import Profile, SKILLS

def export(profile: Profile, destination: Path, photo: Path|None=None, label: str=""):
 """Render a one-page selectable PDF and editable DOCX; never shrink below 9pt."""
 from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,HRFlowable
 from reportlab.lib.styles import ParagraphStyle
 from reportlab.lib.colors import HexColor
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.ttfonts import TTFont
 from docx import Document
 from docx.shared import Inches,Pt,RGBColor
 import fitz
 destination.mkdir(parents=True,exist_ok=True)
 font='Helvetica'
 fontdir=Path('/usr/share/fonts/truetype/liberation')
 if (fontdir/'LiberationSans-Regular.ttf').exists():
  font='ResumeSans';pdfmetrics.registerFont(TTFont(font,str(fontdir/'LiberationSans-Regular.ttf')))
  pdfmetrics.registerFont(TTFont(font+'-Bold',str(fontdir/'LiberationSans-Bold.ttf')))
  pdfmetrics.registerFontFamily(font,normal=font,bold=font+'-Bold',italic=font,boldItalic=font+'-Bold')
 regex=re.compile(r'(?<!\w)(?:'+'|'.join(a for aliases in SKILLS.values() for a in aliases)+r')(?!\w)',re.I)
 def marked(t):
  end=0;out=[]
  for m in regex.finditer(t):out.extend([escape(t[end:m.start()]),'<b>'+escape(m.group())+'</b>']);end=m.end()
  return ''.join(out)+escape(t[end:])
 body=ParagraphStyle('b',fontName=font,fontSize=9,leading=11,spaceAfter=4,textColor=HexColor('#273444'))
 heading=ParagraphStyle('h',parent=body,fontName=font+'-Bold',textColor=HexColor('#17354F'),fontSize=10,leading=12,spaceBefore=7,spaceAfter=4)
 title=ParagraphStyle('title',parent=heading,fontSize=20,leading=23,spaceBefore=0)
 contact=ParagraphStyle('contact',parent=body,rightIndent=85 if photo else 0)
 bullet=ParagraphStyle('bullet',parent=body,leftIndent=10,bulletIndent=0)
 story=[Paragraph(escape(profile.name),title),Paragraph(escape(profile.headline),contact)]
 story.extend(Paragraph(escape(c),contact) for c in profile.contacts)
 story.extend([Spacer(1,3),HRFlowable(width='100%',thickness=1,color=HexColor('#17354F'))])
 for name,items in [('PROFESSIONAL SUMMARY',[profile.summary]),('TECHNICAL SKILLS',profile.skills)]:
  story.append(Paragraph(name,heading));story.extend(Paragraph(marked(t),body) for t in items)
 story.append(Paragraph('PROFESSIONAL EXPERIENCE',heading))
 for exp in profile.experience:
  story.append(Paragraph(escape(exp.heading),heading))
  story.extend(Paragraph(marked(t),bullet,bulletText='•') for t in exp.bullets)
 story.append(Paragraph('EDUCATION',heading));story.extend(Paragraph(marked(t),body) for t in profile.education)
 def draw(canvas,doc):
  if label:
   canvas.setFont(font,7);canvas.setFillColor(HexColor('#566574'));canvas.drawRightString(561,16,label)
  if photo:canvas.drawImage(str(photo),491,709.89,width=70,height=105,preserveAspectRatio=True,mask='auto')
 pdf=destination/'resume.pdf'
 SimpleDocTemplate(str(pdf),pagesize=(595.28,841.89),leftMargin=34,rightMargin=34,topMargin=27,bottomMargin=27).build(story,onFirstPage=draw)
 with fitz.open(pdf) as d:
  pages=len(d);extracted='\n'.join(p.get_text() for p in d)
 # DOCX matches content; exact pagination varies by Word/font implementation.
 d=Document();s=d.sections[0];s.page_width=Inches(8.27);s.page_height=Inches(11.69)
 s.top_margin=s.bottom_margin=Inches(.38);s.left_margin=s.right_margin=Inches(.48)
 n=d.styles['Normal'];n.font.name='Calibri';n.font.size=Pt(9);n.paragraph_format.space_after=Pt(3)
 def paragraph(text,style=None,bold=False):
  p=d.add_paragraph(style=style);end=0
  for m in regex.finditer(text):p.add_run(text[end:m.start()]);p.add_run(m.group()).bold=True;end=m.end()
  p.add_run(text[end:])
  if bold:
   for r in p.runs:r.bold=True;r.font.color.rgb=RGBColor.from_string('17354F')
  return p
 if photo:
  table=d.add_table(rows=1,cols=2);table.columns[0].width=Inches(6.2);table.columns[1].width=Inches(1)
  left=table.cell(0,0);left.paragraphs[0].add_run(profile.name).bold=True
  for text in [profile.headline,*profile.contacts]:left.add_paragraph(text)
  table.cell(0,1).paragraphs[0].add_run().add_picture(str(photo),width=Inches(.97),height=Inches(1.455))
 else:
  p=paragraph(profile.name,bold=True);p.runs[0].font.size=Pt(20)
  paragraph(profile.headline)
  for c in profile.contacts:paragraph(c)
 for name,items in [('PROFESSIONAL SUMMARY',[profile.summary]),('TECHNICAL SKILLS',profile.skills)]:
  paragraph(name,bold=True)
  for t in items:paragraph(t)
 paragraph('PROFESSIONAL EXPERIENCE',bold=True)
 for exp in profile.experience:
  paragraph(exp.heading,bold=True)
  for t in exp.bullets:paragraph(t,'List Bullet')
 paragraph('EDUCATION',bold=True)
 for t in profile.education:paragraph(t)
 if label:
  footer=s.footer.paragraphs[0];footer.alignment=2
  r=footer.add_run(label);r.font.size=Pt(7);r.font.color.rgb=RGBColor.from_string('566574')
 d.save(destination/'resume.docx')
 return {'pages':pages,'text':extracted,'pdf':str(pdf),'docx':str(destination/'resume.docx')}
