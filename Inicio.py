import streamlit as st
import requests
import sqlite3
import json
import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Início - Dashboard", page_icon="🙏", layout="wide")

# --- Inicialização do Estado (Session State) ---
if 'progresso_leituras' not in st.session_state:
    st.session_state['progresso_leituras'] = {} 

if 'leitura_atual' not in st.session_state:
    st.session_state['leitura_atual'] = None 

# --- Funções de Banco e API ---
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
        
        if resp.status_code == 404:
            return None, "Liturgia não encontrada para esta data."
        
        if resp.status_code != 200: 
            return None, f"Erro na API: {resp.status_code}"
            
        d = resp.json()
        
        # Mapeamento para garantir estrutura padrão (Novo Formato)
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
            
            # Forçar atualização se os dados do banco estiverem no formato antigo
            if dados_db and 'leituras' not in dados_db:
                dados_db = None # Força buscar na API novamente para corrigir estrutura
                
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
        
        # --- CORREÇÃO DE ERRO (PATCH DE COMPATIBILIDADE) ---
        # Se os dados carregados forem antigos e não tiverem a chave 'leituras', cria-se agora.
        if 'leituras' not in d:
            d['leituras'] = [
                {"tipo": "1ª Leitura", "texto": d.get("primeira_leitura", ""), "ref": d.get("primeira_leitura_ref", "")},
                {"tipo": "2ª Leitura", "texto": d.get("segunda_leitura", ""), "ref": d.get("segunda_leitura_ref", "")},
                {"tipo": "Salmo", "texto": d.get("salmo", ""), "ref": d.get("salmo_ref", "")},
                {"tipo": "Evangelho", "texto": d.get("evangelho", ""), "ref": d.get("evangelho_ref", "")}
            ]
            # Atualiza o estado para não rodar isso toda vez
            st.session_state['dados_brutos'] = d
        # ----------------------------------------------------

        st.markdown(f"### {d.get('liturgia', 'Liturgia')} ({d.get('cor', '')})")
        st.divider()

        st.write("#### 🚀 Pipeline de Produção")
        
        # Filtra leituras vazias com segurança
        leituras_validas = [l for l in d.get('leituras', []) if l.get('texto')]

        if not leituras_validas:
            st.warning("Nenhuma leitura encontrada nos dados. Tente clicar em 'Buscar/Atualizar Liturgia'.")

        for i, leitura in enumerate(leituras_validas):
            tipo = leitura.get('tipo', 'Leitura')
            chave = f"{data_str}-{tipo}"
            progresso = st.session_state['progresso_leituras'].get(chave, {'roteiro': False, 'imagens': False, 'audio': False})
            
            c1, c2, c3, c4, c5 = st.columns([2, 3, 1.5, 1.5, 1.5])
            
            with c1:
                st.markdown(f"**{tipo}**")
            with c2:
                st.caption(f"{leitura.get('ref', '')}")
            
            # Botão ROTEIRO
            with c3:
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
                disabled = not progresso['roteiro']
                icon = "🔊" if progresso['roteiro'] else "🔒"
                if st.button(f"{icon} Áudio", key=f"btn_aud_{i}", disabled=disabled):
                    selecionar_leitura(leitura, data_str)
                    ir_para_pagina("pages/3_Audio_TTS.py")
            
            st.markdown("---")
            
    else:
        st.info("Selecione uma data e clique em 'Buscar/Atualizar Liturgia' para ver o pipeline.")
