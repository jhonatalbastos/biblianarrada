import streamlit as st
import sys
import os
import requests
import json
import socket
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIGURAÇÃO DE IMPORTAÇÃO (CRÍTICO)
# ---------------------------------------------------------------------
root_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_path)

try:
    import modules.database as db
except ImportError:
    try:
        from modules import database as db
    except ImportError:
        st.error("🚨 Erro Crítico: Não foi possível importar 'modules/database.py'.")
        st.stop()

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(page_title="Início – Biblia Narrada", layout="wide")

if hasattr(db, 'init_db'):
    db.init_db()
else:
    st.error("Erro no módulo database.")
    st.stop()

# --- FUNÇÕES AUXILIARES ---

def get_leitura_status_logic(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    prog, em_prod = db.load_status(chave)
    if prog:
        default.update(prog)
        return default, em_prod
    return default, 0

def test_api_connection():
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    try:
        from urllib.parse import urlparse
        hostname = urlparse(BASE_URL).netloc or "api-liturgia-diaria.vercel.app"
    except:
        hostname = "api-liturgia-diaria.vercel.app"
    
    # Teste simples de DNS para evitar travar a UI
    try:
        socket.getaddrinfo(hostname, 443)
        return True
    except:
        return False

# --- INTEGRAÇÃO COM A API (PARSER CORRIGIDO) ---

def fetch_liturgia(date_obj):
    """Busca liturgia e tenta interpretar múltiplos formatos de JSON."""
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Cache Local
    cached = db.carregar_liturgia(date_str)
    if cached:
        st.toast(f"Carregado do banco local: {date_str}", icon="💾")
        return cached
    
    # 2. API Request
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    if BASE_URL.endswith('/'): BASE_URL = BASE_URL[:-1]

    try:
        response = requests.get(BASE_URL, params={'date': date_str}, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        leituras_formatadas = []
        cor_liturgica = "Verde" # Default
        nome_dia = "Dia Litúrgico"

        # --- ESTRATÉGIA A: Formato Aninhado "today" (O que você recebeu) ---
        if 'today' in data:
            today = data['today']
            cor_liturgica = today.get('color', 'Verde')
            nome_dia = today.get('entry_title', 'Dia Litúrgico').replace('<br/>', ' - ')
            
            readings = today.get('readings', {})
            
            # 1. Primeira Leitura
            if 'first_reading' in readings:
                item = readings['first_reading']
                leituras_formatadas.append({
                    'tipo': 'Primeira Leitura',
                    'titulo': 'Primeira Leitura',
                    'ref': item.get('title', ''), # Ex: "Primeira leitura: Isaías..."
                    'texto': item.get('text', '')
                })

            # 2. Segunda Leitura
            if 'second_reading' in readings:
                item = readings['second_reading']
                leituras_formatadas.append({
                    'tipo': 'Segunda Leitura',
                    'titulo': 'Segunda Leitura',
                    'ref': item.get('title', ''),
                    'texto': item.get('text', '')
                })

            # 3. Salmo (Tratamento especial para lista)
            if 'psalm' in readings:
                item = readings['psalm']
                refrao = item.get('response', '')
                # Se content_psalm for lista, junta. Se for string, usa direto.
                conteudo_salmo = item.get('content_psalm', [])
                if isinstance(conteudo_salmo, list):
                    texto_salmo = "\n".join([str(v) for v in conteudo_salmo])
                else:
                    texto_salmo = str(conteudo_salmo)
                
                texto_completo = f"Refrão: {refrao}\n\n{texto_salmo}"
                
                leituras_formatadas.append({
                    'tipo': 'Salmo Responsorial',
                    'titulo': 'Salmo Responsorial',
                    'ref': item.get('title', ''), # Ex: "Salmo 146"
                    'texto': texto_completo
                })

            # 4. Evangelho
            if 'gospel' in readings:
                item = readings['gospel']
                # Tenta pegar head_title, se falhar pega title
                ref = item.get('head_title', '') or item.get('title', '')
                leituras_formatadas.append({
                    'tipo': 'Evangelho',
                    'titulo': 'Evangelho',
                    'ref': ref,
                    'texto': item.get('text', '')
                })

        # --- ESTRATÉGIA B: Formato Plano (Legado/Outras datas) ---
        else:
            # Tenta achar a cor na raiz ou dentro de 'liturgia'
            cor_liturgica = data.get('cor') or data.get('liturgia', {}).get('cor', 'Verde')
            nome_dia = data.get('dia', 'Dia Litúrgico')

            mapeamento = {
                'primeiraLeitura': 'Primeira Leitura',
                'segundaLeitura': 'Segunda Leitura',
                'salmo': 'Salmo Responsorial',
                'evangelho': 'Evangelho'
            }
            
            for chave_api, titulo_sistema in mapeamento.items():
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
                        leituras_formatadas.append({'tipo': titulo_sistema, 'titulo': titulo_sistema, 'ref': ref, 'texto': texto})

        # --- VALIDAÇÃO FINAL ---
        if not leituras_formatadas:
            st.warning("⚠️ JSON recebido, mas o formato não foi reconhecido.")
            with st.expander("🕵️ Ver JSON Recebido (Para Debug)"):
                st.json(data)
            return None

        final_data = {
            'data': date_str,
            'nome_dia': nome_dia,
            'cor': cor_liturgica,
            'leituras': leituras_formatadas
        }
        
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
        
        db.update_status(f"{data_str}-{tipo_leitura}", data_str, tipo_leitura, prog, 1)
        st.switch_page("pages/1_Roteiro_Viral.py")
    except Exception as e:
        st.error(f"Erro ao selecionar: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == '__main__':
    # Teste silencioso
    test_api_connection()

st.title("📖 Biblia Narrada: Painel de Produção")

# --- DASHBOARD ---
st.header("📋 Em Produção")
status_raw = db.load_status()
dash_data = []

if status_raw:
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
cache = db.listar_historico()
if cache:
    st.subheader("🗓️ Histórico Local")
    col_c1, col_c2 = st.columns([3,1])
    with col_c1:
        selected_cache = st.selectbox("Itens salvos:", [f"{c['Data']} - {c['Cor Litúrgica']}" for c in cache], key="sel_cache")
    with col_c2:
        if st.button("Carregar do Histórico"):
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

# --- RESULTADOS DA BUSCA ---
data_busca = st.session_state.get('data_busca')
if data_busca:
    dados = fetch_liturgia(datetime.strptime(data_busca, '%Y-%m-%d'))
    
    if dados:
        cor_map = {"roxo": "🟣", "verde": "🟢", "vermelho": "🔴", "branco": "⚪", "rosa": "🌸"}
        cor_emoji = cor_map.get(dados['cor'].lower(), "🎨")
        
        st.success(f"{cor_emoji} **{dados['nome_dia']}** ({dados['cor']})")
        
        if 'leituras' in dados:
            cols = st.columns(len(dados['leituras']))
            for i, l in enumerate(dados['leituras']):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.subheader(l['tipo'])
                        st.caption(l['ref'][:50] + "..." if len(l['ref']) > 50 else l['ref'])
                        if st.button(f"Produzir", key=f"prod_{l['tipo']}_{data_busca}"):
                            handle_leitura_selection(data_busca, l['tipo'])
