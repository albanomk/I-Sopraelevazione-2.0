"""Motore verificabile: nessuna stima non calibrata viene considerata misura."""
from __future__ import annotations
import io, re
import numpy as np
import pandas as pd
import fitz
from PIL import Image

COLS=['progressiva_m','h_mm','rotaia_alzata','verificato']

def km(s):
    s=str(s).strip().replace(' ', '').replace('km','').replace('KM','')
    if not s: raise ValueError('progressiva assente')
    if '+' in s:
        a,b=s.split('+',1);return float(a.replace(',','.'))*1000+float(b.replace(',','.'))
    s=s.replace(',','.')
    return float(s)*1000 if float(s)<100 and '.' in s else float(s)

def fmt_km(m):
    if pd.isna(m):return 'dato non leggibile'
    return f'{int(m//1000)}+{m%1000:06.2f}'.replace('.',',')

def pages(data,scale=2):
    doc=fitz.open(stream=data,filetype='pdf')
    for p in doc:
        pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
        yield Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')

def tabellino_ocr(data,language='ita'):
    """OCR preliminare: le righe non sono mai verificate automaticamente."""
    import pytesseract
    results=[]
    for pi,im in enumerate(pages(data,3),1):
        # Tabellino: le colonne progressive/h/rotaia occupano circa x 26-75%.
        txt=pytesseract.image_to_data(im,lang=language,config='--psm 6',output_type=pytesseract.Output.DATAFRAME)
        txt=txt.dropna(subset=['text'])
        txt=txt[txt.conf>=40]
        txt['text']=txt.text.astype(str)
        for (_,_,_,line),g in txt.groupby(['block_num','par_num','line_num','top'],sort=True):
            words=g.sort_values('left');line_text=' '.join(words.text)
            # Estrazione conservativa: propone soltanto progressive riconoscibili.
            for match in re.finditer(r'(?<!\d)(\d{1,2})\s*[+\-]\s*(\d{3})[.,](\d{1,3})(?!\d)',line_text):
                try: prog=km(f'{match.group(1)}+{match.group(2)}.{match.group(3)}')
                except ValueError:continue
                results.append({'progressiva_m':prog,'h_mm':np.nan,'rotaia_alzata':'','verificato':False,'pagina':pi,'testo_ocr':line_text})
    return pd.DataFrame(results,columns=COLS+['pagina','testo_ocr'])

def normalize_project(df):
    d=df.copy()
    for c in COLS:
        if c not in d: d[c]=np.nan if c in ('progressiva_m','h_mm') else (False if c=='verificato' else '')
    d['progressiva_m']=pd.to_numeric(d.progressiva_m,errors='coerce')
    d['h_mm']=pd.to_numeric(d.h_mm,errors='coerce')
    d['rotaia_alzata']=d.rotaia_alzata.astype(str).str.strip().str.lower().replace({'sinistra':'sx','destra':'dx','nan':''})
    d['verificato']=d.verificato.fillna(False).astype(bool)
    d=d[d.progressiva_m.notna()].sort_values('progressiva_m')
    return d

def trace(im, x0,x1,km0,km1,y0,v0,y1,v1,band_top,band_bottom,step_m=5, max_jump_px=9):
    """Traccia candidata da pixel scuri: non è una misura finché l'utente non la convalida."""
    import cv2
    arr=np.array(im.convert('RGB'));gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
    H,W=gray.shape
    if abs(x1-x0)<20 or abs(y1-y0)<5 or abs(km1-km0)<10:raise ValueError('Calibrazione insufficiente')
    if not (0<=band_top<band_bottom<H):raise ValueError('Fascia non valida')
    if abs(v1-v0)<1:raise ValueError('Due valori verticali distinti necessari')
    dx=(km1-km0)/(x1-x0); result=[];previous=None
    n=max(2,int(abs(km1-km0)/step_m)+1)
    for p in np.linspace(min(km0,km1),max(km0,km1),n):
        x=int(round(x0+(p-km0)/dx))
        if x<2 or x>=W-2:continue
        ys=np.arange(band_top,band_bottom)
        # Scarta linee verticali di griglia: colonna quasi tutta scura.
        roi=gray[band_top:band_bottom,max(0,x-1):min(W,x+2)]
        dark=(roi<105).sum(axis=1)
        if (dark>0).mean()>.45:
            result.append((p,np.nan,False,'griglia/ostacolo'));continue
        candidates=ys[dark>=1]
        if previous is not None:candidates=candidates[np.abs(candidates-previous)<=max_jump_px]
        if len(candidates)==0:
            result.append((p,np.nan,False,'traccia non identificabile'));continue
        # Se due tracce separate plausibili, non sceglie arbitrariamente.
        groups=np.split(candidates,np.where(np.diff(candidates)>2)[0]+1)
        groups=[g for g in groups if len(g)>0]
        if len(groups)>1:
            result.append((p,np.nan,False,'più tracce possibili'));continue
        yy=float(np.median(groups[0]));previous=yy
        val=v0+(yy-y0)*(v1-v0)/(y1-y0)
        result.append((p,round(val,2),False,'da verificare'))
    return pd.DataFrame(result,columns=['progressiva_m','rilevato_mm','verificato','nota'])

