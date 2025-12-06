import streamlit as st
import requests
import sqlite3
import json
import datetime
from datetime import timedelta
import calendar

# --- Configuração da Página ---
st.set_page_config(page_title="Início - Dashboard", page_icon="🎛️", layout="wide")

# --- Variáveis Globais de Estado ---
# Nome do arquivo do banco de dados SQLite para persistência
DB_FILE = 'biblia_narrada_db.sqlite' 

# --- Funções de Banco de Dados ---
def get_db_connection():
    """Cria e retorna a conexão com o banco de dados."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Inicializa as tabelas do banco de dados se elas não existirem."""
    conn = get_db_connection()
    c = conn.cursor()
    # Tabela 1: Cache da Liturgia (para evitar chamadas repetidas à API)
    c.execute('''CREATE TABLE IF NOT EXISTS historico 
                 (data_liturgia TEXT PRIMARY KEY, santo TEXT, cor TEXT, json_completo TEXT, data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Tabela 2: Estado de Produção (Onde está o progresso persistente)
    c.execute('''CREATE TABLE IF NOT EXISTS producao_status 
                 (chave_leitura TEXT PRIMARY KEY, 
                 data_liturgia TEXT, 
                 tipo_leitura TEXT,
                 progresso TEXT, 
                 em_producao INTEGER,
                 ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def salvar_no_banco(dados):
    """Salva os dados completos da liturgia (JSON) no cache."""
    conn = get_db_connection()
    c = conn.cursor()
    json_str = json.dumps(dados, ensure_ascii=False)
    # data_liturgia está no formato DD/MM/AAAA
    data_str = dados.get("data") 
    c.execute('INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo) VALUES (?, ?, ?, ?)', 
              (data_str, dados.get('liturgia'), dados.get('cor'), json_str))
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    """Carrega os dados da liturgia pelo formato DD/MM/AAAA."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    if res:
        return json.loads(res[0])
    return None

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

def load_producao_status(chave=None):
    """
    Carrega o progresso de uma leitura específica ou de todas as leituras ativas.
    Retorna o progresso (dict) e o status 'em_producao' (int)
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
        # O default_progresso (7x False) é o estado de 'nenhum progresso'
        default_progresso_json = json.dumps({"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False})
        
        # Seleciona as leituras que:
        # 1. Estão com o flag 'em_producao' ligado (em_producao = 1)
        # OU
        # 2. Possuem um progresso diferente do estado inicial (progresso != default_progresso_json)
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

def get_leitura_status(data_str, tipo_leitura):
    """Wrapper para carregar status ou retornar default se não existir."""
    chave = f"{data_str}-{tipo_leitura}"
    default_progresso = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    
    progresso_json, em_producao = load_producao_status(chave)
    
    if progresso_json:
        # Garante que todas as chaves existam para evitar KeyError nas etapas futuras
        progresso = default_progresso.copy()
        progresso.update(progresso_json)
        return progresso, em_producao
    
    return default_progresso, 0


# --- Funções de Lógica e Ações ---

def buscar_liturgia_api(data_obj):
    """Busca a liturgia diária na API externa."""
    # data_obj é um objeto datetime.date
    dia, mes, ano = data_obj.day, data_obj.month, data_obj.year
    url = f"https://liturgia.up.railway.app/{dia}-{mes}-{ano}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404: return None, "Liturgia não encontrada (data futura ou indisponível)."
        if resp.status_code != 200: return None, f"Erro na API: {resp.status_code}"
        d = resp.json()
        
        def safe_extract(source, key, sub_key="texto"):
            val = source.get(key)
            if val is None: return ""
            if isinstance(val, str): return "" if sub_key == "referencia" else val
            if isinstance(val, dict): return val.get(sub_key, "")
            return str(val)

        return {
            "data": d.get("data", f"{dia:02d}/{mes:02d}/{ano}"), # Formato DD/MM/AAAA
            "liturgia": d.get("liturgia", "Liturgia Diária"),
            "cor": d.get("cor", "N/A"),
            "leituras": [
                {"tipo": "1ª Leitura", "texto": safe_extract(d, "primeiraLeitura", "texto"), "ref": safe_extract(d, "primeiraLeitura", "referencia")},
                {"tipo": "2ª Leitura", "texto": safe_extract(d, "segundaLeitura", "texto"), "ref": safe_extract(d, "segundaLeitura", "referencia")},
                {"tipo": "Salmo", "texto": safe_extract(d, "salmo", "texto"), "ref": safe_extract(d, "salmo", "referencia")},
                {"tipo": "Evangelho", "texto": safe_extract(d, "evangelho", "texto"), "ref": safe_extract(d, "evangelho", "referencia")}
            ]
        }, None
    except Exception as e:
        return None, str(e)


def set_leitura_em_producao(data_str, tipo_leitura, em_producao):
    """Marca uma leitura como 'Em Produção' ou desativa o flag."""
    chave = f"{data_str}-{tipo_leitura}"
    
    # Carrega estado atual ou default (garantindo que o progresso não seja perdido)
    progresso, _ = get_leitura_status(data_str, tipo_leitura)
    
    update_producao_status(chave, data_str, tipo_leitura, progresso, em_producao)
    st.toast(f"Status de produção de {tipo_leitura} em {data_str} alterado para {'Ativo' if em_producao else 'Inativo'}.")
    # Atualiza o cache da sessão para o dropdown (nas páginas 1-7)
    st.session_state['leituras_em_producao'] = load_producao_status()

def selecionar_leitura(leitura_data, data_str, cor_liturgica="N/A"):
    """Define qual leitura está sendo trabalhada e redireciona."""
    lectura_data = leitura_data.copy()
    lectura_data['cor_liturgica'] = cor_liturgica
    
    st.session_state['leitura_atual'] = lectura_data
    st.session_state['data_atual_str'] = data_str
    
    # Garante que o progresso persistente seja carregado para a sessão
    chave = f"{data_str}-{leitura_data['tipo']}"
    progresso, _ = get_leitura_status(data_str, leitura_data['tipo'])
    st.session_state['progresso_leitura_atual'] = progresso
    
    # Redireciona para a primeira página de trabalho (Roteiro Viral)
    st.switch_page("pages/1_Roteiro_Viral.py") # Assumindo que esta é a primeira página de trabalho

def apagar_progresso_leitura(data_str, tipo_leitura):
    """Apaga o registro de progresso (incluindo o flag 'em_producao') do banco."""
    chave = f"{data_str}-{tipo_leitura}"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM producao_status WHERE chave_leitura = ?', (chave,))
    conn.commit()
    conn.close()
    
    # Limpa estado da sessão se for a leitura atual
    if 'leitura_atual' in st.session_state and f"{st.session_state['data_atual_str']}-{st.session_state['leitura_atual']['tipo']}" == chave:
        del st.session_state['leitura_atual']
        if 'progresso_leitura_atual' in st.session_state:
            del st.session_state['progresso_leitura_atual']
    
    st.toast(f"✅ Progresso de {tipo_leitura} em {data_str} apagado.")
    # Força recarregamento do dashboard
    st.session_state['leituras_em_producao'] = load_producao_status()


# --- Funções de Interface da Dashboard ---

def get_date_range_for_months():
    """Calcula o início do mês atual e o fim do próximo mês."""
    today = datetime.date.today()
    
    # Mês Atual
    start_current = today.replace(day=1)
    
    # Mês Seguinte
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    end_next = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])

    return start_current, end_next

def get_liturgia_data_range(start_date, end_date):
    """Busca dados da liturgia no cache ou na API para o range especificado."""
    delta = end_date - start_date
    all_data = []
    
    with st.status(f"Buscando e populando cache da liturgia de {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}..."):
        for i in range(delta.days + 1):
            date_obj = start_date + timedelta(days=i)
            data_str = date_obj.strftime("%d/%m/%Y")
            
            # 1. Tenta carregar do cache local (SQLite)
            dados_dia = carregar_do_banco(data_str)
            
            if not dados_dia:
                # 2. Se falhar, busca na API
                dados_api, err = buscar_liturgia_api(date_obj)
                if dados_api:
                    salvar_no_banco(dados_api) # Salva no cache para acesso futuro
                    dados_dia = dados_api
                else:
                    st.write(f"⚠️ Erro ao buscar {data_str}: {err}")
                    continue # Ignora dias com erro na API
            
            if dados_dia and 'leituras' in dados_dia:
                for leitura in dados_dia['leituras']:
                    if leitura.get('texto'): # Apenas leituras com texto válido
                        all_data.append({
                            'data': data_str,
                            'data_obj': date_obj,
                            'liturgia': dados_dia.get('liturgia'),
                            'cor': dados_dia.get('cor'),
                            'tipo': leitura.get('tipo'),
                            'ref': leitura.get('ref'),
                            'leitura_completa': leitura
                        })
    return all_data

def create_dashboard_table(data_list):
    """Cria a visualização da dashboard em formato de tabela com expanders."""
    # Agrupa por semana (usando o rótulo da semana para o expander)
    leituras_por_semana = {}
    
    for item in data_list:
        # Pega a data da segunda-feira para o rótulo da semana
        start_of_week = item['data_obj'] - timedelta(days=item['data_obj'].weekday())
        week_label = f"📅 Semana de {start_of_week.strftime('%d/%b')}"
        
        if week_label not in leituras_por_semana:
            leituras_por_semana[week_label] = []
            
        leituras_por_semana[week_label].append(item)
        
    # Ícones de Status para o cabeçalho
    status_icons = {
        'roteiro': '📝', 'imagens': '🎨', 'audio': '🔊', 
        'overlay': '🖼️', 'legendas': '💬', 'video': '🎬', 'publicacao': '🚀'
    }
    
    today = datetime.date.today()
    current_week_num = today.isocalendar()[1]
    
    st.markdown("""
        <style>
        /* Estilo para a tabela responsiva e compacta */
        .dashboard-row {
            display: flex;
            align-items: center;
            padding: 5px 0;
            border-bottom: 1px solid #f0f2f6;
        }
        .dashboard-col {
            padding: 0 5px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .header .dashboard-col {
            font-weight: bold;
            font-size: 0.85em;
        }
        .progress-bar-container {
            min-width: 60px; /* Garante que a barra não suma */
        }
        .stButton button {
            padding: 2px 5px !important;
            line-height: 1;
            font-size: 0.75rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    
    # Renderiza as semanas
    for week_label, leituras in leituras_por_semana.items():
        # A primeira leitura da semana define o número da semana para comparação
        is_current_week = leituras[0]['data_obj'].isocalendar()[1] == current_week_num
        
        # Expande a semana atual por padrão
        with st.expander(week_label, expanded=is_current_week):
            
            # Define as proporções da coluna (ajustadas para mobile)
            col_weights = [0.5, 1.5, 2.5, 1, 1.5] + [0.3] * 7 + [0.5]
            
            # Cabeçalho da Tabela
            header_cols = st.columns(col_weights)
            header_cols[0].markdown("<div class='dashboard-col header'>Prod.</div>", unsafe_allow_html=True) 
            header_cols[1].markdown("<div class='dashboard-col header'>Data/Tipo</div>", unsafe_allow_html=True)
            header_cols[2].markdown("<div class='dashboard-col header'>Referência/Liturgia</div>", unsafe_allow_html=True)
            header_cols[3].markdown("<div class='dashboard-col header'>Ações</div>", unsafe_allow_html=True)
            header_cols[4].markdown("<div class='dashboard-col header progress-bar-container'>Progresso</div>", unsafe_allow_html=True)
            
            # Ícones de Status
            for i, (key, icon) in enumerate(status_icons.items()):
                header_cols[5 + i].caption(icon)

            st.markdown("---") # Separador para o cabeçalho

            for leitura in leituras:
                data_str = leitura['data']
                tipo = leitura['tipo']
                chave = f"{data_str}-{tipo}"
                
                progresso, em_producao = get_leitura_status(data_str, tipo)
                
                # Oculta leituras publicadas que não estão mais marcadas como "em produção"
                if progresso.get('publicacao', False) and em_producao == 0:
                    continue

                # Colunas da Linha
                cols = st.columns(col_weights)
                
                # Checkbox 'Em Produção' (Col 0)
                with cols[0]:
                    # st.checkbox retorna True/False e o valor é usado para chamar a função de persistência
                    if cols[0].checkbox("", value=em_producao, key=f"prod_{chave}") != (em_producao == 1):
                        set_leitura_em_producao(data_str, tipo, not em_producao)
                        st.rerun() # Recarrega para refletir a mudança no dashboard e no dropdown
                
                # Data e Tipo (Col 1)
                with cols[1]:
                    st.markdown(f"**{data_str}**")
                    st.caption(tipo)
                
                # Referência e Liturgia (Col 2)
                with cols[2]:
                    st.markdown(leitura['ref'])
                    st.caption(f"({leitura['liturgia']})")
                    
                # Ações - Selecionar (Col 3)
                with cols[3]:
                    if cols[3].button("▶️ Selecionar", key=f"sel_{chave}", use_container_width=True, help="Carrega esta leitura nas páginas de produção"):
                        selecionar_leitura(leitura['leitura_completa'], data_str, leitura['cor'])
                        
                # Progresso geral (Visual) (Col 4)
                with cols[4]:
                    steps_done = sum(progresso.values())
                    total_steps = len(progresso)
                    progress_val = steps_done / total_steps
                    # Ajusta a cor para indicar 100% ou progresso
                    progress_color = 'green' if steps_done == total_steps else 'blue'
                    st.progress(progress_val)
                    st.caption(f"{steps_done}/{total_steps}")

                # Status de Etapa (Cols 5-11)
                for i, (key, icon) in enumerate(status_icons.items()):
                    with cols[5 + i]:
                        if progresso.get(key, False):
                            st.markdown("✅")
                        else:
                            st.markdown("➖")
                
                # Botão Excluir (Col 12)
                with cols[-1]:
                    if cols[-1].button("🗑️", key=f"del_{chave}", help="Apagar TODO o progresso e estado desta leitura"):
                        apagar_progresso_leitura(data_str, tipo)
                        st.rerun()


# --- Execução Principal ---
init_db()

st.title("🎛️ Dashboard de Produção – Memória Persistente")
st.markdown("Use esta tela para carregar as leituras, marcar o que está **Em Produção** e monitorar o progresso.")

start_date, end_date = get_date_range_for_months()

if st.button(f"🔎 Carregar Leituras: {start_date.strftime('%d/%b')} até {end_date.strftime('%d/%b')}", type="primary", use_container_width=True):
    # Busca os dados, popula o cache e o st.session_state
    data_range = get_liturgia_data_range(start_date, end_date)
    st.session_state['dashboard_data'] = data_range
    # Atualiza o estado das leituras em produção (persistente) para o dropdown de navegação
    st.session_state['leituras_em_producao'] = load_producao_status()
    st.success("Leituras carregadas com sucesso! Role para baixo para ver a tabela.")
    
# --- Renderiza a Dashboard se os dados estiverem na sessão ---
if 'dashboard_data' in st.session_state and st.session_state['dashboard_data']:
    st.divider()
    st.subheader(f"Leituras Encontradas ({len(st.session_state['dashboard_data'])}):")
    st.caption("A tabela exibe leituras marcadas 'Em Produção' ou com algum progresso. Clique em 'Selecionar' para ir à primeira etapa de trabalho.")
    create_dashboard_table(st.session_state['dashboard_data'])
elif 'dashboard_data' in st.session_state and not st.session_state['dashboard_data']:
    st.warning("Nenhuma leitura encontrada para o período solicitado.")
    
# --- Inicializa Leituras Ativas na Sessão (para uso nas outras páginas) ---
if 'leituras_em_producao' not in st.session_state:
     # Carrega ao iniciar, mesmo que o botão da dashboard não tenha sido clicado
     st.session_state['leituras_em_producao'] = load_producao_status()

st.markdown("---")
st.caption(f"Dados da liturgia fornecidos por API externa. Última atualização de status: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
