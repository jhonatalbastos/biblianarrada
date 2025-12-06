import streamlit as st
import requests
import sqlite3
import json
from datetime import datetime, timedelta
from requests.exceptions import Timeout, RequestException, HTTPError 

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

def listar_cache_liturgia():
    """Retorna uma lista de dicionários com data, cor e último acesso do cache."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT data_liturgia, cor, ultimo_acesso FROM historico ORDER BY data_liturgia DESC')
    rows = c.fetchall()
    conn.close()
    
    lista_cache = []
    for data, cor, acesso in rows:
        # Formata a data de acesso para ser mais legível
        data_acesso = datetime.strptime(acesso.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        lista_cache.append({
            'Data': data,
            'Cor Litúrgica': cor,
            'Último Acesso': data_acesso
        })
    return lista_cache

def salvar_no_banco(data_str, json_data):
    """Salva os dados da liturgia (JSON) no cache."""
    conn = get_db_connection()
    c = conn.cursor()
    json_str = json.dumps(json_data)
    cor = json_data.get('cor', 'Branco') 
    c.execute('''INSERT OR REPLACE INTO historico 
                 (data_liturgia, json_completo, cor, ultimo_acesso) 
                 VALUES (?, ?, ?, CURRENT_TIMESTAMP)''', 
              (data_str, json_str, cor))
    conn.commit()
    conn.close()

def load_producao_status(chave=None):
    """
    Carrega o progresso de uma leitura específica ou de todas as leituras ativas.
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
        # Usando '!= ?' para garantir a robustez na comparação de strings no SQLite
        c.execute(f'''SELECT chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao 
                     FROM producao_status 
                     WHERE em_producao = 1 OR progresso != ? ''', (default_progresso_json,))
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


# --- INTEGRAÇÃO COM API EXTERNA (REFINADA) ---

