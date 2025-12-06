import streamlit as st
import requests
import sqlite3
import json
from datetime import datetime, timedelta
import calendar # Corrigido: Usamos apenas 'datetime' e 'timedelta' da biblioteca 'datetime'

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Início – Biblia Narrada", layout="wide")

# --- BANCO DE DADOS E PERSISTÊNCIA ---
DB_FILE = 'biblia_narrada_db.sqlite'

def get_db_connection():
    """Cria e retorna a conexão com o banco de dados."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Inicializa as tabelas do banco de dados (se não existirem)."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabela para cache das liturgias (evita chamar API desnecessariamente)
    c.execute('''CREATE TABLE IF NOT EXISTS historico
                 (data_liturgia TEXT PRIMARY KEY, json_completo TEXT, cor TEXT, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                 
    # Tabela para rastrear o progresso da produção de cada leitura
    c.execute('''CREATE TABLE IF NOT EXISTS producao_status
                 (chave_leitura TEXT PRIMARY KEY, 
                  data_liturgia TEXT, 
                  tipo_leitura TEXT, 
                  progresso TEXT, 
                  em_producao INTEGER, 
                  ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    """Carrega os dados da liturgia (JSON) do cache."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    if res:
        return json.loads(res[0])
    return None

def salvar_no_banco(data_str, json_data):
    """Salva os dados da liturgia (JSON) no cache."""
    conn = get_db_connection()
    c = conn.cursor()
    json_str = json.dumps(json_data)
    cor = json_data.get('cor', 'Branco') # Assumindo que a cor está no nível superior
    c.execute('''INSERT OR REPLACE INTO historico 
                 (data_liturgia, json_completo, cor, ultimo_acesso) 
                 VALUES (?, ?, ?, CURRENT_TIMESTAMP)''', 
              (data_str, json_str, cor))
    conn.commit()
    conn.close()

def load_producao_status(chave=None):
    """
    Carrega o progresso de uma leitura específica ou de todas as leituras ativas.
    Retorna um dicionário de status se for chamada sem chave.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    if chave:
        c.execute('SELECT progresso, em_producao FROM producao_status WHERE chave_leitura = ?', (chave,))
        res = c.fetchone()
        conn.close()
        if res:
            return json.loads(res[0]), res[1]
        return None, 0
    else:
        # Carrega todas as leituras que estão ativas OU que têm algum progresso
        default_progresso_json = json.dumps({"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False})
        c.execute(f'''SELECT chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao 
                     FROM producao_status 
                     WHERE em_producao = 1 OR progresso != '{default_progresso_json}' ''')
        rows = c.fetchall()
        conn.close()
        all_status = {}
        for row in rows:
            chave, data_liturgia, tipo_leitura, progresso_json, em_producao = row
            all_status[chave] = {
                'data_liturgia': data_liturgia,
                'tipo_leitura': tipo_leitura,
                'progresso': json.loads(progresso_json),
                'em_producao': em_producao
            }
        return all_status

def update_producao_status(chave, data_liturgia, tipo_leitura, progresso_dict, em_producao):
    """Atualiza o estado persistente de progresso e flag 'em_producao'."""
    conn = get_db_connection()
    c = conn.cursor()
    progresso_json = json.dumps(progresso_dict)
    c.execute('''INSERT OR REPLACE INTO producao_status 
                 (chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao, ultimo_acesso) 
                 VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
              (chave, data_liturgia, tipo_leitura, progresso_json, 1 if em_producao else 0))
    conn.commit()
    conn.close()
    
def get_leitura_status(data_str, tipo_leitura):
    """Wrapper para carregar status ou retornar default se não existir."""
    chave = f"{data_str}-{tipo_leitura}"
    default_progresso = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    progresso_json, em_producao = load_producao_status(chave)
    if progresso_json:
        progresso = default_progresso.copy()
        progresso.update(progresso_json)
        return progresso, em_producao
    return default_progresso, 0


# --- INTEGRAÇÃO COM API EXTERNA (Simulada) ---

def fetch_liturgia(date_obj):
    """
    Busca a liturgia do dia na API externa ou no cache local.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Tenta carregar do cache
    cached_data = carregar_do_banco(date_str)
    if cached_data:
        st.info(f"Dados de **{date_str}** carregados do cache local.")
        return cached_data
    
    # 2. Se não estiver no cache, busca na API (Simulação: API da ACI Digital)
    API_URL = f"https://liturgiadiaria.pt/api/v1/liturgia/{date_str}"
    
    st.info(f"Buscando dados da liturgia para {date_str} na API externa...")
    
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
        data = response.json()
        
        # 3. Processamento e Salvamento
        if data and 'leituras' in data:
            
            # Formatação básica das leituras para o formato interno
            leituras_formatadas = []
            for leitura in data['leituras']:
                if 'texto' in leitura and 'titulo' in leitura and 'ref' in leitura:
                    # Normaliza o tipo de leitura
                    tipo_mapeamento = {
                        "Primeira Leitura": "Primeira Leitura",
                        "Salmo Responsorial": "Salmo",
                        "Segunda Leitura": "Segunda Leitura",
                        "Evangelho": "Evangelho"
                    }
                    tipo = tipo_mapeamento.get(leitura['titulo'].strip(), leitura['titulo'].strip())
                    
                    leituras_formatadas.append({
                        'tipo': tipo,
                        'titulo': leitura['titulo'],
                        'ref': leitura['ref'],
                        'texto': leitura['texto']
                    })
            
            # Cor Litúrgica
            cor = data.get('cor', 'Branco')

            final_data = {
                'data': date_str,
                'nome_dia': data.get('nome', 'Dia Litúrgico'),
                'cor': cor,
                'leituras': leituras_formatadas
            }
            
            salvar_no_banco(date_str, final_data)
            return final_data
        
        else:
            st.error("Resposta da API inválida ou sem leituras.")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Erro: Tempo limite da requisição à API excedido.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar dados da API: {e}")
    except json.JSONDecodeError:
        st.error("Erro ao decodificar a resposta JSON da API.")
        
    return None

