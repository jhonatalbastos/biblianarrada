import streamlit as st
import sys
import os
import requests
import json
import socket
import re
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE IMPORTAÇÃO DOS MÓDULOS
# ---------------------------------------------------------------------
root_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_path)

try:
    import modules.database as db
except ImportError:
    try:
        from modules import database as db
    except ImportError:
        st.error("🚨 Erro Crítico: Não foi possível importar 'modules/database.py'. Verifique a estrutura de pastas.")
        st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="Início – Biblia Narrada", layout="wide")

# Inicializa banco de dados
if hasattr(db, 'init_db'):
    db.init_db()

# ---------------------------------------------------------------------
# 3. FUNÇÕES DE FORMATAÇÃO (REGEX)
# ---------------------------------------------------------------------

def limpar_referencia_evangelho(ref_bruta):
    """
    Limpa especificamente a referência do Evangelho:
    - Remove 'Proclamação...', 'Evangelho segundo...', 'São', 'Santo'.
    - Adiciona ', Cap. ' antes do número do capítulo.
    """
    if not ref_bruta: return "Evangelho"

    texto = ref_bruta
    
    # 1. Remove prefixos longos (Case Insensitive)
    texto = re.sub(r'^(Proclamação do\s+)?Evangelho(\s+de Jesus Cristo)?\s+segundo\s+', '', texto, flags=re.IGNORECASE)
    
    # 2. Remove títulos de Santos (São, Santo, Santa) isolados
    texto = re.sub(r'\b(São|Santo|Santa)\b\s*', '', texto, flags=re.IGNORECASE)
    
    # 3. Garante formato "Livro, Cap. N"
    # Procura: (Letras) espaço (Dígitos)
    # Substitui por: (Letras), Cap. (Dígitos)
    # Ex: "Mateus 9,35" -> "Mateus, Cap. 9,35"
    texto = re.sub(r'([A-Za-zÀ-ÿ]+)\s+(\d+)', r'\1, Cap. \2', texto)

    return texto.strip()

def formatar_referencia_geral(ref_bruta):
    """Limpeza básica para outras leituras."""
    if not ref_bruta: return ""
    # Remove "Leitura do..."
    texto = re.sub(r'^Leitura\s+(do|da)\s+', '', ref_bruta, flags=re.IGNORECASE)
    return texto.strip()

# ---------------------------------------------------------------------
# 4. INTEGRAÇÃO COM A API V2 (Dancrf)
# ---------------------------------------------------------------------

def fetch_liturgia(date_obj):
    # Data formatada para salvar no banco (ID único)
    date_str_db = date_obj.strftime('%Y-%m-%d')
    
    # 1. Verifica Cache Local
    cached = db.carregar_liturgia(date_str_db)
    if cached:
        st.toast(f"Carregado do banco local: {date_str_db}", icon="💾")
        return cached
    
    # 2. Configura Requisição
    BASE_URL = "https://liturgia.up.railway.app/v2/"
    
    # Parâmetros conforme documentação: ?dia=X&mes=Y&ano=Z
    params = {
        "dia": date_obj.day,
        "mes": date_obj.month,
        "ano": date_obj.year
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=20)
        
        if response.status_code == 404:
            st.warning(f"A API retornou 404. Liturgia não encontrada para {date_obj.strftime('%d/%m/%Y')}.")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # --- PARSING DOS DADOS (V2) ---
        
        # Cor e Nome do Dia
        cor_liturgica = data.get('cor', 'Verde')
        nome_dia = data.get('liturgia', data.get('dia', 'Dia Litúrgico'))
        
        leituras_formatadas = []
        obj_leituras = data.get('leituras', {})

        # Função interna para processar listas da API
        def processar_lista(chave_api, titulo_sistema, tipo_formatacao="geral"):
            itens = obj_leituras.get(chave_api, [])
            
            # Se não for lista, transforma em lista (robustez)
            if isinstance(itens, dict): itens = [itens]
            if not isinstance(itens, list): return

            for item in itens:
                texto = item.get('texto', '')
                if not texto: continue # Pula se não tiver texto
                
                # Definição do Título (Ex: Primeira Leitura, Salmo...)
                # Se vier 'tipo' no JSON (comum em extras), usa ele. Senão usa o padrão do sistema.
                tipo_real = item.get('tipo', titulo_sistema)
                
                # Definição da Referência
                ref_bruta = item.get('referencia', '')
                
                # Aplica formatação específica
                if tipo_formatacao == "evangelho":
                    ref_final = limpar_referencia_evangelho(ref_bruta)
                elif tipo_formatacao == "salmo":
                    ref_final = ref_bruta # Salmo geralmente não mexe
                    # Adiciona refrão ao texto se existir
                    refrao = item.get('refrao', '')
                    if refrao:
                        texto = f"Refrão: {refrao}\n\n{texto}"
                else:
                    ref_final = formatar_referencia_geral(ref_bruta)

                # Adiciona à lista final
                leituras_formatadas.append({
                    'tipo': tipo_real,
                    'titulo': tipo_real, # Usado no header do card
                    'ref': ref_final,    # Usado no subheader
                    'texto': texto
                })

        # Processa na ordem litúrgica
        processar_lista('primeiraLeitura', 'Primeira Leitura', 'geral')
        processar_lista('salmo', 'Salmo Responsorial', 'salmo')
        processar_lista('segundaLeitura', 'Segunda Leitura', 'geral')
        processar_lista('evangelho', 'Evangelho', 'evangelho')
        
        # Processa Extras (Vigílias, etc)
        # Em 'extras', o campo 'tipo' ou 'titulo' define o nome da leitura
        if 'extras' in obj_leituras:
            for item in obj_leituras['extras']:
                nome = item.get('tipo') or item.get('titulo') or "Leitura Extra"
                ref = item.get('referencia', '')
                texto = item.get('texto', '')
                
                if texto:
                    leituras_formatadas.append({
                        'tipo': nome,
                        'titulo': nome,
                        'ref': formatar_referencia_geral(ref),
                        'texto': texto
                    })

        if not leituras_formatadas:
            st.error("A API respondeu, mas não foram encontradas leituras no JSON.")
            return None

        # Monta objeto final
        final_data = {
            'data': date_str_db,
            'nome_dia': nome_dia,
            'cor': cor_liturgica,
            'leituras': leituras_formatadas
        }
        
        # Salva no cache para não chamar API de novo
        db.salvar_liturgia(date_str_db, final_data)
        return final_data

    except Exception as e:
        st.error(f"Erro de conexão com a API: {e}")
        return None