def compare(project,measure,tolerance=10,orange=160,red=160,step_m=5):
    if red<orange:raise ValueError('La soglia rossa non può essere inferiore all’arancione')
    p=normalize_project(project)
    m=measure.copy()
    m['progressiva_m']=pd.to_numeric(m.progressiva_m,errors='coerce')
    m['rilevato_mm']=pd.to_numeric(m.rilevato_mm,errors='coerce')
    m=m.dropna(subset=['progressiva_m']).sort_values('progressiva_m')
    rows=[]
    # Interpolazione SOLO fra punti di progetto verificati e consecutivi, senza attraversare buchi.
    for _,r in m.iterrows():
        x=float(r.progressiva_m); rec={'progressiva_m':x,'rilevato_mm':r.rilevato_mm,'progetto_mm':np.nan,'scostamento_mm':np.nan,'codice':'NON LEGGIBILE','motivo':'dato non leggibile'}
        if not bool(r.get('verificato',False)) or pd.isna(r.rilevato_mm):
            rec['motivo']='rilievo non verificato o dato non leggibile';rows.append(rec);continue
        candidates=p[(p.progressiva_m<=x)&(p.verificato)&(p.h_mm.notna())&(p.rotaia_alzata.isin(['sx','dx']))]
        upper=p[(p.progressiva_m>=x)&(p.verificato)&(p.h_mm.notna())&(p.rotaia_alzata.isin(['sx','dx']))]
        if candidates.empty or upper.empty:
            rec['motivo']='progetto non disponibile o non verificato';rows.append(rec);continue
        a=candidates.iloc[-1];b=upper.iloc[0]
        # Non interpolare attraverso discontinuità, variazioni rotaia, grandi intervalli.
        if b.progressiva_m-a.progressiva_m>max(100,step_m*20) or a.rotaia_alzata!=b.rotaia_alzata:
            rec['motivo']='intervallo progetto ambiguo';rows.append(rec);continue
        ha=abs(a.h_mm)*(1 if a.rotaia_alzata=='sx' else -1)
        hb=abs(b.h_mm)*(1 if b.rotaia_alzata=='sx' else -1)
        target=ha if a.progressiva_m==b.progressiva_m else ha+(hb-ha)*(x-a.progressiva_m)/(b.progressiva_m-a.progressiva_m)
        dev=float(r.rilevato_mm)-target
        code='VERDE'
        if abs(dev)>tolerance:code='GIALLO'
        # Arancio solo per sopraelevazione non prevista dal progetto e sotto soglia assoluta.
        if abs(target)<=tolerance and abs(r.rilevato_mm)>tolerance and abs(r.rilevato_mm)<=orange:code='ARANCIONE'
        if abs(r.rilevato_mm)>red:code='ROSSO'
        rec.update(progetto_mm=round(target,2),scostamento_mm=round(dev,2),codice=code,motivo='')
        rows.append(rec)
    return pd.DataFrame(rows)

def aggregate(detail,step_m=5):
    if detail.empty:return pd.DataFrame(columns=['da_km','a_km','codice','esito','punti','scostamento_massimo_mm'])
    d=detail.sort_values('progressiva_m').reset_index(drop=True)
    out=[];start=0
    def emit(a,b):
        z=d.iloc[a:b+1];c=z.iloc[0].codice
        out.append({'da_km':fmt_km(z.progressiva_m.min()),'a_km':fmt_km(z.progressiva_m.max()),'codice':c,'esito':'Nessun alert' if c=='VERDE' else ('dato non leggibile' if c=='NON LEGGIBILE' else f'Alert {dict(GIALLO=1,ARANCIONE=2,ROSSO=3)[c]}'), 'punti':len(z),'scostamento_massimo_mm':z.scostamento_mm.abs().max()})
    for i in range(1,len(d)):
        if d.loc[i,'codice']!=d.loc[i-1,'codice'] or d.loc[i,'progressiva_m']-d.loc[i-1,'progressiva_m']>step_m*1.51:
            emit(start,i-1);start=i
    emit(start,len(d)-1)
    return pd.DataFrame(out)

def excel_bytes(project,detail,summary):
    import openpyxl
    from openpyxl.styles import PatternFill,Font,Alignment
    from openpyxl.utils import get_column_letter
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine='openpyxl') as writer:
        for name,df in [('Tabellino',project),('Dettaglio',detail),('Report aggregato',summary)]:
            df.to_excel(writer,sheet_name=name,index=False)
            ws=writer.sheets[name];ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
            for c in ws[1]:c.fill=PatternFill('solid',fgColor='12304A');c.font=Font(color='FFFFFF',bold=True)
            for col in ws.columns:
                width=min(48,max(13,max(len(str(cell.value or '')) for cell in col)+2))
                ws.column_dimensions[get_column_letter(col[0].column)].width=width
            colors={'VERDE':'C8E6C9','GIALLO':'FFF59D','ARANCIONE':'FFCC80','ROSSO':'EF9A9A','NON LEGGIBILE':'D9E2EC'}
            headers=[c.value for c in ws[1]]
            if 'codice' in headers:
                idx=headers.index('codice')+1
                for row in ws.iter_rows(min_row=2):
                    color=colors.get(row[idx-1].value)
                    if color:
                        for cell in row:cell.fill=PatternFill('solid',fgColor=color)
    return buf.getvalue()
