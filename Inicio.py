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
    # Cria tabela se não existir
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

# Inicializa o DB ao abrir
init_db()

# --- Função de Scraping Dinâmica ---
def get_liturgia_cancaonova(data_obj):
    # Dicionário para converter mês numérico para nome (URL da Canção Nova usa nomes)
    meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'marco', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    
    dia = data_obj.day
    mes_nome = meses[data_obj.month]
    ano = data_obj.year
    
    # Constrói a URL dinâmica: ex: .../d/5-dezembro-2025/
    url = f"https://liturgia.cancaonova.com/pb/liturgia/d/{dia}-{mes_nome}-{ano}/"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return None, f"Erro ao acessar site (Status: {response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extração de dados (Adaptado para o layout padrão da CN)
        # Título / Santo
        titulo_elem = soup.find('h1', class_='entry-title')
        santo = titulo_elem.get_text(strip=True) if titulo_elem else "Liturgia Diária"

        # Cor Litúrgica (Geralmente está numa div ou texto específico, mas vamos tentar pegar genérico)
        cor = "Não identificada" 
        # Tentar achar a cor baseada em palavras chave no texto se necessário, 
        # mas por hora deixamos manual ou N/A se o site não explicitar na classe.

        # Textos
        conteudo = soup.find('div', class_='entry-content')
        if not conteudo:
            return None, "Conteúdo não encontrado na página."

        # Separação simples (Melhoria: buscar pelos h2/h3 de "Evangelho", "Primeira Leitura")
        texto_completo = conteudo.get_text(separator="\n").strip()
        
        # Tentativa de isolar o Evangelho
        evangelho = ""
        primeira_leitura = ""
        
        partes = texto_completo.split("Evangelho")
        if len(partes) > 1:
            primeira_leitura = partes[0]
            evangelho = partes[1]
        else:
            evangelho = texto_completo # Fallback

        return {
            "data": data_obj.strftime("%d/%m/%Y"),
            "url_origem": url,
            "santo": santo,
            "cor": cor,
            "primeira_leitura": primeira_leitura[:1000] + "...", # Limita tamanho
            "evangelho": evangelho,
            "reflexao": "Reflexão gerada automaticamente pela IA no próximo passo."
        }, None

    except Exception as e:
        return None, str(e)

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
        with st.spinner("Acessando Canção Nova..."):
            # 1. Tenta carregar do banco local primeiro
            dados_db = carregar_do_banco(data_str_formatada)
            
            if dados_db:
                st.session_state['dados_liturgia'] = dados_db
                st.success("✅ Carregado do Histórico!")
            else:
                # 2. Se não tiver no banco, faz o scraping
                dados_web, erro = get_liturgia_cancaonova(data_selecionada)
                
                if dados_web:
                    # Salva no banco e na sessão
                    salvar_no_banco(dados_web)
                    st.session_state['dados_liturgia'] = dados_web
                    st.success("✅ Liturgia encontrada e salva!")
                else:
                    st.error(f"Erro ao buscar: {erro}")

    st.divider()
    
    # Histórico Rápido
    st.subheader("📂 Histórico Recente")
    itens_historico = listar_historico()
    if itens_historico:
        for data_h, santo_h in itens_historico:
            if st.button(f"🔄 {data_h} - {santo_h}", key=data_h):
                dados_recuperados = carregar_do_banco(data_h)
                st.session_state['dados_liturgia'] = dados_recuperados
                st.rerun()
    else:
        st.info("Nenhuma pesquisa salva ainda.")

with col2:
    if 'dados_liturgia' in st.session_state:
        d = st.session_state['dados_liturgia']
        
        st.info(f"Visualizando: **{d['data']}**")
        st.subheader(d['santo'])
        
        with st.expander("📖 Evangelho", expanded=True):
            st.write(d['evangelho'])
            
        with st.expander("📜 Primeira Leitura"):
            st.write(d['primeira_leitura'])
            
        st.divider()
        
        # BOTÃO PARA IR AO ROTEIRO
        st.success("Tudo pronto! Agora crie o roteiro.")
        if st.button("✨ Ir para Gerador de Roteiro Viral ➡️", type="primary"):
            st.switch_page("pages/1_Roteiro_Viral.py")
            
    else:
        st.warning("👈 Selecione uma data e clique em buscar para começar.")
        st.image("https://images.unsplash.com/photo-1507692863980-863a681c4e4c?q=80&w=1000&auto=format&fit=crop", caption="Aguardando busca...")