# --- FUNÇÕES DE RENDERIZAÇÃO DA DASHBOARD ---

def get_status_emoji(key, progresso):
    """Retorna o emoji de status para a chave de progresso."""
    if progresso.get(key, False):
        return "✅"
    return "❌"

def create_dashboard_table(data_list):
    """Cria a tabela de progresso no Streamlit."""
    
    # Prepara os dados para a tabela
    table_data = []
    default_progresso = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}

    for item in data_list:
        chave = item['chave']
        progresso_raw = item['progresso']
        em_producao = item['em_producao']
        
        progresso = default_progresso.copy()
        progresso.update(progresso_raw)

        # Mapeamento do Status Litúrgico
        if progresso.get('publicacao', False) and not em_producao:
            status_liturgico = "🟢 Publicado"
        elif em_producao:
            status_liturgico = "🚧 Em Produção"
        elif progresso_raw != default_progresso:
            status_liturgico = "🟡 Rascunho/Pausado"
        else:
            status_liturgico = "⚪ Inativo"

        # Coluna de Ações
        action_key = f"select_{chave}"
        
        # Colunas de Progresso (emojis)
        row = {
            'Data': item['data_liturgia'],
            'Tipo': item['tipo_leitura'],
            'Status': status_liturgico,
            'Roteiro': get_status_emoji('roteiro', progresso),
            'Imagem': get_status_emoji('imagens', progresso),
            'Áudio': get_status_emoji('audio', progresso),
            'Overlay': get_status_emoji('overlay', progresso),
            'Legendas': get_status_emoji('legendas', progresso),
            'Vídeo': get_status_emoji('video', progresso),
            'Publicar': get_status_emoji('publicacao', progresso),
            'Ação': f'<div id="action_btn_{action_key}"></div>' # Placeholder para o botão
        }
        table_data.append(row)
        
    if not table_data:
        st.info("Nenhuma leitura em produção ou com rascunho salvo.")
        return

    df = st.dataframe(
        table_data,
        column_config={
            "Ação": st.column_config.ButtonColumn("Selecionar", help="Clique para iniciar/continuar a produção desta leitura", key="dashboard_action_btn"),
        },
        hide_index=True,
        use_container_width=True,
        # Adiciona tooltip nas colunas de progresso
        column_order=['Data', 'Tipo', 'Status', 'Roteiro', 'Imagem', 'Áudio', 'Overlay', 'Legendas', 'Vídeo', 'Publicar', 'Ação']
    )
    
    # Processa o clique no botão
    clicked_row_index = st.session_state.get('dashboard_action_btn')
    if clicked_row_index is not None and clicked_row_index != -1:
        selected_item = data_list[clicked_row_index]
        handle_leitura_selection(selected_item['data_liturgia'], selected_item['tipo_leitura'])


