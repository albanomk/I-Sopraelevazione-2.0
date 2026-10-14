import io
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates
from engine import pages,tabellino_ocr,normalize_project,trace,compare,aggregate,excel_bytes

st.set_page_config(page_title='I-Sopraelevazioni 2.0',page_icon='🚆',layout='wide')
st.markdown('''<style>.stApp{background:#f5f8fb}.block-container{padding-top:1.3rem}h1{color:#12304a}.stButton button[kind=primary]{background:#12304a;border-radius:9px}</style>''',unsafe_allow_html=True)
st.title('🚆 I-Sopraelevazioni 2.0')
st.caption('Controllo sopraelevazioni · tracciabilità del dato · nessun confronto su valori non verificati')

with st.sidebar:
    st.header('⚙️ Soglie modificabili')
    yellow=st.number_input('Alert 1 · scostamento > mm',min_value=0.0,value=10.0,step=1.0)
    orange=st.number_input('Alert 2 · massimo mm',min_value=0.0,value=160.0,step=5.0)
    red=st.number_input('Alert 3 · sopra mm',min_value=orange,value=max(160.0,orange),step=5.0)
    step=st.number_input('Campionamento (m)',min_value=1,max_value=100,value=5)
    st.info('🟢 Nessun alert · 🟡 Alert 1 · 🟠 Alert 2 · 🔴 Alert 3 · ⚪ dato non leggibile')

c1,c2=st.columns(2)
with c1:
    st.subheader('1 · Tabellino di progetto')
    project_file=st.file_uploader('Carica PDF scansionato, Excel o CSV',type=['pdf','xlsx','csv'],key='project')
with c2:
    st.subheader('2 · Grafici di rilievo')
    graph_files=st.file_uploader('Carica uno o più PDF o immagini',type=['pdf','png','jpg','jpeg'],accept_multiple_files=True,key='graphs')

if 'project' not in st.session_state:st.session_state.project=pd.DataFrame(columns=['progressiva_m','h_mm','rotaia_alzata','verificato'])
if 'measures' not in st.session_state:st.session_state.measures=pd.DataFrame(columns=['progressiva_m','rilevato_mm','verificato','nota'])

if project_file:
    file_key=(project_file.name,project_file.size)
    if st.session_state.get('loaded_project')!=file_key:
        try:
            if project_file.name.lower().endswith('.pdf'):
                with st.spinner('Analisi OCR preliminare delle pagine...'):
                    df=tabellino_ocr(project_file.getvalue())
                st.session_state.project=df
            elif project_file.name.lower().endswith('.csv'):
                st.session_state.project=pd.read_csv(io.BytesIO(project_file.getvalue()),sep=None,engine='python')
            else:st.session_state.project=pd.read_excel(io.BytesIO(project_file.getvalue()))
            st.session_state.loaded_project=file_key
        except Exception as e:st.error(f'Lettura tabellino non riuscita: {e}')
    if project_file.name.lower().endswith('.pdf'):
        st.warning('PDF scansionato: OCR preliminare. La progressiva può essere proposta, ma h e rotaia alzata NON sono inventati. Inserisci/verifica i dati prima di abilitarli al confronto.')
        with st.expander('Visualizza le pagine originali per la trascrizione'):
            imgs=list(pages(project_file.getvalue(),1.6))
            page=st.selectbox('Pagina',range(1,len(imgs)+1))
            st.image(imgs[page-1],use_container_width=True)

