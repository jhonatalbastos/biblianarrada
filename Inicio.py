import streamlit as st
import requests
import sqlite3
import json
import datetime
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(page_title="Início - Dashboard", page_icon="🙏", layout="wide")

# --- Inicialização do Estado (Session State) ---
if 'progresso_leituras' not in st.session_state:
    st.session_state['progresso_leituras'] = {} 
    # Ex: {'05/12/2025-evangelho': {'roteiro': True, 'imagens': False, ...}}

if 'leitura_atual' not in st.session_state:
    st.session_state['leitura_atual'] = None # Ex: {'tipo': 'Evangelho', 'texto': '...', 'ref': 'Mt...'}

# --- Funções de Banco e API (Mantidas da versão anterior) ---
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
    return json.loads(res[0]) if res else None

def safe_extract(source, key, sub_key="texto"):
    val = source.get(key)
    if val is None: return ""
    if isinstance(val, str): return "" if sub_key == "referencia" else val
    return val.get(sub_key, "")

def buscar_liturgia_api(data_obj):
    dia, mes, ano = data_obj.day, data_obj.month, data_obj.year
    url = f"https://liturgia.up.railway.app/{dia}-{mes}-{ano}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None, "Erro na API"
        d = resp.json()
        
        # Mapeamento para garantir estrutura padrão
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

# --- Funções de Navegação ---
def selecionar_leitura(leitura_data, data_str):
    """Define qual leitura está sendo trabalhada e redireciona."""
    st.session_state['leitura_atual'] = leitura_data
    st.session_state['data_atual_str'] = data_str
    
    # Cria chave única para rastrear progresso
    chave = f"{data_str}-{leitura_data['tipo']}"
    if chave not in st.session_state['progresso_leituras']:
        st.session_state['progresso_leituras'][chave] = {'roteiro': False, 'imagens': False, 'audio': False}

def ir_para_pagina(pagina):
    st.switch_page(pagina)

# --- Interface Principal ---
init_db()
st.title("🎛️ Dashboard de Produção")

col_conf, col_dash = st.columns([1, 3])

with col_conf:
    st.subheader("Data Litúrgica")
    data_sel = st.date_input("Data", datetime.date.today())
    data_str = data_sel.strftime("%d/%m/%Y")
    
    if st.button("🔄 Buscar/Atualizar Liturgia", type="primary"):
        with st.spinner("Buscando..."):
            dados_db = carregar_do_banco(data_str)
            if dados_db:
                st.session_state['dados_brutos'] = dados_db
                st.success("Carregado do Cache")
            else:
                dados_api, err = buscar_liturgia_api(data_sel)
                if dados_api:
                    salvar_no_banco(dados_api)
                    st.session_state['dados_brutos'] = dados_api
                    st.success("Atualizado da API")
                else:
                    st.error(f"Erro: {err}")

with col_dash:
    if 'dados_brutos' in st.session_state:
        d = st.session_state['dados_brutos']
        st.markdown(f"### {d['liturgia']} ({d['cor']})")
        st.divider()

        # Montar Tabela Visual de Pipeline
        st.write("#### 🚀 Pipeline de Produção")
        
        # Filtra leituras vazias (ex: 2ª leitura em dia de semana)
        leituras_validas = [l for l in d['leituras'] if l['texto']]

        for i, leitura in enumerate(leituras_validas):
            chave = f"{data_str}-{leitura['tipo']}"
            progresso = st.session_state['progresso_leituras'].get(chave, {'roteiro': False, 'imagens': False, 'audio': False})
            
            c1, c2, c3, c4, c5 = st.columns([2, 3, 1.5, 1.5, 1.5])
            
            with c1:
                st.markdown(f"**{leitura['tipo']}**")
            with c2:
                st.caption(f"{leitura['ref']}")
            
            # Botão ROTEIRO
            with c3:
                # Sempre habilitado para começar
                if st.button(f"📝 Roteiro", key=f"btn_rot_{i}"):
                    selecionar_leitura(leitura, data_str)
                    ir_para_pagina("pages/1_Roteiro_Viral.py")
            
            # Botão IMAGENS
            with c4:
                disabled = not progresso['roteiro']
                icon = "🎨" if progresso['roteiro'] else "🔒"
                if st.button(f"{icon} Imagens", key=f"btn_img_{i}", disabled=disabled):
                    selecionar_leitura(leitura, data_str)
                    ir_para_pagina("pages/2_Imagens.py")

            # Botão AUDIO
            with c5:
                disabled = not progresso['roteiro'] # Audio depende do roteiro, não necessariamente das imagens
                icon = "🔊" if progresso['roteiro'] else "🔒"
                if st.button(f"{icon} Áudio", key=f"btn_aud_{i}", disabled=disabled):
                    selecionar_leitura(leitura, data_str)
                    ir_para_pagina("pages/3_Audio_TTS.py")
            
            st.markdown("---")
            
    else:
        st.info("Selecione uma data e busque a liturgia para ver o pipeline.")
