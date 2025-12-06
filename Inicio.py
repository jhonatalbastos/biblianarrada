import streamlit as st
import requests
import json
import socket
from datetime import datetime
from modules import database as db  # Importa nosso novo módulo

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Início – Biblia Narrada", layout="wide")

# Inicializa o banco (cria pasta e arquivo se não existirem)
db.init_db()

# --- FUNÇÕES AUXILIARES (LÓGICA DE NEGÓCIO) ---

def get_leitura_status_logic(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    prog, em_prod = db.load_status(chave)
    if prog:
        default.update(prog)
        return default, em_prod
    return default, 0

# --- TESTE DE CONEXÃO (MANTIDO) ---
def test_api_connection():
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    
    try:
        from urllib.parse import urlparse
        hostname = urlparse(BASE_URL).netloc or "api-liturgia-diaria.vercel.app"
    except:
        hostname = "api-liturgia-diaria.vercel.app"

    log = [f"🌐 Hostname: **{hostname}**", f"🔗 URL: `{BASE_URL}`"]
    success = True
    
    # 1. Teste DNS
    try:
        socket.getaddrinfo(hostname, 443)
        log.append("✅ DNS OK.")
    except socket.gaierror as e:
        success = False
        log.append(f"❌ ERRO DNS: {e}")

    # 2. Teste HTTP
    if success:
        hoje = datetime.today().strftime('%Y-%m-%d')
        log.append(f"📡 Testando GET: `?date={hoje}`")
        try:
            resp = requests.get(BASE_URL, params={'date': hoje}, timeout=10)
            if resp.status_code == 200:
                log.append("✅ HTTP 200: Conexão OK.")
            else:
                log.append(f"❌ HTTP Erro: {resp.status_code}")
                success = False
        except Exception as e:
            success = False
            log.append(f"❌ ERRO HTTP: {e}")

    if not success:
        with st.expander("🚨 DIAGNÓSTICO DE CONEXÃO", expanded=True):
            st.markdown("\n".join([f"- {l}" for l in log]))
    
    return success

# --- INTEGRAÇÃO COM A API ---

def fetch_liturgia(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Verifica no Banco (Módulo Externo)
    cached = db.carregar_liturgia(date_str)
    if cached:
        st.toast(f"Carregado do banco local: {date_str}", icon="💾")
        return cached
    
    # 2. Busca na API
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    if BASE_URL.endswith('/'): BASE_URL = BASE_URL[:-1]

    try:
        response = requests.get(BASE_URL, params={'date': date_str}, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parser
        leituras_formatadas = []
        cor = data.get('cor', 'Verde') 
        if not cor and 'liturgia' in data: cor = data['liturgia'].get('cor', 'Verde')

        mapeamento = {
            'primeiraLeitura': 'Primeira Leitura',
            'segundaLeitura': 'Segunda Leitura',
            'salmo': 'Salmo Responsorial',
            'evangelho': 'Evangelho'
        }
        
        for chave_api, titulo in mapeamento.items():
            if chave_api in data:
                conteudo = data[chave_api]
                texto, ref = "", ""
                
                if isinstance(conteudo, dict):
                    texto = conteudo.get('texto', '') or conteudo.get('refrao', '')
                    ref = conteudo.get('referencia', '') or conteudo.get('ref', '')
                elif isinstance(conteudo, str):
                    texto = conteudo
                    ref = data.get(f"{chave_api}Ref", "")
                
                if texto:
                    leituras_formatadas.append({'tipo': titulo, 'titulo': titulo, 'ref': ref, 'texto': texto})

        if not leituras_formatadas:
            st.warning("JSON recebido mas sem leituras reconhecíveis.")
            return None

        final_data = {
            'data': date_str,
            'nome_dia': data.get('dia', 'Dia Litúrgico'),
            'cor': cor,
            'leituras': leituras_formatadas
        }
        
        # Salva no Banco (Módulo Externo)
        db.salvar_liturgia(date_str, final_data)
        return final_data

    except Exception as e:
        st.error(f"Erro na requisição: {e}")
        return None

# --- UI HELPER ---
def handle_leitura_selection(data_str, tipo_leitura):
    try:
        dados_dia = fetch_liturgia(datetime.strptime(data_str, '%Y-%m-%d'))
        if not dados_dia: return
        
        leitura = next((l for l in dados_dia['leituras'] if l['tipo'] == tipo_leitura), None)
        if not leitura: st.error("Leitura não encontrada."); return

        prog, _ = get_leitura_status_logic(data_str, tipo_leitura)
        
        st.session_state.update({
            'data_atual_str': data_str,
            'leitura_atual': {**leitura, 'cor_liturgica': dados_dia['cor']},
            'progresso_leitura_atual': prog
        })
        
        # Atualiza Status no Banco
        db.update_status(f"{data_str}-{tipo_leitura}", data_str, tipo_leitura, prog, 1)
        st.switch_page("pages/1_Roteiro_Viral.py")
    except Exception as e:
        st.error(f"Erro ao selecionar: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == '__main__':
    test_api_connection()

st.title("📖 Biblia Narrada: Painel de Produção")

# --- DASHBOARD ---
st.header("📋 Em Produção")
status_raw = db.load_status() # Carrega do módulo DB
dash_data = []
for k, v in status_raw.items():
    if not (v['progresso'].get('publicacao') and not v['em_producao']):
        dash_data.append({'chave': k, **v})

if dash_data:
    cols = st.columns(4)
    for idx, item in enumerate(dash_data):
        with cols[idx % 4]:
            with st.container(border=True):
                st.caption(f"{item['data_liturgia']} | {item['tipo_leitura']}")
                etapas = sum(item['progresso'].values())
                st.progress(etapas/7)
                if st.button("Abrir", key=f"btn_dash_{item['chave']}"):
                    handle_leitura_selection(item['data_liturgia'], item['tipo_leitura'])
else:
    st.info("Nenhuma leitura em andamento.")

st.divider()

# --- HISTÓRICO ---
cache = db.listar_historico() # Carrega do módulo DB
if cache:
    st.subheader("🗓️ Histórico Local")
    col_c1, col_c2 = st.columns([3,1])
    with col_c1:
        selected_cache = st.selectbox("Itens salvos no banco:", [f"{c['Data']} - {c['Cor Litúrgica']}" for c in cache], key="sel_cache")
    with col_c2:
        if st.button("Carregar"):
            data_sel = selected_cache.split(' - ')[0]
            st.session_state['data_busca'] = data_sel
            st.rerun()

st.divider()

# --- BUSCA API ---
st.header("🔍 Buscar Nova Liturgia")
c1, c2 = st.columns([1, 2])
with c1:
    dt_input = st.date_input("Data", value=datetime.today())
with c2:
    st.write("")
    st.write("")
    if st.button("Buscar API Externa", type="primary"):
        st.session_state['data_busca'] = dt_input.strftime('%Y-%m-%d')
        if 'dados_liturgia' in st.session_state: del st.session_state['dados_liturgia']
        st.rerun()

data_busca = st.session_state.get('data_busca')
if data_busca:
    dados = fetch_liturgia(datetime.strptime(data_busca, '%Y-%m-%d'))
    
    if dados:
        st.success(f"Liturgia: {dados['nome_dia']} ({dados['cor']})")
        cols = st.columns(len(dados['leituras']))
        for i, l in enumerate(dados['leituras']):
            with cols[i % 4]:
                with st.container(border=True):
                    st.markdown(f"**{l['tipo']}**")
                    if st.button(f"Produzir", key=f"prod_{l['tipo']}_{data_busca}"):
                        handle_leitura_selection(data_busca, l['tipo'])
