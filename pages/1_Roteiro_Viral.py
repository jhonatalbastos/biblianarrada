import streamlit as st
import sqlite3
import json
import os # Necessário para simular o caminho do arquivo

# --- CONFIGURAÇÃO E UTILS DE PERSISTÊNCIA (Recuperados do arquivo 1) ---
DB_FILE = 'biblia_narrada_db.sqlite'

def get_db_connection():
    """Cria e retorna a conexão com o banco de dados."""
    return sqlite3.connect(DB_FILE)

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
    """Carrega o progresso de uma leitura específica ou de todas as leituras ativas."""
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

# --- FUNÇÃO DE NAVEGAÇÃO EXPANDIDA (Recuperada e Otimizada) ---
def render_navigation_bar(current_page_title):
    
    # 1. Carrega todas as produções ativas
    if 'leituras_em_producao' not in st.session_state:
        st.session_state['leituras_em_producao'] = load_producao_status()
        
    leituras_ativas = st.session_state.get('leituras_em_producao', {})
    
    opcoes_dropdown = {}
    chaves_ordenadas = sorted(leituras_ativas.keys())
    
    leitura_atual_key = None
    if 'leitura_atual' in st.session_state:
        leitura_atual = st.session_state['leitura_atual']
        leitura_atual_key = f"{st.session_state.get('data_atual_str', '')}-{leitura_atual['tipo']}"

    default_index = 0
    
    for i, chave in enumerate(chaves_ordenadas):
        item = leituras_ativas[chave]
        progresso = item['progresso']
        
        if progresso.get('publicacao', False) and item.get('em_producao', 0) == 0:
            continue
            
        rotulo = f"[{item['data_liturgia']}] {item['tipo_leitura']}"
        opcoes_dropdown[rotulo] = chave
        
        if chave == leitura_atual_key:
            default_index = len(opcoes_dropdown) - 1
            
    # --- Estilização e Layout Fixo ---
    st.markdown("""
        <style>
        /* Esconde o menu principal e footer padrões do Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        /* Estiliza o Expander para ser discreto no topo */
        [data-testid="stExpander"] {
            margin-top: -30px; /* Reduz margem superior */
        }
        [data-testid="stExpander"] > div:first-child {
            padding-top: 5px; 
            padding-bottom: 5px;
        }
        /* Ajusta o estilo dos botões da barra de navegação para mobile */
        .nav-button-container {
            display: flex;
            flex-wrap: wrap; /* Permite que os botões quebrem em telas pequenas */
            gap: 5px;
            padding-bottom: 5px;
        }
        /* Estilo dos botões da barra de navegação */
        .nav-button-container .stButton > button {
            padding: 0.2rem 0.5rem;
            margin: 0;
            line-height: 1;
            flex-grow: 1; /* Permite que os botões usem o espaço disponível */
            min-width: 40px; /* Garante que os ícones não sumam */
        }
        </style>
    """, unsafe_allow_html=True)
    
    # --- Título do Expander ---
    expander_title = "🛠️ Controle de Produção | "
    if 'leitura_atual' in st.session_state:
        leitura_atual = st.session_state['leitura_atual']
        expander_title += f"{st.session_state.get('data_atual_str', '')} - {leitura_atual.get('tipo', 'Nenhuma Leitura Selecionada')}"
    else:
         expander_title += "Nenhuma Leitura Selecionada"
         
    
    with st.expander(expander_title, expanded=False):
        
        # Conteúdo do Expander (Dropdown e Botões)
        # Em mobile, col_select e col_nav se empilham
        col_select, col_nav = st.columns([3, 5])
        
        with col_select:
            opcoes_nomes = list(opcoes_dropdown.keys())
            
            if not opcoes_nomes:
                st.warning("Nenhuma leitura marcada 'Em Produção'. Volte ao Dashboard.")
                if st.button("🏠 Ir para Início/Dashboard"): st.switch_page("Inicio.py")
                st.stop()
                return

            if leitura_atual_key not in opcoes_dropdown.values():
                default_index = 0 
                
            selected_option = st.selectbox(
                "Mudar Leitura Ativa:",
                opcoes_nomes,
                index=default_index,
                key='nav_leitura_dropdown'
            )
            
            # Lógica para trocar a leitura selecionada no dropdown
            if st.session_state.get('last_selected_nav') != selected_option:
                chave_selecionada = opcoes_dropdown[selected_option]
                item_selecionado = leituras_ativas[chave_selecionada]
                
                dados_dia = carregar_do_banco(item_selecionado['data_liturgia'])
                
                if dados_dia and 'leituras' in dados_dia:
                    leitura_completa = next((l for l in dados_dia['leituras'] if l['tipo'] == item_selecionado['tipo_leitura']), None)
                    if leitura_completa:
                        st.session_state['leitura_atual'] = leitura_completa
                        st.session_state['data_atual_str'] = item_selecionado['data_liturgia']
                        st.session_state['progresso_leitura_atual'] = item_selecionado['progresso']
                        st.session_state['leitura_atual']['cor_liturgica'] = dados_dia['cor']

                        st.session_state['last_selected_nav'] = selected_option
                        st.switch_page(st.session_state['current_page_name'])
                        
        
        if 'leitura_atual' not in st.session_state:
             st.stop()
             return
             
        leitura_atual = st.session_state['leitura_atual']
        chave_atual = f"{st.session_state['data_atual_str']}-{leitura_atual['tipo']}"
        progresso = st.session_state.get('progresso_leitura_atual', {})
        
        midia_pronta = progresso.get('imagens', False) or progresso.get('audio', False)

        stages = [
            ('Roteiro', 'roteiro', 'pages/1_Roteiro_Viral.py', '📝', True),
            ('Imagens', 'imagens', 'pages/2_Imagens.py', '🎨', progresso.get('roteiro', False)),
            ('Áudio', 'audio', 'pages/3_Audio_TTS.py', '🔊', progresso.get('roteiro', False)),
            ('Overlay', 'overlay', 'pages/4_Overlay.py', '🖼️', midia_pronta),
            ('Legendas', 'legendas', 'pages/5_Legendas.py', '💬', midia_pronta),
            ('Vídeo', 'video', 'pages/6_Video_Final.py', '🎬', progresso.get('overlay', False) and progresso.get('legendas', False)),
            ('Publicar', 'publicacao', 'pages/7_Publicar.py', '🚀', progresso.get('video', False))
        ]

        # Botões de Navegação Horizontal
        with col_nav:
            st.markdown('<div class="nav-button-container">', unsafe_allow_html=True)
            
            current_page = st.session_state['current_page_name']
            
            for (label, key, page, icon, base_enabled) in stages:
                status = progresso.get(key, False)
                is_current = current_page == page
                
                display_icon = f"✅" if status and not is_current else icon
                btn_disabled = not base_enabled and not status and not is_current
                
                # Renderiza o botão dentro do container flexível
                btn_style = "primary" if is_current else "secondary"
                # Inclui o label no help/tooltip
                if st.button(display_icon, key=f"nav_btn_{chave_atual}_{key}", type=btn_style, disabled=btn_disabled, help=f"{label} ({'Pronto' if status else 'Pendente'})"):
                    update_producao_status(chave_atual, st.session_state['data_atual_str'], leitura_atual['tipo'], progresso, 1)
                    st.switch_page(page)
                    
            st.markdown('</div>', unsafe_allow_html=True)

    # Título da Página Abaixo da Barra
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    st.caption(f"Leitura Atual: **{leitura_atual.get('tipo', 'N/A')}** - Referência: {leitura_atual.get('ref', 'N/A')}")
    st.markdown("---")