def fetch_liturgia(date_obj):
    """
    Busca a liturgia do dia na API externa (usando o endpoint Vercel/Proxy) ou no cache local.
    A API padrão é https://api.liturgiadiaria.net/api/v1/liturgia
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Tenta carregar do cache
    cached_data = carregar_do_banco(date_str)
    if cached_data:
        st.info(f"Dados de **{date_str}** carregados do cache local.")
        return cached_data
    
    # 2. Define o endpoint da API
    # Prioriza o segredo (se for um proxy Vercel customizado) ou usa a API pública principal
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api.liturgiadiaria.net/api/v1/liturgia")
    
    API_URL = f"{BASE_URL}/{date_str}"
    
    # st.info(f"Buscando dados da liturgia para {date_str} em: {BASE_URL}...")
    
    try:
        # Aumentando o timeout para dar mais robustez
        response = requests.get(API_URL, timeout=15) 
        response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
        data = response.json()
        
        # 3. Processamento e Salvamento
        if data and 'leituras' in data:
            
            leituras_formatadas = []
            # Mapeamento para normalizar os tipos de leitura
            tipo_mapeamento = {
                "Primeira Leitura": "Primeira Leitura",
                "Salmo Responsorial": "Salmo",
                "Segunda Leitura": "Segunda Leitura",
                "Evangelho": "Evangelho",
                "Evangelho (Missa do dia)": "Evangelho", 
                "Salmo": "Salmo" 
            }
            
            for leitura in data.get('leituras', []):
                if 'texto' in leitura and 'titulo' in leitura and 'ref' in leitura:
                    # Tenta mapear o tipo, caso contrário, usa o título original
                    tipo_original = leitura['titulo'].strip()
                    tipo = tipo_mapeamento.get(tipo_original, tipo_original)
                    
                    leituras_formatadas.append({
                        'tipo': tipo,
                        'titulo': tipo_original,
                        'ref': leitura['ref'],
                        'texto': leitura['texto']
                    })
            
            cor = data.get('cor', 'Branco')

            final_data = {
                'data': date_str,
                'nome_dia': data.get('nome', 'Dia Litúrgico'),
                'cor': cor,
                'leituras': leituras_formatadas
            }
            
            salvar_no_banco(date_str, final_data)
            st.success(f"Dados de **{date_str}** buscados e salvos no cache. Cor: **{cor}**")
            return final_data
        
        else:
            st.error("Resposta da API inválida ou sem leituras.")
            return None 

    except Timeout:
        st.error("Erro: Tempo limite da requisição à API excedido.")
    except HTTPError as e:
        st.error(f"Erro HTTP {e.response.status_code} ao buscar dados da API. Detalhe: {e}")
    except RequestException as e:
        st.error(f"🚨 ERRO DE CONEXÃO 🚨 Falha ao tentar buscar dados da URL: {API_URL}. Detalhe do erro: {e}")
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

        # Contagem do progresso para exibir na coluna 'Status'
        etapas_completas = sum(progresso.values())
        total_etapas = len(default_progresso)
        
        if progresso.get('publicacao', False):
            status_liturgico = "🟢 Publicado"
        elif em_producao:
            # Mostra o progresso atualizado se estiver em produção
            status_liturgico = f"🚧 Em Produção ({etapas_completas}/{total_etapas})" 
        elif progresso_raw != default_progresso:
            status_liturgico = f"🟡 Rascunho ({etapas_completas}/{total_etapas})"
        else:
            status_liturgico = "⚪ Inativo"

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
            'Ação': f'<div id="action_btn_{chave}"></div>' 
        }
        table_data.append(row)
        
    if not table_data:
        st.info("Nenhuma leitura em produção ou com rascunho salvo.")
        return

    # Usando o st.dataframe nativo do Streamlit para tabelas interativas
    df = st.dataframe(
        table_data,
        column_config={
            "Ação": st.column_config.ButtonColumn("Selecionar", help="Clique para iniciar/continuar a produção desta leitura", key="dashboard_action_btn"),
        },
        hide_index=True,
        use_container_width=True,
        column_order=['Data', 'Tipo', 'Status', 'Roteiro', 'Imagem', 'Áudio', 'Overlay', 'Legendas', 'Vídeo', 'Publicar', 'Ação']
    )
    
    # Processamento do clique do botão na tabela
    clicked_row_index = st.session_state.get('dashboard_action_btn')
    if clicked_row_index is not None and clicked_row_index != -1:
        selected_item = data_list[clicked_row_index]
        handle_leitura_selection(selected_item['data_liturgia'], selected_item['tipo_leitura'])


def handle_leitura_selection(data_str, tipo_leitura):
    """Lida com a seleção de uma leitura e navega para a primeira página de produção."""
    
    # 1. Carrega os dados completos do dia (usa fetch_liturgia, que verifica o cache)
    try:
        data_obj = datetime.strptime(data_str, '%Y-%m-%d')
    except ValueError:
        st.error(f"Erro: Data inválida para seleção: {data_str}")
        return
        
    # Chama fetch_liturgia para garantir que os dados do dia estejam na sessão e no cache
    dados_dia = fetch_liturgia(data_obj) 
    
    if not dados_dia or 'leituras' not in dados_dia:
        st.warning(f"Não foi possível carregar os dados de liturgia para {data_str}.")
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
    # Adiciona a cor litúrgica para ser usada em outras páginas (ex: tema visual do roteiro)
    leitura_completa['cor_liturgica'] = dados_dia['cor'] 
    st.session_state['leitura_atual'] = leitura_completa 
    st.session_state['progresso_leitura_atual'] = progresso
    
    # 5. Marca como 'Em Produção' e navega
    chave = f"{data_str}-{tipo_leitura}"
    # O status 'em_producao' é sempre 1 ao iniciar/continuar a produção
    update_producao_status(chave, data_str, tipo_leitura, progresso, 1) 
    
    if 'artefatos' not in st.session_state:
        st.session_state['artefatos'] = {}
    
    st.info(f"Produção de **{tipo_leitura}** de {data_str} iniciada/continuada. Navegando...")
    st.switch_page("pages/1_Roteiro_Viral.py")


# --- FUNÇÃO PARA SELECIONAR DO CACHE ---

def select_from_cache(cached_data_list):
    """Cria a tabela de dados em cache e permite a seleção da data."""
    st.subheader("🗓️ Datas Salvas no Cache (Seu Histórico)")
    
    if not cached_data_list:
        st.info("Nenhuma liturgia encontrada no cache local (biblia_narrada_db.sqlite).")
        return
    
    table_data = []
    for item in cached_data_list:
        table_data.append({
            'Data': item['Data'],
            'Cor': item['Cor Litúrgica'],
            'Último Acesso': item['Último Acesso'],
            'Ação': f'<div id="cache_btn_{item["Data"]}"></div>' 
        })

    # Renderiza a tabela de cache
    st.dataframe(
        table_data,
        column_config={
            "Ação": st.column_config.ButtonColumn("Ver Leituras", help="Carregar as leituras desta data para seleção", key="cache_action_btn"),
        },
        hide_index=True,
        use_container_width=True,
        column_order=['Data', 'Cor', 'Último Acesso', 'Ação']
    )
    
    # Processamento do clique do botão na tabela de cache
    clicked_row_index = st.session_state.get('cache_action_btn')
    if clicked_row_index is not None and clicked_row_index != -1:
        data_str_selecionada = cached_data_list[clicked_row_index]['Data']
        # Define a data_busca para acionar a lógica de carregamento de dados
        st.session_state['data_busca'] = data_str_selecionada
        st.success(f"Liturgia de **{data_str_selecionada}** selecionada. Use a seção de 'Busca' para recarregar os dados ou veja a seção 'Seleção de Leitura para Produção' abaixo.")
        st.rerun()


# --- LAYOUT PRINCIPAL ---

# --- Execução Inicial ---
if __name__ == '__main__':
    init_db()

st.title("📖 Biblia Narrada: Painel de Produção")

# --- DASHBOARD DE PRODUÇÃO (Tabela) ---

st.header("📋 Dashboard de Leituras em Produção")
st.markdown("Gerencie o status de produção das leituras ativas e rascunhos salvos.")

leituras_em_producao_full = load_producao_status()
data_list_dashboard = []

# Filtra: mostra o que está em produção (em_producao=1) ou tem progresso, mas não está publicado e inativo
for chave, item in leituras_em_producao_full.items():
    is_published_and_inactive = item['progresso'].get('publicacao', False) and not item.get('em_producao', 0)
    if not is_published_and_inactive:
        data_list_dashboard.append({
            'chave': chave,
            'data_liturgia': item['data_liturgia'],
            'tipo_leitura': item['tipo_leitura'],
            'progresso': item['progresso'],
            'em_producao': item['em_producao']
        })
        
st.session_state['leituras_em_producao'] = leituras_em_producao_full

if data_list_dashboard:
    create_dashboard_table(data_list_dashboard)
else:
    st.info("Nenhuma leitura está marcada como 'Em Produção' ou possui rascunho salvo no momento.")

st.markdown("---")

# --- LISTAGEM DE CACHE ---
cached_data = listar_cache_liturgia()
select_from_cache(cached_data)

st.markdown("---")

# --- SELEÇÃO DE DATA / BUSCA DE API ---
st.header("🔍 Buscar Nova Liturgia (API)")

# Inicia a sessão com data_busca se for o primeiro acesso
if 'data_busca' not in st.session_state:
    st.session_state['data_busca'] = datetime.today().strftime('%Y-%m-%d')


with st.container(border=True):
    col1, col2 = st.columns([1, 3])

    data_hoje = datetime.today().date()
    # Obtém a data mais relevante (da busca ou a data de hoje) para o seletor
    data_str_to_fetch = st.session_state.get('data_busca', data_hoje.strftime('%Y-%m-%d'))
    try:
        data_inicial_obj = datetime.strptime(data_str_to_fetch, '%Y-%m-%d').date()
    except ValueError:
        data_inicial_obj = data_hoje

    with col1:
        data_selecionada = st.date_input(
            "📅 Selecionar Data da Liturgia",
            value=data_inicial_obj,
            min_value=data_hoje - timedelta(days=365), 
            max_value=data_hoje + timedelta(days=365),
            key='data_selecao'
        )
        
    with col2:
        st.markdown("<br>", unsafe_allow_html=True) 

        if st.button("Buscar Liturgia (API/Cache)", type="primary", use_container_width=True):
            st.session_state['data_busca'] = data_selecionada.strftime('%Y-%m-%d')
            # Força o carregamento da nova data
            if 'dados_liturgia' in st.session_state and st.session_state['dados_liturgia'].get('data') != st.session_state['data_busca']:
                 del st.session_state['dados_liturgia']
            st.rerun()

# LÓGICA DE BUSCA E PROCESSAMENTO DE DADOS (Executado após Rerun)
# Se a data do input for diferente da data da última busca, atualiza a data de busca
if data_selecionada.strftime('%Y-%m-%d') != st.session_state.get('data_busca'):
    data_str_to_fetch = data_selecionada.strftime('%Y-%m-%d')
    st.session_state['data_busca'] = data_str_to_fetch

dados_liturgia = None
data_str_to_fetch = st.session_state.get('data_busca')

# Carrega os dados se eles não estiverem na sessão para a data atual
if 'dados_liturgia' in st.session_state and st.session_state['dados_liturgia'].get('data') == data_str_to_fetch:
    dados_liturgia = st.session_state['dados_liturgia']
else:
    try:
        data_obj_to_fetch = datetime.strptime(data_str_to_fetch, '%Y-%m-%d')
        dados_liturgia = fetch_liturgia(data_obj_to_fetch)
        if dados_liturgia:
            st.session_state['dados_liturgia'] = dados_liturgia
    except ValueError:
        pass
    except TypeError:
        pass


# --- RENDERIZAÇÃO DA LITURGIA (Se disponível) ---

if dados_liturgia:
    st.markdown("---")
    
    liturgia_info = f"**{dados_liturgia.get('nome_dia', 'Dia Litúrgico')}**"
    cor_liturgica = dados_liturgia.get('cor', 'Branco')
    
    # Mapeamento de cores para um visual mais agradável
    cor_map = {
        'Verde': '#d4edda', 
        'Branco': '#f8f9fa', 
        'Vermelho': '#f8d7da', 
        'Roxo': '#e4e7ff', 
        'Rosa': '#f8c7d8'
    }
    bg_color = cor_map.get(cor_liturgica, '#f8f9fa')

    # Banner colorido usando HTML/CSS
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; border: 1px solid #ccc;">
        <h3 style="margin-top: 0; color: #333;">{liturgia_info}</h3>
        <p style="margin-bottom: 0;">Data: {data_str_to_fetch} | Cor Litúrgica: <strong>{cor_liturgica}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    
    st.subheader("Seleção de Leitura para Produção")
    
    leituras_disponiveis = []
    
    if 'leituras' in dados_liturgia:
        for leitura in dados_liturgia['leituras']:
            tipo_leitura = leitura['tipo']
            chave = f"{data_str_to_fetch}-{tipo_leitura}"
            progresso, em_producao = get_leitura_status(data_str_to_fetch, tipo_leitura)
            
            leituras_disponiveis.append({
                'tipo': tipo_leitura,
                'ref': leitura['ref'],
                'progresso': progresso,
                'em_producao': em_producao,
                'chave': chave
            })

    
    # Renderiza as colunas de leituras
    if leituras_disponiveis:
        cols_leituras = st.columns(len(leituras_disponiveis))
        
        default_progresso = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}

        for i, leitura in enumerate(leituras_disponiveis):
            progresso = leitura['progresso']
            
            # Define o status e o tipo de botão
            if leitura['em_producao']:
                 status_texto = "Continuar Produção"
                 btn_type = "primary"
                 icone = "➡️"
            elif progresso.get('publicacao', False):
                 status_texto = "Visualizar (Publicado)"
                 btn_type = "secondary"
                 icone = "👁️"
            elif progresso != default_progresso:
                 status_texto = "Continuar Rascunho"
                 btn_type = "secondary"
                 icone = "✍️"
            else:
                 status_texto = "Iniciar Produção"
                 btn_type = "secondary"
                 icone = "➕"

            
            with cols_leituras[i]:
                 with st.container(border=True):
                     st.markdown(f"**{leitura['tipo']}**")
                     st.caption(leitura['ref'])
                     
                     etapas_completas = sum(leitura['progresso'].values())
                     total_etapas = len(default_progresso)
                     progress_value = etapas_completas / total_etapas
                     
                     st.progress(progress_value, text=f"Progresso: {etapas_completas}/{total_etapas} etapas") 
                     
                     # Botão de Ação
                     if st.button(f"{icone} {status_texto}", key=f"select_leitura_{leitura['chave']}", type=btn_type, use_container_width=True):
                        handle_leitura_selection(data_str_to_fetch, leitura['tipo'])
    else:
        st.info("Nenhuma leitura encontrada para a data selecionada.")

else:
    st.warning("Liturgia não carregada. Por favor, use a lista do cache ou tente buscar uma nova data na API.")

# --- FOOTER ---
st.markdown("---")
# A variável BASE_URL é definida dentro de fetch_liturgia, então usamos o segredo ou o fallback aqui para o aviso
api_warning_url = st.secrets.get("LITURGIA_API_BASE_URL", "https://api.liturgiadiaria.net/api/v1/liturgia")
st.caption(f"Dados da liturgia fornecidos pela API. Fonte: `{api_warning_url}`. Última atualização de status: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
