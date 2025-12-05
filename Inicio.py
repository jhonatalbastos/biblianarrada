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
DB_FILE = 'liturgia_db.sqlite'

# --- Funções de Banco de Dados ---
def get_db_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabela 1: Cache da Liturgia
    c.execute('''CREATE TABLE IF NOT EXISTS historico 
                 (data_liturgia TEXT PRIMARY KEY, santo TEXT, cor TEXT, json_completo TEXT, data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Tabela 2: Estado de Produção
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
    conn = get_db_connection()
    c = conn.cursor()
    json_str = json.dumps(dados, ensure_ascii=False)
    c.execute('INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo) VALUES (?, ?, ?, ?)', 
              (dados['data'], dados['liturgia'], dados['cor'], json_str))
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    if res:
        return json.loads(res[0])
    return None

def update_producao_status(chave, data_liturgia, tipo_leitura, progresso_dict, em_producao):
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
        # Carrega todas as leituras ativas ou em progresso
        c.execute('SELECT chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao FROM producao_status WHERE em_producao = 1 OR progresso != \'{"roteiro": false, "imagens": false, "audio": false, "overlay": false, "legendas": false, "video": false, "publicacao": false}\'')
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

# --- Funções de Lógica ---

def buscar_liturgia_api(data_obj):
    # (MANTÉM A FUNÇÃO ORIGINAL DE BUSCA NA API)
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

def get_leitura_status(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default_progresso = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    
    progresso_json, em_producao = load_producao_status(chave)
    
    if progresso_json:
        # Garante que todas as chaves existam
        progresso = default_progresso.copy()
        progresso.update(progresso_json)
        return progresso, em_producao
    
    return default_progresso, 0

def set_leitura_em_producao(data_str, tipo_leitura, em_producao):
    chave = f"{data_str}-{tipo_leitura}"
    
    # Carrega estado atual ou default
    progresso, _ = get_leitura_status(data_str, tipo_leitura)
    
    update_producao_status(chave, data_str, tipo_leitura, progresso, em_producao)
    st.toast(f"Status de produção de {tipo_leitura} em {data_str} alterado para {'Ativo' if em_producao else 'Inativo'}.")
    # Atualiza o cache da sessão
    st.session_state['leituras_em_producao'] = load_producao_status()

def selecionar_leitura(leitura_data, data_str, cor_liturgica="N/A"):
    """Define qual leitura está sendo trabalhada e inicializa o progresso no st.session_state."""
    lectura_data = leitura_data.copy()
    lectura_data['cor_liturgica'] = cor_liturgica
    
    st.session_state['leitura_atual'] = lectura_data
    st.session_state['data_atual_str'] = data_str
    
    # Carrega progresso persistente para a sessão
    chave = f"{data_str}-{leitura_data['tipo']}"
    progresso, em_producao = get_leitura_status(data_str, leitura_data['tipo'])
    st.session_state['progresso_leitura_atual'] = progresso
    
    # Redireciona para a primeira página não concluída
    if progresso['roteiro'] == False:
        st.switch_page("pages/1_Roteiro_Viral.py")
    elif progresso['imagens'] == False and progresso['audio'] == False:
        st.switch_page("pages/1_Roteiro_Viral.py") # Força roteiro de novo se nada foi feito
    elif progresso['overlay'] == False:
        st.switch_page("pages/4_Overlay.py")
    else:
        st.switch_page("pages/6_Video_Final.py")
    

def apagar_progresso_leitura(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM producao_status WHERE chave_leitura = ?', (chave,))
    conn.commit()
    conn.close()
    
    # Limpa estado da sessão
    if 'leitura_atual' in st.session_state and f"{st.session_state['data_atual_str']}-{st.session_state['leitura_atual']['tipo']}" == chave:
        del st.session_state['leitura_atual']
        if 'progresso_leitura_atual' in st.session_state:
            del st.session_state['progresso_leitura_atual']
    
    st.toast(f"✅ Progresso de {tipo_leitura} em {data_str} apagado.")
    # Recarrega a dashboard
    st.session_state['leituras_em_producao'] = load_producao_status()


# --- Funções de Interface da Dashboard ---

def get_liturgia_data_range(start_date, end_date):
    """Busca e armazena os dados da liturgia para um range de datas."""
    delta = end_date - start_date
    all_data = []
    
    for i in range(delta.days + 1):
        date_obj = start_date + timedelta(days=i)
        data_str = date_obj.strftime("%d/%m/%Y")
        
        dados_dia = carregar_do_banco(data_str)
        if not dados_dia:
            # Buscar na API e Salvar no banco (simulação de fundo)
            dados_api, err = buscar_liturgia_api(date_obj)
            if dados_api:
                salvar_no_banco(dados_api)
                dados_dia = dados_api
            else:
                continue # Ignora dias com erro na API
        
        if dados_dia and 'leituras' in dados_dia:
            for leitura in dados_dia['leituras']:
                if leitura.get('texto'):
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

def get_date_range_for_months():
    today = datetime.date.today()
    
    # Mês Atual
    start_current = today.replace(day=1)
    end_current = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    # Mês Seguinte
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    end_next = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])

    return start_current, end_next

def create_dashboard_table(data_list):
    # Agrupa por semana para o expander
    leituras_por_semana = {}
    
    for item in data_list:
        week_num = item['data_obj'].isocalendar()[1]
        
        # Cria um rótulo de semana no formato (01/Jan - 07/Jan)
        # O rótulo deve ser estável, então usamos a data da segunda-feira
        start_of_week = item['data_obj'] - timedelta(days=item['data_obj'].weekday())
        week_label = f"📅 Semana de {start_of_week.strftime('%d/%b')}"
        
        if week_label not in leituras_por_semana:
            leituras_por_semana[week_label] = []
            
        leituras_por_semana[week_label].append(item)
        
    # Colunas de Status
    status_icons = {
        'roteiro': '📝', 'imagens': '🎨', 'audio': '🔊', 
        'overlay': '🖼️', 'legendas': '💬', 'video': '🎬', 'publicacao': '🚀'
    }
    
    # Determina a semana atual
    today = datetime.date.today()
    current_week_num = today.isocalendar()[1]
    
    # Renderiza as semanas
    for week_label, leituras in leituras_por_semana.items():
        is_current_week = leituras[0]['data_obj'].isocalendar()[1] == current_week_num
        
        # Expande a semana atual por padrão
        with st.expander(week_label, expanded=is_current_week):
            
            # Tabela de Leituras
            cols = st.columns([0.5, 1.5, 1.5, 1, 1] + [0.3] * 7 + [0.5])
            
            # Cabeçalho
            cols[0].markdown("**Prod.**") # Checkbox de Produção
            cols[1].markdown("**Data/Tipo**")
            cols[2].markdown("**Referência/Liturgia**")
            cols[3].markdown("**Ações**")
            cols[4].markdown("**Progresso**")
            
            # Ícones de Status
            for i, (key, icon) in enumerate(status_icons.items()):
                cols[5 + i].caption(icon)

            st.markdown("---") # Separador para o cabeçalho

            for leitura in leituras:
                data_str = leitura['data']
                tipo = leitura['tipo']
                chave = f"{data_str}-{tipo}"
                
                progresso, em_producao = get_leitura_status(data_str, tipo)
                
                # Exclui leituras que foram publicadas E não estão em produção ativa
                if progresso['publicacao'] and em_producao == 0:
                    continue

                c = st.columns([0.5, 1.5, 1.5, 1, 1] + [0.3] * 7 + [0.5])
                
                # Checkbox 'Em Produção'
                with c[0]:
                    if c[0].checkbox("", value=em_producao, key=f"prod_{chave}"):
                        set_leitura_em_producao(data_str, tipo, True)
                    else:
                        set_leitura_em_producao(data_str, tipo, False)
                
                # Data e Tipo
                with c[1]:
                    st.markdown(f"**{data_str}**")
                    st.caption(tipo)
                
                # Referência e Liturgia
                with c[2]:
                    st.markdown(leitura['ref'])
                    st.caption(f"({leitura['liturgia']})")
                    
                # Ações
                with c[3]:
                    if c[3].button("▶️ Selecionar", key=f"sel_{chave}"):
                        selecionar_leitura(leitura['leitura_completa'], data_str, leitura['cor'])
                        
                # Progresso geral (Visual)
                with c[4]:
                    steps_done = sum(progresso.values())
                    total_steps = len(progresso)
                    progress_val = steps_done / total_steps
                    st.progress(progress_val)

                # Status de Etapa
                for i, (key, icon) in enumerate(status_icons.items()):
                    with c[5 + i]:
                        if progresso[key]:
                            st.markdown("✅")
                        else:
                            st.markdown("➖")
                
                # Botão Excluir
                with c[-1]:
                    if c[-1].button("🗑️", key=f"del_{chave}", help="Apagar todo o progresso desta leitura"):
                        apagar_progresso_leitura(data_str, tipo)
                        st.rerun()

# --- Execução Principal ---
init_db()

st.title("🎛️ Dashboard de Produção - Memória Persistente")

start_date, end_date = get_date_range_for_months()

if st.button(f"🔎 Carregar Leituras do Mês Atual ({start_date.strftime('%b')}) e Próximo ({end_date.strftime('%b')})", type="primary"):
    with st.spinner(f"Buscando e populando cache da liturgia de {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}..."):
        data_range = get_liturgia_data_range(start_date, end_date)
        st.session_state['dashboard_data'] = data_range
        # Atualiza o estado das leituras em produção (persistente)
        st.session_state['leituras_em_producao'] = load_producao_status()
        
if 'dashboard_data' in st.session_state:
    st.divider()
    st.subheader(f"Leituras Disponíveis: {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    create_dashboard_table(st.session_state['dashboard_data'])

else:
    st.info("Clique no botão acima para carregar as leituras dos próximos 60 dias e iniciar a produção persistente.")

# --- Inicializa Leituras Ativas na Sessão (para o menu dropdown nas outras páginas) ---
if 'leituras_em_producao' not in st.session_state:
     st.session_state['leituras_em_producao'] = load_producao_status()
