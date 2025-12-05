import streamlit as st
import requests
import sqlite3
import json
import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Início - Dashboard", page_icon="🙏", layout="wide")

# --- Inicialização do Estado ---
if 'progresso_leituras' not in st.session_state:
    st.session_state['progresso_leituras'] = {} 

if 'leitura_atual' not in st.session_state:
    st.session_state['leitura_atual'] = None 

# --- Funções Auxiliares (Banco e API) ---
def init_db():
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS historico 
                 (data_liturgia TEXT PRIMARY KEY, santo TEXT, cor TEXT, json_completo TEXT, data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def salvar_no_banco(dados):
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    json_str = json.dumps(dados, ensure_ascii=False)
    c.execute('INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo) VALUES (?, ?, ?, ?)', 
              (dados['data'], dados['liturgia'], dados['cor'], json_str))
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    if res:
        return json.loads(res[0])
    return None

def safe_extract(source, key, sub_key="texto"):
    val = source.get(key)
    if val is None: return ""
    if isinstance(val, str): return "" if sub_key == "referencia" else val
    if isinstance(val, dict): return val.get(sub_key, "")
    return str(val)

def buscar_liturgia_api(data_obj):
    dia, mes, ano = data_obj.day, data_obj.month, data_obj.year
    url = f"https://liturgia.up.railway.app/{dia}-{mes}-{ano}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404: return None, "Liturgia não encontrada (data futura ou indisponível)."
        if resp.status_code != 200: return None, f"Erro na API: {resp.status_code}"
        d = resp.json()
        
        return {
            "data": d.get("data", f"{dia:02d}/{mes:02d}/{ano}"),
            "liturgia": d.get("liturgia", "Liturgia Diária"),
            "cor": d.get("cor", "N/A"),
            "santo": d.get("liturgia", ""),
            "leituras": [
                {"tipo": "1ª Leitura", "texto": safe_extract(d, "primeiraLeitura", "texto"), "ref": safe_extract(d, "primeiraLeitura", "referencia")},
                {"tipo": "2ª Leitura", "texto": safe_extract(d, "segundaLeitura", "texto"), "ref": safe_extract(d, "segundaLeitura", "referencia")},
                {"tipo": "Salmo", "texto": safe_extract(d, "salmo", "texto"), "ref": safe_extract(d, "salmo", "referencia")},
                {"tipo": "Evangelho", "texto": safe_extract(d, "evangelho", "texto"), "ref": safe_extract(d, "evangelho", "referencia")}
            ]
        }, None
    except Exception as e:
        return None, str(e)

# --- Navegação ---
def selecionar_leitura(leitura_data, data_str, cor_liturgica="N/A"):
    """Define qual leitura está sendo trabalhada e inicializa o progresso."""
    lectura_data = leitura_data.copy()
    lectura_data['cor_liturgica'] = cor_liturgica # Passa a cor para o overlay
    
    st.session_state['leitura_atual'] = lectura_data
    st.session_state['data_atual_str'] = data_str
    
    chave = f"{data_str}-{leitura_data['tipo']}"
    if chave not in st.session_state['progresso_leituras']:
        st.session_state['progresso_leituras'][chave] = {
            'roteiro': False, 'imagens': False, 'audio': False,
            'overlay': False, 'legendas': False, 'video': False, 'publicacao': False
        }

def ir_para_pagina(pagina):
    st.switch_page(pagina)

# --- Interface ---
init_db()
st.title("🎛️ Dashboard de Produção")

col_conf, col_dash = st.columns([1, 4])

with col_conf:
    st.subheader("Data Litúrgica")
    data_sel = st.date_input("Data", datetime.date.today())
    data_str = data_sel.strftime("%d/%m/%Y")
    
    if st.button("🔄 Buscar Liturgia", type="primary", use_container_width=True):
        with st.spinner("Buscando..."):
            dados_db = carregar_do_banco(data_str)
            if dados_db and 'leituras' not in dados_db: dados_db = None 
            
            if dados_db:
                st.session_state['dados_brutos'] = dados_db
                st.success("Cache OK")
            else:
                dados_api, err = buscar_liturgia_api(data_sel)
                if dados_api:
                    salvar_no_banco(dados_api)
                    st.session_state['dados_brutos'] = dados_api
                    st.success("API OK")
                else:
                    st.error(f"Erro: {err}")

with col_dash:
    if 'dados_brutos' in st.session_state:
        d = st.session_state['dados_brutos']
        if 'leituras' not in d:
            st.warning("Dados antigos detectados. Por favor, clique em buscar novamente.")
            st.stop()

        st.markdown(f"### {d.get('liturgia', 'Liturgia')} ({d.get('cor', '')})")
        st.divider()

        st.write("#### 🚀 Pipeline de Produção")
        leituras_validas = [l for l in d.get('leituras', []) if l.get('texto')]

        # Cabeçalho da Tabela
        cols = st.columns([2, 2, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
        cols[0].markdown("**Leitura**")
        cols[1].markdown("**Ref**")
        cols[2].caption("Roteiro")
        cols[3].caption("Imagens")
        cols[4].caption("Áudio")
        cols[5].caption("Overlay")
        cols[6].caption("Legenda")
        cols[7].caption("Vídeo")
        cols[8].caption("Publicar")

        for i, leitura in enumerate(leituras_validas):
            tipo = leitura.get('tipo', 'Leitura')
            chave = f"{data_str}-{tipo}"
            
            default_prog = {'roteiro': False, 'imagens': False, 'audio': False, 'overlay': False, 'legendas': False, 'video': False, 'publicacao': False}
            progresso = st.session_state['progresso_leituras'].get(chave, default_prog)
            
            c = st.columns([2, 2, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
            
            with c[0]: st.markdown(f"**{tipo}**")
            with c[1]: st.caption(f"{leitura.get('ref', '')}")

            # Botões de Ação
            def check_btn(label, key_suffix, page, enabled, icon_on, icon_off):
                icon = icon_on if progresso.get(key_suffix, False) else icon_off
                disabled = not enabled
                if st.button(icon, key=f"{key_suffix}_{i}", disabled=disabled, help=label):
                    selecionar_leitura(leitura, data_str, d.get('cor', 'N/A'))
                    # Define a página atual para que a navegação saiba para onde ir
                    st.switch_page(page)

            midia_pronta = progresso['imagens'] and progresso['audio']
            
            with c[2]: check_btn("Roteiro", "roteiro", "pages/1_Roteiro_Viral.py", True, "📝", "📝")
            with c[3]: check_btn("Imagens", "imagens", "pages/2_Imagens.py", progresso['roteiro'], "🎨", "🔒")
            with c[4]: check_btn("Áudio", "audio", "pages/3_Audio_TTS.py", progresso['roteiro'], "🔊", "🔒")
            with c[5]: check_btn("Overlay", "overlay", "pages/4_Overlay.py", midia_pronta, "🖼️", "🔒")
            with c[6]: check_btn("Legendas", "legendas", "pages/5_Legendas.py", midia_pronta, "💬", "🔒")
            with c[7]: check_btn("Vídeo Final", "video", "pages/6_Video_Final.py", midia_pronta, "🎬", "🔒")
            with c[8]: check_btn("Publicar", "publicacao", "pages/7_Publicar.py", progresso['video'], "🚀", "🔒")
            
            st.markdown("---")
            
    else:
        st.info("Selecione uma data para iniciar.")