def handle_leitura_selection(data_str, tipo_leitura):
    """Lida com a seleção de uma leitura e navega para a primeira página de produção."""
    
    # 1. Carrega os dados completos do dia
    dados_dia = carregar_do_banco(data_str)
    
    if not dados_dia or 'leituras' not in dados_dia:
        st.error("Erro ao carregar dados da liturgia. Tente recarregar ou buscar novamente.")
        return
        
    # 2. Encontra a leitura específica
    leitura_completa = next((l for l in dados_dia['leituras'] if l['tipo'] == tipo_leitura), None)
    
    if not leitura_completa:
        st.error(f"Leitura do tipo '{tipo_leitura}' não encontrada para o dia {data_str}.")
        return

    # 3. Carrega ou inicializa o progresso
    progresso, _ = get_leitura_status(data_str, tipo_leitura)

    # 4. Salva no Session State
    st.session_state['data_atual_str'] = data_str
    st.session_state['leitura_atual'] = leitura_completa
    st.session_state['leitura_atual']['cor_liturgica'] = dados_dia['cor']
    st.session_state['progresso_leitura_atual'] = progresso
    
    # 5. Marca como 'Em Produção' e navega
    chave = f"{data_str}-{tipo_leitura}"
    update_producao_status(chave, data_str, tipo_leitura, progresso, 1) # 1 = Em Produção
    
    # Inicializa artefatos se não existirem
    if 'artefatos' not in st.session_state:
        st.session_state['artefatos'] = {}
    
    st.info(f"Produção de **{tipo_leitura}** de {data_str} iniciada/continuada.")
    st.switch_page("pages/1_Roteiro_Viral.py")


# --- LAYOUT E INTERAÇÃO DO USUÁRIO ---

# 1. Seleção de Data
col1, col2 = st.columns([1, 3])

with col1:
    data_hoje = datetime.today().date()
    data_selecionada = st.date_input(
        "📅 Selecionar Data da Liturgia",
        value=data_hoje,
        min_value=data_hoje - timedelta(days=180),
        max_value=data_hoje + timedelta(days=365),
        key='data_selecao'
    )
    
with col2:
    st.markdown("<br>", unsafe_allow_html=True) # Espaçamento para alinhar o botão

    if st.button("🔍 Buscar Liturgia e Atualizar Dashboard", type="primary", use_container_width=True):
        st.session_state['data_busca'] = data_selecionada.strftime('%Y-%m-%d')
        st.rerun()

# --- LÓGICA DE BUSCA E PROCESSAMENTO DE DADOS ---

# A data a ser buscada/processada é a data do input, a menos que o botão "Buscar" tenha sido clicado.
data_str_input = data_selecionada.strftime('%Y-%m-%d')
data_str_to_fetch = st.session_state.get('data_busca', data_str_input)

# Verifica se precisa buscar os dados da liturgia
dados_liturgia = None
if 'dados_liturgia' in st.session_state and st.session_state['dados_liturgia'].get('data') == data_str_to_fetch:
    dados_liturgia = st.session_state['dados_liturgia']
else:
    dados_liturgia = fetch_liturgia(datetime.strptime(data_str_to_fetch, '%Y-%m-%d'))
    if dados_liturgia:
        st.session_state['dados_liturgia'] = dados_liturgia

# --- RENDERIZAÇÃO DA LITURGIA (Se disponível) ---

