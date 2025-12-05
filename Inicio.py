import streamlit as st
import requests
import sqlite3
import json
import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Início - Bíblia Narrada",
    page_icon="🙏",
    layout="wide"
)

# --- Configuração do Banco de Dados (SQLite) ---
def init_db():
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            data_liturgia TEXT PRIMARY KEY,
            santo TEXT,
            cor TEXT,
            json_completo TEXT,
            data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def salvar_no_banco(dados):
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    json_str = json.dumps(dados, ensure_ascii=False)
    c.execute('''
        INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo)
        VALUES (?, ?, ?, ?)
    ''', (dados['data'], dados['liturgia'], dados['cor'], json_str))
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    resultado = c.fetchone()
    conn.close()
    if resultado:
        return json.loads(resultado[0])
    return None

def listar_historico():
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('SELECT data_liturgia, santo FROM historico ORDER BY data_acesso DESC LIMIT 10')
    items = c.fetchall()
    conn.close()
    return items

# Inicializa DB
init_db()

# --- Função Auxiliar de Extração Segura ---
def safe_extract(source_dict, main_key, sub_key="texto"):
    """
    Tenta extrair dados de forma segura, seja string direta ou dicionário aninhado.
    Evita o erro 'str object has no attribute get'.
    """
    val = source_dict.get(main_key)
    
    if val is None:
        return ""
    
    # Se o valor já for o texto (string), retorna ele
    if isinstance(val, str):
        # Se pedirmos 'referencia' mas o valor é só texto, retornamos vazio
        if sub_key == "referencia": 
            return "" 
        return val
        
    # Se for dicionário, acessa a subchave
    if isinstance(val, dict):
        return val.get(sub_key, "")
        
    return str(val)

# --- Função de Consumo da API ---
def buscar_liturgia_api(data_obj):
    dia = data_obj.day
    mes = data_obj.month
    ano = data_obj.year
    
    # URL da API
    url = f"https://liturgia.up.railway.app/{dia}-{mes}-{ano}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 404:
            return None, "Liturgia não encontrada (404). Data futura ou indisponível."
        
        if response.status_code != 200:
            return None, f"Erro na API (Status: {response.status_code})"

        dados_json = response.json()
        
        # --- Extração Robusta dos Dados ---
        # Usa a função safe_extract para garantir que não quebre se vier string
        
        resultado_processado = {
            "data": dados_json.get("data", f"{dia:02d}/{mes:02d}/{ano}"),
            "liturgia": dados_json.get("liturgia", "Liturgia Diária"),
            "cor": dados_json.get("cor", "Não informada"),
            
            # Extração de Textos
            "primeira_leitura": safe_extract(dados_json, "primeiraLeitura", "texto"),
            "salmo": safe_extract(dados_json, "salmo", "texto"),
            "segunda_leitura": safe_extract(dados_json, "segundaLeitura", "texto"),
            "evangelho": safe_extract(dados_json, "evangelho", "texto"),
            
            # Extração de Referências
            "primeira_leitura_ref": safe_extract(dados_json, "primeiraLeitura", "referencia"),
            "salmo_ref": safe_extract(dados_json, "salmo", "referencia"),
            "evangelho_ref": safe_extract(dados_json, "evangelho", "referencia"),
            
            # Alias para compatibilidade
            "santo": dados_json.get("liturgia", "Liturgia do Dia")
        }

        # Validação mínima: se não tiver evangelho, algo deu errado
        if not resultado_processado["evangelho"]:
             return None, "API retornou dados incompletos (sem Evangelho)."

        return resultado_processado, None

    except Exception as e:
        return None, f"Erro técnico ao processar dados: {str(e)}"

# --- Interface do Usuário ---
st.title("🙏 Liturgia Diária (Via API)")
st.markdown("Busca estruturada de dados litúrgicos.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📅 Configuração")
    data_selecionada = st.date_input("Escolha a Data", datetime.date.today())
    data_chave = data_selecionada.strftime("%d/%m/%Y")
    
    if st.button("🔍 Buscar Liturgia", use_container_width=True, type="primary"):
        with st.spinner("Conectando à API..."):
            
            dados_db = carregar_do_banco(data_chave)
            
            if dados_db:
                st.session_state['dados_liturgia'] = dados_db
                st.success("✅ Carregado do banco local!")
            else:
                dados_api, erro = buscar_liturgia_api(data_selecionada)
                
                if dados_api:
                    salvar_no_banco(dados_api)
                    st.session_state['dados_liturgia'] = dados_api
                    st.success("✅ Sucesso!")
                else:
                    st.error(f"❌ {erro}")

    st.divider()
    st.subheader("📂 Histórico")
    historico = listar_historico()
    if historico:
        for data_h, titulo_h in historico:
            if st.button(f"🔄 {data_h}", key=data_h):
                dados_rec = carregar_do_banco(data_h)
                st.session_state['dados_liturgia'] = dados_rec
                st.rerun()

with col2:
    if 'dados_liturgia' in st.session_state:
        d = st.session_state['dados_liturgia']
        
        st.markdown(f"### {d['liturgia']}")
        st.caption(f"📅 **Data:** {d['data']} | 🎨 **Cor:** {d['cor']}")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Evangelho", "📜 1ª Leitura", "🎶 Salmo", "⛪ 2ª Leitura"])
        
        with tab1:
            if d['evangelho_ref']: st.markdown(f"**Ref:** *{d['evangelho_ref']}*")
            st.info(d['evangelho'])
        
        with tab2:
            if d['primeira_leitura_ref']: st.markdown(f"**Ref:** *{d['primeira_leitura_ref']}*")
            st.write(d['primeira_leitura'])
            
        with tab3:
            if d['salmo_ref']: st.markdown(f"**Ref:** *{d['salmo_ref']}*")
            st.write(d['salmo'])
            
        with tab4:
            if not d['segunda_leitura']:
                st.caption("Não há segunda leitura hoje.")
            else:
                st.write(d['segunda_leitura'])
        
        st.divider()
        if st.button("✨ Gerar Roteiro Viral ➡️", use_container_width=True):
            st.switch_page("pages/1_Roteiro_Viral.py")
            
    else:
        st.info("👈 Selecione uma data para começar.")
