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
    """Cria o banco de dados local se não existir."""
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
    """Salva o retorno da API no banco local."""
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    # Serializa o dicionário inteiro para JSON para salvar no banco
    json_str = json.dumps(dados, ensure_ascii=False)
    
    c.execute('''
        INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo)
        VALUES (?, ?, ?, ?)
    ''', (dados['data'], dados['liturgia'], dados['cor'], json_str))
    conn.commit()
    conn.close()

def carregar_do_banco(data_str):
    """Tenta recuperar dados salvos anteriormente."""
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    resultado = c.fetchone()
    conn.close()
    if resultado:
        return json.loads(resultado[0])
    return None

def listar_historico():
    """Lista as últimas pesquisas para o menu lateral."""
    conn = sqlite3.connect('liturgia_db.sqlite')
    c = conn.cursor()
    c.execute('SELECT data_liturgia, santo FROM historico ORDER BY data_acesso DESC LIMIT 10')
    items = c.fetchall()
    conn.close()
    return items

# Inicializa o DB ao abrir a página
init_db()

# --- Função de Consumo da API ---
def buscar_liturgia_api(data_obj):
    """
    Consome a API pública de Liturgia Diária.
    URL Base utilizada: liturgia.up.railway.app (fork estável do projeto vercel)
    """
    dia = data_obj.day
    mes = data_obj.month
    ano = data_obj.year
    
    # Endpoint padrão da comunidade open-source
    url = f"https://liturgia.up.railway.app/{dia}-{mes}-{ano}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 404:
            return None, "Liturgia não encontrada. Motivo provável: A data é muito futura e a CNBB ainda não disponibilizou os textos."
        
        if response.status_code != 200:
            return None, f"Erro na API (Status: {response.status_code})"

        # A API retorna exatamente o JSON que você descreveu
        dados_json = response.json()
        
        # Tratamento de dados para garantir que campos opcionais não quebrem o app
        resultado_processado = {
            "data": dados_json.get("data", f"{dia:02d}/{mes:02d}/{ano}"),
            "liturgia": dados_json.get("liturgia", "Liturgia Diária"),
            "cor": dados_json.get("cor", "Não informada"),
            "primeira_leitura": dados_json.get("primeiraLeitura", {}).get("texto", ""),
            "primeira_leitura_ref": dados_json.get("primeiraLeitura", {}).get("referencia", ""),
            "salmo": dados_json.get("salmo", {}).get("texto", ""),
            "salmo_ref": dados_json.get("salmo", {}).get("referencia", ""),
            "segunda_leitura": dados_json.get("segundaLeitura", {}).get("texto", "Não há segunda leitura hoje."), # Opcional
            "evangelho": dados_json.get("evangelho", {}).get("texto", ""),
            "evangelho_ref": dados_json.get("evangelho", {}).get("referencia", ""),
            "santo": dados_json.get("liturgia", "Liturgia Diária") # Alias para compatibilidade
        }

        return resultado_processado, None

    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

# --- Interface do Usuário (Streamlit) ---
st.title("🙏 Liturgia Diária (Via API)")
st.markdown("Busca estruturada de dados litúrgicos para geração de roteiros.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📅 Configuração")
    # Input de Data
    data_selecionada = st.date_input("Escolha a Data", datetime.date.today())
    
    # Formatação da data para chave do banco (DD/MM/YYYY)
    data_chave = data_selecionada.strftime("%d/%m/%Y")
    
    # Botão Principal
    if st.button("🔍 Buscar Liturgia", use_container_width=True, type="primary"):
        with st.spinner("Conectando à API de Liturgia..."):
            
            # 1. Verifica Cache Local (Banco de Dados)
            dados_db = carregar_do_banco(data_chave)
            
            if dados_db:
                st.session_state['dados_liturgia'] = dados_db
                st.success("✅ Dados carregados do banco local!")
            else:
                # 2. Busca na API Online
                dados_api, erro = buscar_liturgia_api(data_selecionada)
                
                if dados_api:
                    salvar_no_banco(dados_api)
                    st.session_state['dados_liturgia'] = dados_api
                    st.success("✅ Liturgia obtida da API com sucesso!")
                else:
                    st.error(f"❌ {erro}")
                    st.warning("Nota: Se você escolheu uma data muito distante (ex: final de 2025), a fonte oficial pode ainda não ter liberado os textos.")

    st.divider()
    
    # Histórico Lateral
    st.subheader("📂 Histórico Salvo")
    historico = listar_historico()
    if historico:
        for data_h, titulo_h in historico:
            if st.button(f"🔄 {data_h}", key=data_h, help=titulo_h):
                dados_rec = carregar_do_banco(data_h)
                st.session_state['dados_liturgia'] = dados_rec
                st.rerun()
    else:
        st.caption("Nenhuma pesquisa salva.")

with col2:
    if 'dados_liturgia' in st.session_state:
        d = st.session_state['dados_liturgia']
        
        # Cabeçalho da Visualização
        st.markdown(f"### {d['liturgia']}")
        st.caption(f"📅 **Data:** {d['data']} | 🎨 **Cor:** {d['cor']}")
        
        # Abas para organizar o conteúdo
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Evangelho", "📜 1ª Leitura", "🎶 Salmo", "⛪ 2ª Leitura"])
        
        with tab1:
            st.markdown(f"**Referência:** *{d['evangelho_ref']}*")
            st.info(d['evangelho'])
        
        with tab2:
            st.markdown(f"**Referência:** *{d['primeira_leitura_ref']}*")
            st.write(d['primeira_leitura'])
            
        with tab3:
            st.markdown(f"**Referência:** *{d['salmo_ref']}*")
            st.write(d['salmo'])
            
        with tab4:
            if "Não há" in d['segunda_leitura']:
                st.caption(d['segunda_leitura'])
            else:
                st.write(d['segunda_leitura'])
        
        st.divider()
        
        # Botão de Ação
        st.success("Dados estruturados prontos para o roteiro.")
        if st.button("✨ Gerar Roteiro Viral ➡️", use_container_width=True):
            st.switch_page("pages/1_Roteiro_Viral.py")
            
    else:
        # Estado Inicial
        st.info("👈 Selecione uma data e clique em 'Buscar Liturgia'.")
        st.markdown("""
        **Como funciona esta versão:**
        1. O sistema consulta uma **API JSON** especializada.
        2. Obtém textos separados (Evangelho, Salmo, Leitura).
        3. Salva tudo no seu banco de dados local.
        4. Envia os dados limpos para o gerador de roteiro.
        """)