st.subheader('Tabellino · verifica e correzione')
st.caption('Colonne obbligatorie: progressiva_m (metri), h_mm (mm), rotaia_alzata (sx/dx), verificato (spuntare SOLO dopo controllo visivo). È possibile aggiungere righe.')
project=st.data_editor(st.session_state.project,num_rows='dynamic',hide_index=True,key='edit_project',use_container_width=True,disabled=['pagina','testo_ocr'] if 'pagina' in st.session_state.project else [])
project=normalize_project(project)
st.download_button('⬇️ Scarica tabellino convertito Excel',data=excel_bytes(project,pd.DataFrame(),pd.DataFrame()),file_name='I-Sopraelevazioni_tabellino.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

st.subheader('Grafici · calibrazione e lettura')
st.info('La scala stampata (es. 1:6) NON basta per dedurre i mm dai pixel. Servono due riferimenti verticali e due progressive noti, scelti sul grafico. Le tracce proposte richiedono conferma visiva.')
if graph_files:
    selected=st.selectbox('File grafico',range(len(graph_files)),format_func=lambda i:graph_files[i].name)
    f=graph_files[selected]
    if f.name.lower().endswith('.pdf'):
        imgs=list(pages(f.getvalue(),1.4));idx=st.selectbox('Pagina grafico',range(len(imgs)),format_func=lambda i:str(i+1));im=imgs[idx]
    else:im=Image.open(io.BytesIO(f.getvalue())).convert('RGB')
    st.caption('Fai clic sull’immagine per leggere le coordinate pixel; poi riportale nei campi di calibrazione. Per grafici con progressive decrescenti da sinistra a destra, inserisci km sinistro maggiore del km destro.')
    # Image coordinate component reports original image coordinates.
    click=streamlit_image_coordinates(im,key=f'click-{selected}-{f.name}',width=min(1050,im.width))
    if click:st.write('Punto selezionato (sull’immagine visualizzata):',click,'· attenzione: se ridimensionata, moltiplicare per dimensione originale / dimensione visualizzata')
    W,H=im.size
    with st.expander('Calibrazione metrica · obbligatoria',expanded=True):
        a,b=st.columns(2)
        with a:
            xl=st.number_input('x progressiva sinistra (pixel originali)',value=int(W*.18),min_value=0,max_value=W-1)
            kl=st.number_input('Progressiva sinistra (metri)',value=11800.0)
            yt=st.number_input('y riferimento verticale A (pixel)',value=int(H*.45),min_value=0,max_value=H-1)
            vt=st.number_input('Valore riferimento A (mm)',value=-180.0)
            bandtop=st.number_input('Limite superiore fascia traccia (pixel)',value=int(H*.44),min_value=0,max_value=H-1)
        with b:
            xr=st.number_input('x progressiva destra (pixel originali)',value=int(W*.95),min_value=0,max_value=W-1)
            kr=st.number_input('Progressiva destra (metri)',value=10100.0)
            yb=st.number_input('y riferimento verticale B (pixel)',value=int(H*.50),min_value=0,max_value=H-1)
            vb=st.number_input('Valore riferimento B (mm)',value=0.0)
            bandbottom=st.number_input('Limite inferiore fascia traccia (pixel)',value=int(H*.55),min_value=1,max_value=H)
        st.caption(f'Immagine originale: {W} × {H} px. I valori precompilati sono SEGNAPOSTO, non calibrazioni certificate.')
        if st.button('🔎 Proponi traccia da calibrazione',type='primary'):
            try:
                d=trace(im,xl,xr,kl,kr,yt,vt,yb,vb,bandtop,bandbottom,step_m=step)
                st.session_state.measures=d
                st.success(f'{len(d)} campioni proposti: tutti inizialmente NON verificati.')
            except Exception as e:st.error(str(e))

st.subheader('Misure rilevate · controllo umano')
st.caption('Il riconoscimento automatico non certifica la traccia. Spunta verificato solo per campioni controllati. Puoi inserire manualmente valori letti con strumenti affidabili.')
measures=st.data_editor(st.session_state.measures,num_rows='dynamic',hide_index=True,key='edit_measures',use_container_width=True)
if st.button('▶️ Esegui confronto e crea report',type='primary'):
    try:
        detail=compare(project,measures,tolerance=yellow,orange=orange,red=red,step_m=step)
        summary=aggregate(detail,step_m=step)
        st.session_state.detail=detail;st.session_state.summary=summary;st.session_state.final_project=project
    except Exception as e:st.error(f'Confronto non eseguibile: {e}')
if 'detail' in st.session_state:
    detail=st.session_state.detail;summary=st.session_state.summary
    st.subheader('Report aggregato')
    if detail.empty:st.warning('Nessuna misura disponibile. Non sono stati prodotti confronti.')
    else:
        counts=detail.codice.value_counts()
        cols=st.columns(5)
        for col,label in zip(cols,['VERDE','GIALLO','ARANCIONE','ROSSO','NON LEGGIBILE']):col.metric(label,int(counts.get(label,0)))
        def style_row(row):
            colors={'VERDE':'#d9f5dc','GIALLO':'#fff4ac','ARANCIONE':'#ffdfb3','ROSSO':'#ffd0d0','NON LEGGIBILE':'#e5e7eb'}
            return [f'background-color:{colors.get(row.codice,"white")};color:#17212b']*len(row)
        st.dataframe(summary.style.apply(style_row,axis=1),hide_index=True,use_container_width=True)
        with st.expander('Dettaglio completo e motivi di esclusione'):
            st.dataframe(detail.style.apply(style_row,axis=1),hide_index=True,use_container_width=True)
        st.download_button('⬇️ Scarica report completo Excel',data=excel_bytes(st.session_state.final_project,detail,summary),file_name='I-Sopraelevazioni_2.0_report.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.caption('Uso tecnico di supporto: risultati soggetti a verifica professionale. Nessuna misura o conformità è certificata automaticamente.')