# --- Fim Função de Navegação ---


# --- FUNÇÕES AUXILIARES PARA IMAGEM ---

# Simulação de geração/upload de imagem
def generate_image(prompt):
    """Simula a chamada a um serviço de geração de imagem (DALL-E, Midjourney, etc.)"""
    st.info(f"🎨 Gerando imagem com o prompt: **'{prompt}'**")
    # Retorna um caminho de imagem simulado
    return "imagens_cache/imagem_gerada_simulada.png" 

def save_image_info(chave_progresso, image_path, prompt):
    """Salva o caminho da imagem e o prompt no banco de dados (Simulação)"""
    if 'artefatos' not in st.session_state:
        st.session_state.artefatos = {}
        
    st.session_state.artefatos['imagem_path'] = image_path
    st.session_state.artefatos['imagem_prompt_usado'] = prompt
    st.session_state['progresso_leitura_atual']['imagens'] = True
    
    # Salva o progresso no banco de dados
    leitura = st.session_state['leitura_atual']
    data_str = st.session_state['data_atual_str']
    progresso = st.session_state['progresso_leitura_atual']
    
    update_producao_status(
        chave_progresso, 
        data_str, 
        leitura['tipo'], 
        progresso, 
        1 
    )


# --- LÓGICA PRINCIPAL DA PÁGINA 2 ---