# ---------------------------------------------------------------------
# 5. FUNÇÕES DE INTERFACE (STREAMLIT)
# ---------------------------------------------------------------------

def get_leitura_status_logic(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    prog, em_prod = db.load_status(chave)
    if prog:
        default.update(prog)
        return default, em_prod
    return default, 0

def handle_leitura_selection(data_str, tipo_leitura):
    # Carrega dados
    dados_dia = fetch_liturgia(datetime.strptime(data_str, '%Y-%m-%d'))
    if not dados_dia: return
    
    # Encontra a leitura selecionada na lista
    leitura = next((l for l in dados_dia['leituras'] if l['tipo'] == tipo_leitura), None)
    if not leitura: 
        st.error("Leitura não encontrada nos dados.")
        return

    # Atualiza sessão
    prog, _ = get_leitura_status_logic(data_str, tipo_leitura)
    
    st.session_state.update({
        'data_atual_str': data_str,
        'leitura_atual': {**leitura, 'cor_liturgica': dados_dia['cor']},
        'progresso_leitura_atual': prog
    })
    
    # Salva status e navega
    db.update_status(f"{data_str}-{tipo_leitura}", data_str, tipo_leitura, prog, 1)
    st.switch_page("pages/1_Roteiro_Viral.py")

# ---------------------------------------------------------------------
# 6. LAYOUT PRINCIPAL
# ---------------------------------------------------------------------

st.title("📖 Biblia Narrada: Painel de Produção")

# --- DASHBOARD (EM PRODUÇÃO) ---
st.header("📋 Em Produção")
try:
    status_raw = db.load_status()
except:
    status_raw = {}

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

# --- HISTÓRICO LOCAL ---
try:
    cache = db.listar_historico()
except:
    cache = []

if cache:
    st.subheader("🗓️ Histórico Local")
    col_c1, col_c2 = st.columns([3,1])
    with col_c1:
        selected_cache = st.selectbox("Itens salvos:", [f"{c['Data']} - {c['Cor Litúrgica']}" for c in cache], key="sel_cache")
    with col_c2:
        if st.button("Carregar do Histórico"):
            data_sel = selected_cache.split(' - ')[0]
            st.session_state['data_busca'] = data_sel
            # Limpa dados antigos da sessão para forçar recarga do banco
            if 'dados_liturgia' in st.session_state: del st.session_state['dados_liturgia']
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

# --- EXIBIÇÃO DOS RESULTADOS ---
data_busca = st.session_state.get('data_busca')

if data_busca:
    # Chama a função de busca (que agora trata arrays corretamente)
    dados = fetch_liturgia(datetime.strptime(data_busca, '%Y-%m-%d'))
    
    if dados:
        cor_map = {"roxo": "🟣", "verde": "🟢", "vermelho": "🔴", "branco": "⚪", "rosa": "🌸"}
        cor_emoji = cor_map.get(dados['cor'].lower(), "🎨")
        
        st.success(f"{cor_emoji} **{dados['nome_dia']}** ({dados['cor']})")
        
        if 'leituras' in dados:
            # Layout responsivo
            cols = st.columns(len(dados['leituras']))
            for i, l in enumerate(dados['leituras']):
                with cols[i % 4]: # Garante no máximo 4 por linha
                    with st.container(border=True):
                        # Título (Ex: Evangelho)
                        st.subheader(l['tipo'])
                        
                        # Referência Formatada (Ex: Mateus, Cap. 3, 1-12)
                        st.markdown(f"**{l['ref']}**")
                        
                        st.markdown("---")
                        
                        # Botão de Ação
                        if st.button(f"Produzir", key=f"prod_{i}_{data_busca}", use_container_width=True):
                            handle_leitura_selection(data_busca, l['tipo'])
