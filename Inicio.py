import streamlit as st
import requests
import sqlite3
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup  # Necessário para o scraping (fallback)

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Início – Bíblia Narrada", layout="wide", page_icon="🙏")

# --- BANCO DE DADOS (SQLITE LOCAL) ---
DB_FILE = 'biblia_narrada_db.sqlite'

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabela para guardar o texto cru da liturgia (evita re-buscar na internet)
    c.execute('''CREATE TABLE IF NOT EXISTS historico
                 (data_liturgia TEXT PRIMARY KEY, json_completo TEXT, cor TEXT, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Tabela para controlar status de produção (opcional para integração futura)
    c.execute('''CREATE TABLE IF NOT EXISTS producao_status
                 (chave_leitura TEXT PRIMARY KEY, data_liturgia TEXT, tipo_leitura TEXT, progresso TEXT, em_producao INTEGER, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Inicializa o banco ao carregar
init_db()

# --- FUNÇÕES DE BUSCA (SCRAPER + API) ---

def scrape_cancaonova(data_obj):
    """
    Faz scraping do site da Canção Nova caso a API falhe.
    Retorna um dicionário estruturado.
    """
    # Formato da URL: https://liturgia.cancaonova.com/pb/liturgia_diaria/1-12-2023/
    url = f"https://liturgia.cancaonova.com/pb/liturgia_diaria/{data_obj.day}-{data_obj.month}-{data_obj.year}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Estrutura de retorno
        resultado = {
            "data": data_obj.strftime('%Y-%m-%d'),
            "nome_dia": "Liturgia Diária", # Default
            "cor": "N/A",
            "leituras": []
        }

        # Tenta pegar a cor litúrgica e o nome do dia (geralmente em h1 ou classes especificas)
        titulo_main = soup.find('h1', class_='entry-title')
        if titulo_main:
            resultado["nome_dia"] = titulo_main.get_text(strip=True)

        # Mapeamento básico de seções na Canção Nova (tab-pane)
        # ID normal: liturgia-1 (1ª Leitura), liturgia-2 (Salmo), liturgia-3 (2ª Leitura se houver), liturgia-4 (Evangelho)
        # Nota: A ordem pode variar, então buscamos pelo título dentro da tab
        
        abas = soup.find_all('div', class_='tab-pane')
        
        for aba in abas:
            titulo_aba = aba.find('h1') or aba.find('h2') or aba.find('strong')
            if not titulo_aba: continue
            
            titulo_texto = titulo_aba.get_text(strip=True).lower()
            conteudo_texto = aba.get_text(separator='\n', strip=True)
            
            # Remove o título do conteúdo para ficar limpo
            conteudo_limpo = conteudo_texto.replace(titulo_aba.get_text(strip=True), "").strip()
            
            tipo = "Outro"
            if "primeira leitura" in titulo_texto or "1ª leitura" in titulo_texto:
                tipo = "Primeira Leitura"
            elif "segunda leitura" in titulo_texto or "2ª leitura" in titulo_texto:
                tipo = "Segunda Leitura"
            elif "salmo" in titulo_texto:
                tipo = "Salmo"
            elif "evangelho" in titulo_texto:
                tipo = "Evangelho"
                
            resultado["leituras"].append({
                "titulo": tipo,
                "referencia": "", # Difícil extrair com precisão sem regex complexo, deixa vazio por enquanto
                "texto": conteudo_limpo
            })
            
        return resultado

    except Exception as e:
        print(f"Erro no Scraper: {e}")
        return None

def fetch_liturgia_wrapper(data_obj):
    """
    Tenta buscar no Banco Local -> Tenta API -> Tenta Scraper -> Salva no Banco.
    """
    data_str = data_obj.strftime('%Y-%m-%d')
    
    # 1. Tenta pegar do banco local (Cache)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    
    if res:
        return json.loads(res[0])
    
    # 2. Se não tem no banco, tenta buscar online
    dados_finais = None
    
    # Tentativa A: API (exemplo Vercel)
    try:
        # url_api = f"https://liturgia.vercel.app/api/v1/{data_obj.day}/{data_obj.month}/{data_obj.year}"
        # resp = requests.get(url_api, timeout=3)
        # if resp.status_code == 200:
        #     dados_api = resp.json()
        #     # Adaptação do JSON da API para nosso formato interno se necessário
        #     # ...
        #     pass
        # Desativado temporariamente para forçar o scraper (mais confiável hoje em dia)
        pass
    except:
        pass
    
    # Tentativa B: Scraper (Fallback robusto)
    if not dados_finais:
        with st.spinner(f"Buscando liturgia no site da Canção Nova para {data_str}..."):
            dados_finais = scrape_cancaonova(data_obj)
    
    # 3. Salva no banco se encontrou
    if dados_finais:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO historico (data_liturgia, json_completo, cor) 
                     VALUES (?, ?, ?)''', 
                     (data_str, json.dumps(dados_finais, ensure_ascii=False), dados_finais.get('cor', 'N/A')))
        conn.commit()
        conn.close()
        return dados_finais
    else:
        return None

# --- INTERFACE GRÁFICA ---

st.title("📖 Bíblia Narrada | Central de Liturgia")
st.markdown("Busque a liturgia do dia e inicie o processo de produção de vídeo.")

# Área de Busca
col_top1, col_top2 = st.columns([1, 3])

with col_top1:
    st.subheader("Data")
    dt_input = st.date_input("Selecione o dia", value=datetime.today())
    
    if st.button("🔍 Buscar Liturgia", type="primary", use_container_width=True):
        st.session_state['data_busca'] = dt_input.strftime('%Y-%m-%d')
        # Limpa dados antigos da sessão para forçar atualização visual
        if 'dados_liturgia_atual' in st.session_state:
            del st.session_state['dados_liturgia_atual']
        st.rerun()

# Recupera do histórico se houver solicitação
if 'data_busca' in st.session_state:
    data_dt = datetime.strptime(st.session_state['data_busca'], '%Y-%m-%d')
    dados = fetch_liturgia_wrapper(data_dt)
    
    if dados:
        st.session_state['dados_liturgia_atual'] = dados # Salva para outras páginas usarem
        
        with col_top2:
            st.success(f"Liturgia Carregada: {dados.get('nome_dia', 'Dia Comum')}")
            st.caption(f"Cor Litúrgica (se disponível): {dados.get('cor', '-')}")
        
        st.divider()
        
        # Exibição das Leituras
        leituras = dados.get('leituras', [])
        if not leituras:
            st.warning("Nenhuma leitura encontrada no texto extraído. Verifique se a data é válida.")
        else:
            # Layout dinâmico dependendo do número de leituras
            cols = st.columns(len(leituras)) if len(leituras) > 0 else [st.container()]
            
            for i, leitura in enumerate(leituras):
                with cols[i] if i < len(cols) else st.container():
                    st.markdown(f"### {leitura['titulo']}")
                    texto_preview = leitura['texto'][:500] + "..." if len(leitura['texto']) > 500 else leitura['texto']
                    st.text_area(f"Texto ({leitura['titulo']})", value=leitura['texto'], height=300, key=f"txt_{i}")
                    
                    # Botão para enviar para o Roteiro (Integração com o Pipeline)
                    if st.button(f"🎬 Usar este texto", key=f"btn_use_{i}"):
                        st.info("Copie este texto e vá para a aba '1 - Roteiro' no menu lateral para iniciar.")

    else:
        with col_top2:
            st.error("Não foi possível encontrar a liturgia para esta data. O site fonte pode estar indisponível.")

# --- BARRA LATERAL (HISTÓRICO) ---
with st.sidebar:
    st.header("🕰 Histórico Recente")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT data_liturgia, cor FROM historico ORDER BY data_liturgia DESC LIMIT 10")
    historico = c.fetchall()
    conn.close()
    
    if historico:
        for data_hist, cor_hist in historico:
            if st.button(f"📅 {data_hist}", key=f"hist_{data_hist}"):
                st.session_state['data_busca'] = data_hist
                st.rerun()
    else:
        st.caption("Nenhum histórico ainda.")