if dados_liturgia:
    st.markdown("---")
    
    liturgia_info = f"**{dados_liturgia.get('nome_dia', 'Dia Litúrgico')}**"
    cor_liturgica = dados_liturgia.get('cor', 'Branco')
    
    # Adiciona cor de fundo baseada na cor litúrgica (simulação)
    cor_map = {
        'Verde': '#d4edda', 
        'Branco': '#f8f9fa', 
        'Vermelho': '#f8d7da', 
        'Roxo': '#e4e7ff', 
        'Rosa': '#f8c7d8'
    }
    bg_color = cor_map.get(cor_liturgica, '#f8f9fa')

    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px;">
        <h3 style="margin-top: 0;">{liturgia_info}</h3>
        <p>Data: {data_str_to_fetch} | Cor Litúrgica: <strong>{cor_liturgica}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    
    st.subheader("Seleção de Leitura para Produção")
    
    leituras_disponiveis = []
    
    # Prepara a lista de leituras e checa o progresso
    if 'leituras' in dados_liturgia:
        for leitura in dados_liturgia['leituras']:
            tipo_leitura = leitura['tipo']
            chave = f"{data_str_to_fetch}-{tipo_leitura}"
            progresso, em_producao = get_leitura_status(data_str_to_fetch, tipo_leitura)
            
            # Checa se esta leitura está na lista de produções ativas (para o dashboard)
            is_active_prod = chave in st.session_state.get('leituras_em_producao', {})
            
            leituras_disponiveis.append({
                'tipo': tipo_leitura,
                'ref': leitura['ref'],
                'progresso': progresso,
                'em_producao': em_producao,
                'is_active_prod': is_active_prod,
                'chave': chave
            })

    
    # Renderiza os botões de seleção
    cols_leituras = st.columns(len(leituras_disponiveis) if leituras_disponiveis else 1)
    
    for i, leitura in enumerate(leituras_disponiveis):
        progresso = leitura['progresso']
        status_emoji = get_status_emoji('publicacao', progresso) if progresso.get('publicacao') else get_status_emoji('video', progresso)
        
        btn_label = f"{status_emoji} {leitura['tipo']}"
        
        # Define o tipo do botão: primary se já estiver em produção, secundário caso contrário
        btn_type = "primary" if leitura['em_producao'] else "secondary"
        
        with cols_leituras[i]:
             # Usa um container expander/info para a visualização da ref/progresso
             with st.container(border=True):
                 st.markdown(f"**{leitura['tipo']}**")
                 st.caption(leitura['ref'])
                 
                 # Detalhe de Progresso
                 if leitura['progresso'] != default_progresso:
                     etapas_completas = sum(leitura['progresso'].values())
                     st.progress(etapas_completas, text=f"Progresso: {etapas_completas}/7 etapas completas")
                 
                 
                 if st.button(btn_label, key=f"select_leitura_{leitura['chave']}", type=btn_type, use_container_width=True):
                    handle_leitura_selection(data_str_to_fetch, leitura['tipo'])

else:
    st.warning("Liturgia não carregada ou API indisponível. Por favor, tente novamente ou verifique a conexão.")

# --- DASHBOARD DE PRODUÇÃO (Tabela) ---

st.markdown("---")
st.header("📋 Dashboard de Leituras em Produção")

# Carrega e exibe a lista completa de produções ativas
leituras_em_producao_full = load_producao_status()
data_list_dashboard = []

# Mapeia os dados carregados para o formato da tabela
for chave, item in leituras_em_producao_full.items():
    if not (item['progresso'].get('publicacao', False) and not item.get('em_producao', 0)): # Exclui os que foram publicados e desativados
        data_list_dashboard.append({
            'chave': chave,
            'data_liturgia': item['data_liturgia'],
            'tipo_leitura': item['tipo_leitura'],
            'progresso': item['progresso'],
            'em_producao': item['em_producao']
        })
        
# Atualiza o estado global das leituras em produção (usado pela barra de navegação)
st.session_state['leituras_em_producao'] = leituras_em_producao_full

if data_list_dashboard:
    create_dashboard_table(data_list_dashboard)
else:
    st.info("Nenhuma leitura está marcada como 'Em Produção' ou possui rascunho salvo no momento.")

# --- FOOTER ---
st.markdown("---")
# LINHA 439 CORRIGIDA: datetime.datetime.now()
st.caption(f"Dados da liturgia fornecidos por API externa. Última atualização de status: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


# --- Execução Inicial ---
if __name__ == '__main__':
    # Garante que o DB está pronto antes de qualquer interação
    init_db()
