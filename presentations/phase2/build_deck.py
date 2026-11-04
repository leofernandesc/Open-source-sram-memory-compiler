#!/usr/bin/env python3
"""Build editable PPTX from slides.json and verified project evidence.

No simulator or physical tool is launched. --refresh-figures reads existing
full transient files; normal editing reuses the checked-in PNGs and hashes.
"""
import argparse,hashlib,json,sys,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;ASSETS=OUT/'assets'
NAVY='132A46';BLUE='245C91';TEAL='24756C';GRAY='596776';LIGHT='F2F5F8';INK='202D3C';WHITE='FFFFFF';MUTED='DCE4EB';ORANGE='A96316'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def color(s):return RGBColor.from_string(s)
def trace(rel):
 source=ROOT/rel;s=json.loads((source/'results.json').read_text());raw=ROOT/s['build_directory']/'waveform.dat'
 if sha(raw)!=s['raw_waveform_sha256']:raise ValueError('Raw changed: '+rel)
 return s,np.loadtxt(raw,skiprows=1),{'receipt':rel+'/results.json','receipt_sha256':sha(source/'results.json'),'raw_sha256':sha(raw)}
def figures():
 ASSETS.mkdir(exist_ok=True);meta={}
 for dest,src in [('layout.png','reports/phase2/layout_overview/sram_4x8.png'),('phase_guard.png','reports/phase2/phase_guard_review/write_precharge_guard.png')]:
  shutil.copyfile(ROOT/src,ASSETS/dest);meta[dest]={'kind':'Actual project evidence image','source':src,'source_sha256':sha(ROOT/src)}
 s,d,origin=trace('reports/phase2/final_polish_20261104/startup_extended/r1_idle2');t=d[:,0]*1e9
 col=lambda n:s['vectors'].index(s['probes'][n])+1
 panels=[ [('CLK',col('CLK')),('PCLK',9),('PRECH',10)], [('WE',12),('WL1',14),('SCLK',11)], [('BL0',col('BL0')),('BLB0',col('BLB0'))], [('SA_OUT / RAW0',17),('FF_Q0',col('REG_Q0')),('DATA0',1)]]
 fig,axes=plt.subplots(4,1,figsize=(12,4.6),sharex=True)
 palette=['#245c91','#24756c','#ad6c22','#776aa3']
 for ax,group in zip(axes,panels):
  for k,(label,c) in enumerate(group):ax.plot(t,d[:,c],label=label,color=palette[k],lw=1.5)
  ax.set_ylabel('V',fontsize=10);ax.set_ylim(-.12,2);ax.set_yticks([0,1.8]);ax.legend(loc='upper right',ncol=3,fontsize=9,frameon=False);ax.grid(alpha=.18)
 axes[-1].set_xlim(48,88);axes[-1].set_xlabel('Tempo (ns) · escrita e leitura reais, linha 1',fontsize=11)
 fig.tight_layout(pad=.6);fig.savefig(ASSETS/'access_phases.png',dpi=180);plt.close(fig)
 meta['access_phases.png']={'kind':'Measured full-resolution trace, selected 48..88 ns window',**origin,'columns':panels,'condition':'TT/1.8 V/27 C, no wire RC'}
 s,d,origin=trace('reports/phase2/final_polish_20261104/startup_reduced/r1_idle0');t=d[:,0]*1e9;col=lambda n:s['vectors'].index(s['probes'][n])+1
 fig,axes=plt.subplots(3,1,figsize=(10,3.6),sharex=True)
 for ax,group in zip(axes,[[('WL0',13),('WE',12)],[('Q célula [0,0]',col('CELL_0_0')),('Q célula [1,0]',col('CELL_1_0'))],[('DATA0',1),('FF_Q0',col('REG_Q0'))]]):
  for k,(label,c) in enumerate(group):ax.plot(t,d[:,c],label=label,color=palette[k],lw=1.5)
  ax.set_ylim(-.12,2);ax.set_yticks([0,1.8]);ax.set_ylabel('V');ax.grid(alpha=.18);ax.legend(loc='upper left',ncol=2,fontsize=9,frameon=False)
 axes[-1].set_xlim(8,147);axes[-1].set_xlabel('Tempo (ns) · escrita 00 e reescrita FF na linha 0',fontsize=10)
 fig.tight_layout(pad=.5);fig.savefig(ASSETS/'storage_readback.png',dpi=180);plt.close(fig)
 meta['storage_readback.png']={'kind':'Actual startup experiment, storage and public output observations',**origin,'window_ns':[8,147],'interpretation':'Illustrates storage; directed-campaign counters come from their separate receipt'}
 fig,ax=plt.subplots(figsize=(6,3.2));sources=[]
 for k,n in enumerate(['r1_idle2','r5_idle2','r10_idle2']):
  s,d,o=trace('reports/phase2/final_polish_20261104/startup_extended/'+n);v=s['vectors'].index(s['probes']['VDD'])+1
  ax.plot(d[:,0]*1e9,d[:,v],label=f"Rampa {s['scenario']['ramp_ns']} ns",color=palette[k],lw=2);sources.append(o)
 ax.set_xlim(0,15);ax.set_ylim(-.05,2);ax.set_xlabel('Tempo (ns)');ax.set_ylabel('VDD (V)');ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=11)
 fig.tight_layout();fig.savefig(ASSETS/'startup_ramps.png',dpi=180);plt.close(fig)
 meta['startup_ramps.png']={'kind':'Actual VDD traces from three independent runs','sources':sources,'window_ns':[0,15]}
 for n,m in meta.items():m.update(sha256=sha(ASSETS/n),pixels=list(Image.open(ASSETS/n).size))
 (ASSETS/'sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--refresh-figures',action='store_true');a=p.parse_args()
 if a.refresh_figures:figures()
 sources=json.loads((ASSETS/'sources.json').read_text())
 for n,s in sources.items():
  if sha(ASSETS/n)!=s['sha256']:raise ValueError('Changed presentation asset: '+n)
 slides=json.loads((OUT/'slides.json').read_text());assert len(slides)==22
 prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
 def box(s,x,y,w,h,fill=LIGHT,line=None):
  z=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h));z.fill.solid();z.fill.fore_color.rgb=color(fill)
  z.line.color.rgb=color(line or fill);z.adjustments[0]=.08;return z
 def text(s,x,y,w,h,string,size=18,fg=INK,bold=False,align=PP_ALIGN.LEFT):
  z=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=z.text_frame;tf.clear();tf.word_wrap=True
  tf.margin_left=Pt(0);tf.margin_right=Pt(0);tf.margin_top=Pt(0);tf.margin_bottom=Pt(0)
  for i,l in enumerate(string.split('\n')):
   p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=l;p.font.name='DejaVu Sans';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color(fg);p.alignment=align;p.space_after=Pt(4)
  return z
 def arrow(s,x1,y1,x2,y2,ink=GRAY):
  z=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));z.line.color.rgb=color(ink);z.line.width=Pt(1.5)
  from pptx.oxml.xmlchemy import OxmlElement
  end=OxmlElement('a:tailEnd');end.set('type','triangle');z.line._get_or_add_ln().append(end)
 def card(s,x,y,w,h,title,body,accent=BLUE):
  box(s,x,y,w,h);text(s,x+.22,y+.2,w-.44,.5,title,21,accent,True);text(s,x+.22,y+.86,w-.44,h-1,body,17)
 def bullet_list(s,ss,x=.65,y=1.68,w=5.6,step=1.03,size=17.5):
  for k,b in enumerate(ss):
   text(s,x,y+k*step,.22,.4,'•',size,TEAL,True);text(s,x+.3,y+k*step,w-.3,.94,b,size)
 def picture(s,name,x,y,w,h):
  path=ASSETS/name;im=Image.open(path);rw,rh=im.size;scale=min(w/rw,h/rh);ww,hh=rw*scale,rh*scale
  s.shapes.add_picture(str(path), Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),width=Inches(ww),height=Inches(hh))
 def table(s,x,y,width,headers,rows,widths=None,fontsize=16):
  shape=s.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(width),Inches(.48*(len(rows)+1)));tab=shape.table
  if widths:
   for c,w in zip(tab.columns,widths):c.width=Inches(w)
  for r,values in enumerate([headers,*rows]):
   for c,value in enumerate(values):
    cell=tab.cell(r,c);cell.text=str(value);cell.fill.solid();cell.fill.fore_color.rgb=color(NAVY if r==0 else (LIGHT if r%2 else WHITE));cell.margin_left=Inches(.13);cell.margin_top=Inches(.075)
    for par in cell.text_frame.paragraphs:
     par.font.name='DejaVu Sans';par.font.size=Pt(fontsize);par.font.bold=r==0;par.font.color.rgb=color(WHITE if r==0 else INK)
  return tab
 for i,d in enumerate(slides,1):
  s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=color(WHITE)
  text(s,.65,.28,11.8,.3,d['kicker'],11,BLUE,True)
  if i!=1:text(s,.65,.78,12,.7,d['title'],30,NAVY,True)
  box(s,.65,6.55,12,.48,LIGHT);text(s,.84,6.64,11.62,.35,d['takeaway'],11.4 if i==22 else 12.4,NAVY,True)
  text(s,.65,7.13,11.6,.2,'SRAM 4×8 · SKY130A · evidências: slides.json / assets/sources.json',8.2,GRAY)
  text(s,12.05,7.06,.65,.3,f'{i:02d} / 22',9,GRAY)
  kind=d['kind']
  if kind=='cover':
   text(s,.65,1.35,8.1,1.9,d['title'],37,NAVY,True);text(s,.68,3.55,7.8,1.1,d['bullets'][0],20,GRAY)
   text(s,.68,5.15,8,.55,d['bullets'][1],17,INK)
   box(s,9.3,1.5,3.3,4.3,NAVY);text(s,9.55,1.8,2.8,.65,'4 × 8',38,WHITE,True,PP_ALIGN.CENTER)
   for r in range(4):
    for c in range(8):box(s,9.65+c*.32,2.75+r*.37,.23,.23,'6AB3AA')
   text(s,9.55,4.55,2.8,.5,'1.493 MOS',24,WHITE,True,PP_ALIGN.CENTER);text(s,9.55,5.16,2.8,.35,'Protótipo físico',13,'C6D8E8',False,PP_ALIGN.CENTER)
  elif kind=='cards':
   for k,b in enumerate(d['bullets']):card(s,.65+k*4.08,1.85,3.85,3.9,['Circuito','Automação','Protótipo'][k],b)
  elif kind=='gates':
   card(s,.65,1.8,5.85,3.9,'F2-DIG',d['bullets'][0],BLUE);card(s,6.8,1.8,5.85,3.9,'F2-FIS',d['bullets'][1],TEAL)
   text(s,.9,4.8,5.3,.55,'RTL → Yosys → SKY130HD → GLS',16,BLUE,True);text(s,7.05,4.8,5.3,.8,'Células → layout → GDS → DRC/LVS\n→ acesso transistor-level',16,TEAL,True)
  elif kind=='leaves':
   table(s,.65,1.75,8.4,['Família','Qtd.','MOS/cél.','Total'],[['Bitcell 6T',32,6,192],['Decoder dinâmico',1,33,33],['Wordline driver',4,4,16],['Precharge',8,3,24],['Write driver',8,10,80],['Sense amplifier',8,7,56]], [4,1,1.7,1.7])
   text(s,9.45,2.2,3,.85,'401',52,TEAL,True);text(s,9.45,3.2,2.8,1.2,'MOS das seis\nfamílias selecionadas',19)
   text(s,.85,5.56,11.6,.5,'Decoder oficial: 33 MOS, incluindo quatro PMOS keepers.',18,NAVY,True)
  elif kind=='architecture':
   text(s,.7,1.52,12,.4,'Diagrama funcional explicativo · azul = SKY130HD · verde = custom',12,GRAY)
   for x,y,w,h,t,fill in [(.7,2.2,2.2,1.2,'Interface\nADDR / DATA / CTRL',BLUE),(3.4,2.2,2.45,1.2,'Captura na subida\n12 FF',BLUE),(3.4,4.55,2.45,1.2,'Captura na descida\n8 FF',BLUE),(.7,4.55,2.2,1.2,'8 tri-states\nDATA externo',BLUE),(6.4,1.9,2.4,.85,'Fases internas\n80 inversores HD',BLUE),(9.2,1.9,3.25,.85,'Decoder + WL drivers',TEAL),(6.4,3.25,6.05,1.0,'Matriz 6T · 4 linhas × 8 colunas',TEAL),(6.4,4.85,1.8,.9,'Precharge',TEAL),(8.5,4.85,1.8,.9,'Write',TEAL),(10.6,4.85,1.85,.9,'Sense',TEAL)]:
    box(s,x,y,w,h,fill);text(s,x+.12,y+.17,w-.24,h-.2,t,15.5,WHITE,True,PP_ALIGN.CENTER)
   arrow(s,2.9,2.8,3.4,2.8);arrow(s,5.85,2.8,6.4,2.35);arrow(s,8.8,2.35,9.2,2.35);arrow(s,10.8,2.75,10.8,3.25)
   for x in [7.3,9.4]:arrow(s,x,4.85,x,4.25)
   arrow(s,11.5,4.25,11.5,4.85)
   arrow(s,5.85,3.08,9.02,3.08,BLUE);arrow(s,9.02,3.08,9.02,2.63,BLUE);arrow(s,9.02,2.63,9.2,2.63,BLUE)
   text(s,6.55,2.8,1.8,.25,'ADDR_Q',11,BLUE,True)
   arrow(s,5.85,3.27,6.1,3.27,BLUE);arrow(s,6.1,3.27,6.1,4.55,BLUE);arrow(s,6.1,4.55,9.4,4.55,BLUE);arrow(s,9.4,4.55,9.4,4.85,BLUE)
   text(s,6.55,4.28,1.5,.25,'DIN_Q',11,BLUE,True)
   arrow(s,11.5,5.75,11.5,6.04);arrow(s,11.5,6.04,6.12,6.04);arrow(s,6.12,6.04,6.12,5.3);arrow(s,6.12,5.3,5.85,5.3)
   text(s,7.7,5.78,3,.25,'DOUT_RAW → FF de leitura',10,TEAL,True);arrow(s,3.4,5.15,2.9,5.15)
   text(s,.7,6.24,11.8,.24,'CTRL = CSb / OEb / WEb; VDD e VSS conectados em todas as células.',12,GRAY)
  elif kind=='protocol':
   bullet_list(s,d['bullets'],w=6,step=1.1)
   table(s,7.2,1.75,5.2,['CSb/OEb/WEb','Novo pedido'],[['001','READ'],['010','WRITE'],['000','Inválido'],['011','Idle'],['1xx','Desabilitado']],[2.65,2.55],16)
   text(s,7.2,5.05,5.1,1.0,'drive_DATA = READ_Q\nAND controles vivos = 001',17,TEAL,True)
  elif kind=='hierarchy':
   for k,(name,role) in enumerate([('sram_model','Comportamento público'),('sram_controller + wrapper','Captura + registro de leitura'),('macro_model','Somente simulação funcional'),('macro_bb → binding físico','Black box → circuito real')]):
    box(s,.65,1.7+k*1.08,5.2,.8,BLUE if k<2 else TEAL);text(s,.85,1.88+k*1.08,4.8,.45,name,18,WHITE,True);text(s,6.2,1.88+k*1.08,6.1,.7,role,19)
  elif kind in ['digital_checks','synthesis','results']:
   bullet_list(s,d['bullets'])
   nums={'digital_checks':[('154.303','checks RTL'),('2.048','operações pseudoaleatórias')],'synthesis':[('20 FF / 8 tri','células físicas mapeadas'),('15.619','checks GLS')],'results':[('1.493 MOS','integração física'),('DRC 0 / LVS','geometria e conectividade')]}[kind]
   for k,(a,b) in enumerate(nums):box(s,7,1.85+k*2.1,5.5,1.8);text(s,7.28,2.06+k*2.1,4.95,.7,a,32,TEAL if k else BLUE,True);text(s,7.3,2.95+k*2.1,4.9,.5,b,16,GRAY)
  elif kind=='binding':
   bullet_list(s,d['bullets'],w=5.8)
   for k,(a,b) in enumerate([('24','liberação PRECH'),('40','WE'),('60','PCLK / avaliação'),('80','SCLK / recuperação')]):
    box(s,7,1.78+k*1.08,5.5,.87);text(s,7.2,1.9+k*1.08,.8,.5,a,23,BLUE,True);text(s,8.1,1.97+k*1.08,4.1,.55,b,17)
  elif kind=='decoder':
   bullet_list(s,d['bullets'],w=6.25,step=1.1,size=17)
   for k,t in enumerate(['VDD → PMOS pré-carga','N[i] + PMOS keeper','Rede NMOS de endereço','Footer compartilhado → VSS']):
    box(s,7.2,1.65+k*1.04,5.15,.77,TEAL if k==1 else LIGHT);text(s,7.4,1.82+k*1.04,4.75,.48,t,17,WHITE if k==1 else INK,True)
    if k<3:arrow(s,9.77,2.42+k*1.04,9.77,2.65+k*1.04)
   text(s,7.25,5.95,5,.3,'Representação funcional simplificada',11,GRAY)
  elif kind=='generator':
   bullet_list(s,d['bullets'],w=5.85)
   for r in range(4):
    for c in range(8):box(s,7.05+c*.65,2+r*.65,.51,.48,TEAL)
    text(s,6.4,2.1+r*.65,.6,.3,f'WL{r}',10,TEAL,True)
   text(s,7.15,1.57,5,.3,'Organização lógica explicativa (não é layout)',11,GRAY)
   text(s,7.05,5.1,5.3,.9,'32 bitcells / 8 pares BL–BLB\n16 gates de acesso por WL',18,NAVY,True)
  elif kind=='layout':
   picture(s,'layout.png',.6,1.48,8.35,4.9);bullet_list(s,d['bullets'],x=9.2,y=1.9,w=3.45,step=1.32,size=17)
  elif kind=='phases':
   picture(s,'access_phases.png',.65,1.55,12,4.78)
  elif kind=='issues':
   picture(s,'phase_guard.png',.65,1.6,7.1,4.55);bullet_list(s,d['bullets'],x=8.05,y=1.8,w=4.6,step=1.42,size=16)
  elif kind=='physical_checks':
   bullet_list(s,d['bullets'],w=6.4,size=17)
   card(s,7.7,1.9,4.8,1.75,'DRC = 0','Geometria do GDS final',TEAL)
   card(s,7.7,4,4.8,1.85,'LVS match','Gate / bulk / W / L: erros rejeitados',BLUE)
  elif kind=='electrical':
   picture(s,'storage_readback.png',.65,1.55,8.2,4.65);bullet_list(s,d['bullets'],x=9.15,y=1.8,w=3.45,step=1.45,size=16)
  elif kind=='timing':
   bullet_list(s,d['bullets'],w=6.3,step=1.14,size=17)
   for k,t in enumerate(['SA_OUT = DOUT_RAW','Mux → FF_D','Captura local → FF_Q','Enable vivo → DATA / Z']):
    box(s,7.4,1.75+k*1.08,5,.8);text(s,7.6,1.92+k*1.08,4.6,.5,t,18,BLUE,True)
  elif kind=='startup':
   picture(s,'startup_ramps.png',.65,1.7,5.45,3.65)
   table(s,6.5,1.75,6.0,['Rampa','Idle','Checks','Estado'],[['1 ns',0,637,'PASS'],['1 ns',2,681,'PASS'],['5 ns',2,681,'PASS'],['10 ns',2,681,'PASS'],['1 ns',3,703,'PASS']],fontsize=15)
   text(s,.85,5.58,11.65,.5,'3.383 checks totais, incluindo 240 bits lidos; sem falhas.',21,TEAL,True)
  elif kind=='limits':
   for k,b in enumerate(d['bullets']):card(s,.65+(k%2)*6.15,1.75+(k//2)*2.13,5.85,1.9,['Timing','Variabilidade','Caracterização','Escala física'][k],b,ORANGE)
  elif kind=='closing':
   text(s,.75,1.8,11.8,1.5,'Uma SRAM física verificável,\ncom seus limites explícitos.',34,NAVY,True)
   bullet_list(s,d['bullets'],y=3.7,w=11.8,step=.75,size=19)
  note=s.notes_slide.notes_text_frame;note.text=f"Objetivo: {d['takeaway']}\n\n{d['speech']}\n\nRessalva: {d['caveat']}\n\nTransição: {d['transition']}\n\nFontes: "+'\n'.join(d['source'])
 prs.core_properties.title='Open-Source SRAM Memory Compiler — Phase 2';prs.core_properties.subject='Experimental 4x8 SKY130 integration review';prs.core_properties.author='SRAM project team'
 dest=OUT/'phase2_technical_review.pptx';prs.save(dest)
 check=Presentation(dest);assert len(check.slides)==22
 outside=[]
 for i,s in enumerate(check.slides,1):
  for z in s.shapes:
   if z.left<0 or z.top<0 or z.left+z.width>check.slide_width+1000 or z.top+z.height>check.slide_height+1000:outside.append((i,z.name))
 if outside:raise ValueError('Shape outside slide: '+str(outside))
 print(json.dumps({'slides':22,'pptx_bytes':dest.stat().st_size,'editable_text':True,'native_diagrams':True,'bounds':'PASS'}))
if __name__=='__main__':main()