st.set_page_config(page_title="2 – Imagens", layout="wide")

# 0. Configuração de estado da página e chamada de navegação
st.session_state['current_page_name'] = "pages/2_Imagens.py" 
render_navigation_bar("🎨 2 – Geração de Imagens e Assets")

if 'leitura_atual' not in st.session_state:
    st.error("Nenhuma leitura selecionada. Por favor, volte ao Dashboard.")
    st.stop()
    
if 'artefatos' not in st.session_state or 'roteiro_final' not in st.session_state.artefatos:
    st.warning("⚠️ Roteiro não finalizado. Por favor, complete a Etapa 1 primeiro.")
    if st.button("⬅️ Ir para 1. Roteiro"): st.switch_page("pages/1_Roteiro_Viral.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state['data_atual_str']
progresso = st.session_state['progresso_leitura_atual']
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega artefatos do Roteiro
roteiro_final = st.session_state.artefatos.get('roteiro_final', 'Roteiro não encontrado.')
prompt_base = st.session_state.artefatos.get('prompt_imagem', 'Prompt não definido na Etapa 1.')

# 1. Visualização do Roteiro e Prompt Base
st.subheader("📝 Roteiro Final")
with st.expander("Visualizar o Roteiro Final", expanded=False):
    st.markdown(roteiro_final)

st.subheader("🖼️ Prompt Base da Imagem")
st.warning("Edite o prompt antes de gerar, se necessário. O estilo cinematográfico é crucial!")
prompt_editado = st.text_area(
    "Prompt de Geração (Melhore o Estilo!):",
    value=prompt_base,
    height=100,
    key='prompt_edicao_area'
)

# 2. Geração/Upload e Pré-visualização da Imagem
st.markdown("---")
col_generate, col_upload = st.columns(2)

image_path = st.session_state.artefatos.get('imagem_path', None)

with col_generate:
    if st.button("✨ Gerar Imagem com IA", type="primary", use_container_width=True):
        if not prompt_editado:
            st.error("O prompt não pode estar vazio para a geração.")
        else:
            path_simulado = generate_image(prompt_editado)
            save_image_info(chave_progresso, path_simulado, prompt_editado)
            st.rerun()

with col_upload:
    uploaded_file = st.file_uploader("📥 Ou faça Upload de uma Imagem Pronta (.png/.jpg)", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        # Simula o salvamento do upload
        image_path_uploaded = f"imagens_cache/upload_{chave_progresso}_{uploaded_file.name}"
        # Simula a escrita do arquivo (em um ambiente real, você salvaria isso em um bucket S3 ou disco persistente)
        with open(image_path_uploaded, "wb") as f:
            f.write(uploaded_file.getbuffer()) 
            
        save_image_info(chave_progresso, image_path_uploaded, "Upload Manual")
        st.success("Imagem enviada e salva!")
        st.rerun()

st.markdown("---")

# 3. Exibição do Resultado
if image_path:
    st.subheader("✅ Imagem Final Selecionada")
    st.caption(f"Caminho Simulado: `{image_path}`")
    
    # Exibe a imagem (simulando que 'image_path' existe localmente ou é um URL)
    # NOTE: Em um ambiente real, você precisaria garantir que o Streamlit consiga acessar este caminho.
    # Aqui, usaremos uma imagem placeholder, pois o caminho simulado não existe no ambiente do Streamlit Cloud/Deploy.
    
    st.image("", 
             caption=f"Prompt utilizado: {st.session_state.artefatos.get('imagem_prompt_usado', 'N/A')}",
             use_column_width=True)
    
    st.success("Progresso Salvo! Imagem pronta para uso.")
    
    if st.button("🔊 Ir para 3. Áudio TTS", type="primary", use_container_width=True):
        st.switch_page("pages/3_Audio_TTS.py")
else:
    st.info("Aguardando a geração ou upload da imagem de fundo para a produção do vídeo.")
    st.session_state['progresso_leitura_atual']['imagens'] = False # Garante que está como Falso se não houver path
    # Chama o update status para garantir que o progresso seja atualizado em caso de re-acesso
    update_producao_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)

