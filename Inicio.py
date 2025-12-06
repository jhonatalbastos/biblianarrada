import streamlit as st
import sys
import os
import requests
import json
import socket
import re
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIGURAÇÃO DE IMPORTAÇÃO
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

# --- MAPA DE ABREVIAÇÕES (OPCIONAL, PARA EMBELEZAR) ---
LIVROS_EXTENSO = {
    "Mt": "Mateus", "Mc": "Marcos", "Lc": "Lucas", "Jo": "João",
    "Gn": "Gênesis", "Ex": "Êxodo", "Lv": "Levítico", "Nm": "Números", "Dt": "Deuteronômio",
    "Is": "Isaías", "Jr": "Jeremias", "Ez": "Ezequiel", "Dn": "Daniel",
    "Sl": "Salmo", "At": "Atos dos Apóstolos", "Rm": "Romanos", "1Cor": "1ª Coríntios",
    "2Cor": "2ª Coríntios", "Gl": "Gálatas", "Ef": "Efésios", "Fp": "Filipenses",
    "Cl": "Colossenses", "1Ts": "1ª Tessalonicenses", "2Ts": "2ª Tessalonicenses",
    "1Tm": "1ª Timóteo", "2Tm": "2ª Timóteo", "Tt": "Tito", "Fm": "Filemom",
    "Hb": "Hebreus", "Tg": "Tiago", "1Pd": "1ª Pedro", "2Pd": "2ª Pedro",
    "1Jo": "1ª João", "2Jo": "2ª João", "3Jo": "3ª João", "Jd": "Judas", "Ap": "Apocalipse"
}

# --- FUNÇÕES AUXILIARES ---

def formatar_referencia(ref_bruta, tipo):
    """
    Formata referências da API v2 (ex: 'Mt 9,35-10,1') para o estilo desejado.
    """
    if not ref_bruta: return ""
    
    # Salmo geralmente já vem ok ou precisa de pouco ajuste
    if tipo == "Salmo Responsorial":
        return ref_bruta

    # Tenta expandir abreviações (Ex: "Mt" -> "Mateus")
    partes = ref_bruta.split(" ", 1)
    if len(partes) == 2:
        livro_abrev, resto = partes
        livro_nome = LIVROS_EXTENSO.get(livro_abrev, livro_abrev) # Se não achar, usa original
        texto_ref = f"{livro_nome} {resto}"
    else:
        texto_ref = ref_bruta

    # Formatação especial para Evangelho: "Mateus, Cap. 9..."
    if tipo == "Evangelho":
        # Remove "São", "Santo" se por acaso vierem (na v2 é raro, mas garante)
        texto_ref = re.sub(r'\b(São|Santo|Santa)\s+', '', texto_ref, flags=re.IGNORECASE)
        
        # Insere ", Cap."
        # Regex: Pega (Nome do Livro) + Espaço + (Número)
        texto_ref = re.sub(r'([A-Za-zÀ-ÿ]+)\s+(\d+)', r'\1, Cap. \2', texto_ref)

    return texto_ref

def get_leitura_status_logic(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    prog, em_prod = db.load_status(chave)
    if prog:
        default.update(prog)
        return default, em_prod
    return default, 0

def test_api_connection():
    # URL padrão da API v2 (Dancrf)
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://liturgia.up.railway.app")
    try:
        from urllib.parse import urlparse
        hostname = urlparse(BASE_URL).netloc or "liturgia.up.railway.app"
        socket.getaddrinfo(hostname, 443)
        return True
    except:
        return False

# --- INTEGRAÇÃO COM A API V2 ---

def fetch_liturgia(date_obj):
    # API v2 usa formato DD-MM-YYYY na URL
    date_str_db = date_obj.strftime('%Y-%m-%d')     # Para salvar no banco (padrão ISO)
    date_str_api = date_obj.strftime('%d-%m-%Y')    # Para chamar a API
    
    # 1. Cache Local
    cached = db.carregar_liturgia(date_str_db)
    if cached:
        st.toast(f"Carregado do banco local: {date_str_db}", icon="💾")
        return cached
    
    # 2. API Request
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://liturgia.up.railway.app")
    if BASE_URL.endswith('/'): BASE_URL = BASE_URL[:-1]
    
    # Endpoint da v2: /v2/dia/DD-MM-YYYY
    API_URL = f"{BASE_URL}/v2/dia/{date_str_api}"

    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        leituras_formatadas = []
        
        # Na v2, a cor e o dia costumam estar na raiz ou chaves específicas
        cor_liturgica = data.get('cor', 'Verde')
        nome_dia = data.get('dia', 'Dia Litúrgico')

        # Função helper para extrair da estrutura v2
        def extrair_v2(chave_json, titulo_sistema):
            if chave_json in data:
                item = data[chave_json]
                # v2 retorna 'referencia' e 'texto' claramente
                ref_bruta = item.get('referencia', '')
                texto = item.get('texto', '')
                
                # Se for Salmo, o refrão vem separado
                if chave_json == 'salmo':
                    refrao = item.get('refrao', '')
                    if refrao:
                        texto = f"Refrão: {refrao}\n\n{texto}"
                
                ref_final = formatar_referencia(ref_bruta, titulo_sistema)
                
                leituras_formatadas.append({
                    'tipo': titulo_sistema,
                    'titulo': titulo_sistema,
                    'ref': ref_final,
                    'texto': texto
                })

        # Mapeamento dos campos da v2
        extrair_v2('primeiraLeitura', 'Primeira Leitura')
        extrair_v2('segundaLeitura', 'Segunda Leitura') # Nem sempre tem
        extrair_v2('salmo', 'Salmo Responsorial')
        extrair_v2('evangelho', 'Evangelho')

        if not leituras_formatadas:
            st.warning("⚠️ Dados recebidos, mas nenhuma leitura encontrada.")
            return None

        final_data = {
            'data': date_str_db, # Salva com ISO YYYY-MM-DD no banco para ordenação
            'nome_dia': nome_dia,
            'cor': cor_liturgica,
            'leituras': leituras_formatadas
        }
        
        db.salvar_liturgia(date_str_db, final_data)
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
st.header("🔍 Buscar Nova Liturgia (API v2)")
c1, c2 = st.columns([1, 2])
with c1:
    dt_input = st.date_input("Data", value=datetime.today())
with c2:
    st.write("")
    st.write("")
    if st.button("Buscar API Externa", type="primary"):
        st.session_state['data_busca'] = dt_input.strftime('%Y-%m-%d')
        # Limpa cache da sessão se mudar a data
        if 'dados_liturgia' in st.session_state: del st.session_state['dados_liturgia']
        st.rerun()

# --- RESULTADOS ---
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
                        
                        # Exibe referência formatada
                        ref_display = l['ref'] if l['ref'] else "Sem referência"
                        st.markdown(f"**{ref_display}**")
                        
                        st.markdown("---")
                        
                        if st.button(f"Produzir", key=f"prod_{l['tipo']}_{data_busca}", use_container_width=True):
                            handle_leitura_selection(data_busca, l['tipo'])
