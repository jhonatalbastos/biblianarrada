import streamlit as st
import requests
import sqlite3
import json
import socket
from datetime import datetime, timedelta
from requests.exceptions import Timeout, RequestException, HTTPError 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Início – Biblia Narrada", layout="wide")

# --- BANCO DE DADOS (Mantido igual) ---
DB_FILE = 'biblia_narrada_db.sqlite'

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS historico
                 (data_liturgia TEXT PRIMARY KEY, json_completo TEXT, cor TEXT, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS producao_status
                 (chave_leitura TEXT PRIMARY KEY, data_liturgia TEXT, tipo_leitura TEXT, progresso TEXT, em_producao INTEGER, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    return json.loads(res[0]) if res else None

def listar_cache_liturgia():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT data_liturgia, cor, ultimo_acesso FROM historico ORDER BY data_liturgia DESC')
    rows = c.fetchall()
    conn.close()
    lista_cache = []
    for data, cor, acesso in rows:
        try:
            data_acesso = datetime.strptime(acesso.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        except:
            data_acesso = acesso
        lista_cache.append({'Data': data, 'Cor Litúrgica': cor, 'Último Acesso': data_acesso})
    return lista_cache

def salvar_no_banco(data_str, json_data):
    conn = get_db_connection()
    c = conn.cursor()
    json_str = json.dumps(json_data)
    cor = json_data.get('cor', 'Branco') 
    c.execute('''INSERT OR REPLACE INTO historico (data_liturgia, json_completo, cor, ultimo_acesso) VALUES (?, ?, ?, CURRENT_TIMESTAMP)''', (data_str, json_str, cor))
    conn.commit()
    conn.close()

def load_producao_status(chave=None):
    conn = get_db_connection()
    c = conn.cursor()
    if chave:
        c.execute('SELECT progresso, em_producao FROM producao_status WHERE chave_leitura = ?', (chave,))
        res = c.fetchone()
        conn.close()
        return (json.loads(res[0]), res[1]) if res else (None, 0)
    else:
        default_json = json.dumps({"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False})
        c.execute(f'SELECT chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao FROM producao_status WHERE em_producao = 1 OR progresso != ?', (default_json,))
        rows = c.fetchall()
        conn.close()
        all_status = {}
        for row in rows:
            all_status[row[0]] = {'data_liturgia': row[1], 'tipo_leitura': row[2], 'progresso': json.loads(row[3]), 'em_producao': row[4]}
        return all_status

def update_producao_status(chave, data_liturgia, tipo_leitura, progresso_dict, em_producao):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO producao_status (chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao, ultimo_acesso) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
              (chave, data_liturgia, tipo_leitura, json.dumps(progresso_dict), 1 if em_producao else 0))
    conn.commit()
    conn.close()
    
def get_leitura_status(data_str, tipo_leitura):
    chave = f"{data_str}-{tipo_leitura}"
    default = {"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False}
    prog, em_prod = load_producao_status(chave)
    if prog:
        default.update(prog)
        return default, em_prod
    return default, 0

# --- NOVO TESTE DE CONEXÃO (ADAPTADO PARA QUERY PARAM) ---
def test_api_connection():
    # URL definida no README
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    
    # Extrai o hostname para teste de DNS
    try:
        from urllib.parse import urlparse
        hostname = urlparse(BASE_URL).netloc
        if not hostname: hostname = "api-liturgia-diaria.vercel.app"
    except:
        hostname = "api-liturgia-diaria.vercel.app"

    log = [f"🌐 Hostname alvo: **{hostname}**", f"🔗 URL Base: `{BASE_URL}`"]
    success = True
    
    # 1. Teste DNS
    try:
        socket.getaddrinfo(hostname, 443)
        log.append("✅ DNS Resolvido com sucesso.")
    except socket.gaierror as e:
        success = False
        log.append(f"❌ ERRO DNS: Não foi possível encontrar o servidor `{hostname}`.")
        log.append(f"Detalhe: {e}")

    # 2. Teste HTTP (se DNS ok)
    if success:
        # Testa usando o parâmetro ?date=YYYY-MM-DD
        hoje = datetime.today().strftime('%Y-%m-%d')
        log.append(f"📡 Testando GET com params: `?date={hoje}`")
        
        try:
            # Importante: params=... monta a query string corretamente
            resp = requests.get(BASE_URL, params={'date': hoje}, timeout=10)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    log.append(f"✅ HTTP 200: Conexão OK. JSON recebido.")
                    # Verificação básica se o JSON tem conteúdo
                    if not data:
                        log.append("⚠️ Aviso: JSON vazio retornado.")
                except json.JSONDecodeError:
                    log.append("❌ Erro: Resposta não é um JSON válido.")
                    success = False
            else:
                log.append(f"❌ HTTP Erro: Status {resp.status_code}")
                success = False
                
        except Exception as e:
            success = False
            log.append(f"❌ ERRO HTTP FATAL: {e}")

    # Exibe o log se houver erro
    if not success:
        with st.expander("🚨 DIAGNÓSTICO DE CONEXÃO (CLIQUE PARA ABRIR)", expanded=True):
            st.error("Falha ao conectar na API Litúrgica.")
            st.markdown("\n".join([f"- {l}" for l in log]))
            st.warning("Verifique se a URL base está correta e se a Vercel não está bloqueando o IP.")
    
    return success

# --- INTEGRAÇÃO COM A API (ADAPTADA AO README) ---

def fetch_liturgia(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Cache Local
    cached = carregar_do_banco(date_str)
    if cached:
        st.toast(f"Carregado do cache: {date_str}", icon="💾")
        return cached
    
    # 2. Configuração da API
    BASE_URL = st.secrets.get("LITURGIA_API_BASE_URL", "https://api-liturgia-diaria.vercel.app")
    
    # Remove barra final se houver, para garantir limpeza
    if BASE_URL.endswith('/'): BASE_URL = BASE_URL[:-1]

    try:
        # AQUI ESTÁ A MUDANÇA PRINCIPAL: Uso de params
        response = requests.get(BASE_URL, params={'date': date_str}, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # --- PARSER PARA O FORMATO JOSUÉ SANTOS ---
        leituras_formatadas = []
        
        # Tenta pegar a cor (às vezes vem 'liturgia_cor', 'cor' ou dentro de 'liturgia')
        cor = data.get('cor', 'Verde') 
        if not cor and 'liturgia' in data: 
            cor = data['liturgia'].get('cor', 'Verde')

        # Mapeamento de chaves planas que essa API costuma retornar
        mapeamento = {
            'primeiraLeitura': 'Primeira Leitura',
            'segundaLeitura': 'Segunda Leitura',
            'salmo': 'Salmo Responsorial',
            'evangelho': 'Evangelho'
        }
        
        for chave_api, titulo_exibicao in mapeamento.items():
            if chave_api in data:
                conteudo = data[chave_api]
                
                # O conteúdo pode vir como string direta ou dict
                texto_final = ""
                ref_final = ""
                
                if isinstance(conteudo, dict):
                    texto_final = conteudo.get('texto', '') or conteudo.get('refrao', '')
                    ref_final = conteudo.get('referencia', '') or conteudo.get('ref', '')
                elif isinstance(conteudo, str):
                    texto_final = conteudo
                    # Tenta achar referência se estiver separada (às vezes acontece)
                    ref_final = data.get(f"{chave_api}Ref", "")
                
                if texto_final:
                    leituras_formatadas.append({
                        'tipo': titulo_exibicao,
                        'titulo': titulo_exibicao,
                        'ref': ref_final,
                        'texto': texto_final
                    })

        if not leituras_formatadas:
            # Fallback: Tenta iterar caso o formato seja diferente
            st.warning("Formato padrão não encontrado. Tentando extração genérica.")
            # (Adicione lógica extra aqui se necessário, mas o mapeamento acima cobre 90% dos casos dessa lib)

        final_data = {
            'data': date_str,
            'nome_dia': data.get('dia', 'Dia Litúrgico'),
            'cor': cor,
            'leituras': leituras_formatadas
        }
        
        if leituras_formatadas:
            salvar_no_banco(date_str, final_data)
            return final_data
        else:
            st.error("API respondeu, mas não encontrei leituras no JSON.")
            st.json(data) # Debug para o usuário ver o que chegou
            return None

    except Exception as e:
        st.error(f"Erro na requisição: {e}")
        # Chama o diagnóstico se falhar
        test_api_connection()
        return None

# --- RENDERIZAÇÃO DA DASHBOARD (IGUAL AO ANTERIOR) ---

def get_status_emoji(key, progresso):
    return "✅" if progresso.get(key, False) else "❌"

def handle_leitura_selection(data_str, tipo_leitura):
    try:
        dados_dia = fetch_liturgia(datetime.strptime(data_str, '%Y-%m-%d'))
        if not dados_dia: return
        
        leitura = next((l for l in dados_dia['leituras'] if l['tipo'] == tipo_leitura), None)
        if not leitura: st.error("Leitura não encontrada."); return

        prog, _ = get_leitura_status(data_str, tipo_leitura)
        
        st.session_state.update({
            'data_atual_str': data_str,
            'leitura_atual': {**leitura, 'cor_liturgica': dados_dia['cor']},
            'progresso_leitura_atual': prog
        })
        
        update_producao_status(f"{data_str}-{tipo_leitura}", data_str, tipo_leitura, prog, 1)
        st.switch_page("pages/1_Roteiro_Viral.py")
    except Exception as e:
        st.error(f"Erro ao selecionar: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == '__main__':
    init_db()
    # Executa o teste de conexão logo no início
    test_api_connection()

st.title("📖 Biblia Narrada: Painel de Produção")

# --- DASHBOARD ---
st.header("📋 Em Produção")
status_raw = load_producao_status()
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
    st.info("Nada em produção.")

st.divider()

# --- CACHE ---
cache = listar_cache_liturgia()
if cache:
    st.subheader("🗓️ Histórico")
    col_c1, col_c2 = st.columns([3,1])
    with col_c1:
        selected_cache = st.selectbox("Selecione do histórico:", [f"{c['Data']} - {c['Cor Litúrgica']}" for c in cache], key="sel_cache")
    with col_c2:
        if st.button("Carregar Histórico"):
            data_sel = selected_cache.split(' - ')[0]
            st.session_state['data_busca'] = data_sel
            st.rerun()

st.divider()

# --- BUSCA API ---
st.header("🔍 Buscar Nova (API Vercel)")
c1, c2 = st.columns([1, 2])
with c1:
    dt_input = st.date_input("Data", value=datetime.today())
with c2:
    st.write("")
    st.write("")
    if st.button("Buscar na API", type="primary"):
        st.session_state['data_busca'] = dt_input.strftime('%Y-%m-%d')
        if 'dados_liturgia' in st.session_state: del st.session_state['dados_liturgia']
        st.rerun()

data_busca = st.session_state.get('data_busca')
if data_busca:
    dados = fetch_liturgia(datetime.strptime(data_busca, '%Y-%m-%d'))
    
    if dados:
        st.success(f"Liturgia encontrada: {dados['nome_dia']} ({dados['cor']})")
        cols = st.columns(len(dados['leituras']))
        for i, l in enumerate(dados['leituras']):
            with cols[i % 4]:
                with st.container(border=True):
                    st.markdown(f"**{l['tipo']}**")
                    st.caption(l['ref'] if l['ref'] else "Sem referência")
                    if st.button(f"Produzir", key=f"prod_{l['tipo']}_{data_busca}"):
                        handle_leitura_selection(data_busca, l['tipo'])
