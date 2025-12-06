import streamlit as st
import sys
import os
import requests
import json
import socket
import re # Importante para limpar os títulos
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

# --- FUNÇÕES AUXILIARES ---

def limpar_referencia(texto, tipo):
    """
    Remove prefixos litúrgicos para deixar apenas a referência bíblica.
    Ex: 'Primeira leitura: Isaías 30' -> 'Isaías 30'
    Ex: 'Evangelho... segundo São Mateus' -> 'São Mateus...'
    """
    if not texto: return ""
    
    # Se for Salmo, geralmente queremos manter o formato "Salmo X (Y)"
    if tipo == "Salmo Responsorial":
        return texto

    # Remove "Primeira leitura:", "Segunda leitura:" (case insensitive)
    texto = re.sub(r'^(Primeira|Segunda)\s+leitura\s*[:|-]?\s*', '', texto, flags=re.IGNORECASE)
    
    # Remove "Leitura do..."
    texto = re.sub(r'^Leitura\s+d[oa]\s+', '', texto, flags=re.IGNORECASE)

    # Limpeza específica para Evangelho
    if tipo == "Evangelho":
        # Remove "Proclamação do Evangelho..." ou "Evangelho... segundo"
        texto = re.sub(r'^(Proclamação do\s+)?Evangelho(\s+de Jesus Cristo)?\s+segundo\s+', '', texto, flags=re.IGNORECASE)
        # Tenta formatar "Mateus 9" para "Mateus, Cap. 9" (Opcional, mas atende seu pedido visual)
        # Adiciona "Cap." se houver um número logo após o nome do livro
        # Ex: "São Mateus 9,..." -> "São Mateus, Cap. 9,..."
        texto = re.sub(r'([A-Za-z])\s+(\d+)', r'\1, Cap. \2', texto)

    return texto.strip()

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
    
    try:
        socket.getaddrinfo(hostname, 443)
        return True
    except:
        return False

# --- INTEGRAÇÃO COM A API ---

def fetch_liturgia(date_obj):
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
        cor_liturgica = "Verde"
        nome_dia = "Dia Litúrgico"

        # --- PARSER DO JSON ---
        if 'today' in data:
            today = data['today']
            cor_liturgica = today.get('color', 'Verde')
            nome_dia = today.get('entry_title', 'Dia Litúrgico').replace('<br/>', ' - ')
            readings = today.get('readings', {})
            
            # Helper para processar cada item
            def processar_item(tipo_sistema, item_api, ref_key='title'):
                if not item_api: return
                
                # Pega a referência bruta (Ex: "Primeira leitura: Isaías...")
                ref_bruta = item_api.get(ref_key, '') or item_api.get('head_title', '')
                
                # Limpa a referência para o formato desejado
                ref_limpa = limpar_referencia(ref_bruta, tipo_sistema)
                
                # Tratamento especial para Salmo (texto)
                texto_final = item_api.get('text', '')
                if tipo_sistema == 'Salmo Responsorial':
                    refrao = item_api.get('response', '')
                    conteudo = item_api.get('content_psalm', [])
                    if isinstance(conteudo, list):
                        corpo_salmo = "\n".join([str(v) for v in conteudo])
                    else:
                        corpo_salmo = str(conteudo)
                    texto_final = f"Refrão: {refrao}\n\n{corpo_salmo}"

                leituras_formatadas.append({
                    'tipo': tipo_sistema,
                    'titulo': tipo_sistema, # Título fixo (Header do Card)
                    'ref': ref_limpa,       # Referência limpa (Subheader)
                    'texto': texto_final
                })

            processar_item('Primeira Leitura', readings.get('first_reading'))
            processar_item('Segunda Leitura', readings.get('second_reading'))
            processar_item('Salmo Responsorial', readings.get('psalm'))
            processar_item('Evangelho', readings.get('gospel'))

        else:
            # Fallback para formato antigo/plano
            cor_liturgica = data.get('cor') or data.get('liturgia', {}).get('cor', 'Verde')
            nome_dia = data.get('dia', 'Dia Litúrgico')
            
            mapeamento = {
                'primeiraLeitura': 'Primeira Leitura',
                'segundaLeitura': 'Segunda Leitura',
                'salmo': 'Salmo Responsorial',
                'evangelho': 'Evangelho'
            }
            
            for chave, tipo_sis in mapeamento.items():
                if chave in data:
                    conteudo = data[chave]
                    ref_bruta = ""
                    texto = ""
                    
                    if isinstance(conteudo, dict):
                        texto = conteudo.get('texto', '') or conteudo.get('refrao', '')
                        ref_bruta = conteudo.get('referencia', '') or conteudo.get('ref', '')
                    elif isinstance(conteudo, str):
                        texto = conteudo
                        ref_bruta = data.get(f"{chave}Ref", "")

                    if texto:
                        ref_limpa = limpar_referencia(ref_bruta, tipo_sis)
                        leituras_formatadas.append({
                            'tipo': tipo_sis,
                            'titulo': tipo_sis,
                            'ref': ref_limpa,
                            'texto': texto
                        })

        if not leituras_formatadas:
            st.warning("⚠️ JSON recebido, mas o formato não foi reconhecido.")
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

# --- RESULTADOS ---
data_busca = st.session_state.get('data_busca')
if data_busca:
    dados = fetch_liturgia(datetime.strptime(data_busca, '%Y-%m-%d'))
    
    if dados:
        cor_map = {"roxo": "🟣", "verde": "🟢", "vermelho": "🔴", "branco": "⚪", "rosa": "🌸"}
        cor_emoji = cor_map.get(dados['cor'].lower(), "🎨")
        
        st.success(f"{cor_emoji} **{dados['nome_dia']}** ({dados['cor']})")
        
        if 'leituras' in dados:
            # Layout em Colunas
            cols = st.columns(len(dados['leituras']))
            for i, l in enumerate(dados['leituras']):
                with cols[i % 4]:
                    with st.container(border=True):
                        # Cabeçalho Principal (Tipo)
                        st.subheader(l['tipo'])
                        
                        # Referência Limpa (Ex: Isaías 30, ...)
                        # Se não tiver ref, exibe um traço
                        ref_display = l['ref'] if l['ref'] else ""
                        if ref_display:
                            st.markdown(f"**{ref_display}**")
                        
                        st.markdown("---")
                        
                        if st.button(f"Produzir", key=f"prod_{l['tipo']}_{data_busca}", use_container_width=True):
                            handle_leitura_selection(data_busca, l['tipo'])
