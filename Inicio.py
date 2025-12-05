import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import sqlite3
import json

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
    c.execute('''
        INSERT OR REPLACE INTO historico (data_liturgia, santo, cor, json_completo)
        VALUES (?, ?, ?, ?)
    ''', (dados['data'], dados['santo'], dados['cor'], json.dumps(dados)))
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
    c.execute('SELECT data_liturgia, santo FROM historico ORDER BY data_liturgia DESC LIMIT 10')
    items = c.fetchall()
    conn.close()
    return items

# Inicializa o DB
init_db()

# --- Função de Scraping Robusta ---
def get_liturgia_cancaonova(data_obj):
    # Mapeamento estrito para o padrão de URL da Canção Nova (sem acentos)
    meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'marco', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    
    # Formatação: Dia sem zero à esquerda (int), Mês por extenso, Ano de 4 dígitos
    dia = int(data_obj.day) 
    mes_nome = meses[data_obj.month]
    ano = data_obj.year
    
    # URL Padrão: https://liturgia.cancaonova.com/pb/liturgia/d/5-dezembro-2023/
    url = f"https://liturgia.cancaonova.com/pb/liturgia/d/{dia}-{mes_nome}-{ano}/"
    
    # Headers para simular um navegador real (evita bloqueios 403/404 falsos)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Se der erro 404, verifica se é uma data muito distante
        if response.status_code == 404:
            return None, f"Liturgia não encontrada (404). O site ainda não disponibilizou esta data ou a URL mudou. URL tentada: {url}"
        
        if response.status_code != 200:
            return None, f"Erro ao acessar site (Status: {response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Extração dos Dados ---
        
        # 1. Santo / Título
        titulo_elem = soup.find('h1', class_='entry-title')
        santo = titulo_elem.get_text(strip=True) if titulo_elem else "Liturgia do Dia"

        # 2. Conteúdo Principal
        conteudo_div = soup.find('div', class_='entry-content')
        if not conteudo_div:
            return None, "Estrutura do site mudou (conteúdo não achado)."

        texto_bruto = conteudo_div.get_text(separator="\n")
        
        # 3. Lógica de Separação (Evangelho vs Leitura)
        # Tenta achar marcadores comuns no texto
        evangelho = ""
        primeira_leitura = ""
        
        # Estratégia simples de split
        if "Evangelho" in texto_bruto:
            partes = texto_bruto.split("Evangelho", 1) # Divide na primeira ocorrência
            primeira_leitura = partes[0].strip()
            # Pega o restante como Evangelho, limpando cabeçalhos comuns
            evangelho_raw = partes[1].strip()
            # Remove sufixos comuns de reflexão se existirem (Opcional, refinamento)
            evangelho = evangelho_raw 
        else:
            evangelho = texto_bruto # Se não achar a divisória, traz tudo

        # Limpeza básica de strings
        evangelho = evangelho.replace("—", "").strip()

        return {
            "data": data_obj.strftime("%d/%m/%Y"),
            "url_origem": url,
            "santo": santo,
            "cor": "Litúrgica", # O site nem sempre expõe a cor em texto fácil
            "primeira_leitura": primeira_leitura[:1500], # Limite de segurança
            "evangelho": evangelho[:3000], 
            "reflexao": "" # Deixamos vazio para a IA preencher depois se necessário
        }, None

    except Exception as e:
        return None, f"Erro técnico: {str(e)}"

# --- Interface do Usuário ---
st.title("🙏 Liturgia Diária & Roteiros")
st.markdown("Busque a liturgia de qualquer data para gerar conteúdo.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📅 Selecione a Data")
    data_selecionada = st.date_input("Data da Liturgia", datetime.date.today())
    data_str_formatada = data_selecionada.strftime("%d/%m/%Y")
    
    # Botão de Busca
    if st.button("🔍 Buscar Liturgia", use_container_width=True):
        with st.spinner(f"Buscando liturgia de {data_str_formatada}..."):
            
            # 1. Tenta carregar do banco local primeiro
            dados_db = carregar_do_banco(data_str_formatada)
            
            if dados_db:
                st.session_state['dados_liturgia'] = dados_db
                st.success("✅ Carregado do Histórico Local!")
            else:
                # 2. Busca na Web
                dados_web, erro = get_liturgia_cancaonova(data_selecionada)
                
                if dados_web:
                    salvar_no_banco(dados_web)
                    st.session_state['dados_liturgia'] = dados_web
                    st.success("✅ Liturgia encontrada e salva!")
                else:
                    st.error(f"❌ {erro}")
                    st.info("Dica: Tente selecionar uma data passada ou a data de hoje.")

    st.divider()
    
    st.subheader("📂 Histórico")
    itens_historico = listar_historico()
    if itens_historico:
        for data_h, santo_h in itens_historico:
            if st.button(f"📄 {data_h} - {santo_h}", key=data_h):
                dados_recuperados = carregar_do_banco(data_h)
                st.session_state['dados_liturgia'] = dados_recuperados
                st.rerun()
    else:
        st.caption("Seu histórico de pesquisas aparecerá aqui.")

with col2:
    if 'dados_liturgia' in st.session_state:
        d = st.session_state['dados_liturgia']
        
        st.info(f"Visualizando: **{d['data']}**")
        st.markdown(f"## {d['santo']}")
        
        tab1, tab2 = st.tabs(["📖 Evangelho", "📜 Primeira Leitura"])
        
        with tab1:
            st.write(d['evangelho'])
        with tab2:
            st.write(d['primeira_leitura'])
            
        st.divider()
        
        col_btn_1, col_btn_2 = st.columns([1, 3])
        with col_btn_2:
            if st.button("✨ Ir para Gerador de Roteiro Viral ➡️", type="primary", use_container_width=True):
                st.switch_page("pages/1_Roteiro_Viral.py")
            
    else:
        st.warning("👈 Selecione uma data e clique em buscar para começar.")
        # Espaço vazio ou imagem ilustrativa
        st.empty()
