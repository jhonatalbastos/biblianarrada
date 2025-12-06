import streamlit as st
import sys
import os
import json
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CORREÇÃO DE IMPORTAÇÃO (PÁGINAS DENTRO DE /PAGES)
# ---------------------------------------------------------------------
# Adiciona o diretório pai (raiz) ao sys.path para encontrar 'modules'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="1. Roteiro Viral", layout="wide")

# ---------------------------------------------------------------------
# 3. RECUPERAÇÃO DE ESTADO (CRÍTICO)
# ---------------------------------------------------------------------
# Se não houver leitura na sessão, tenta recuperar ou manda voltar
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    st.info("Por favor, volte para a página inicial e selecione uma liturgia.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

# Carrega dados da sessão
leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega status atual do banco
progresso, em_producao = db.load_status(chave_progresso)

# ---------------------------------------------------------------------
# 4. INTERFACE DO ROTEIRO
# ---------------------------------------------------------------------

st.title("📝 Passo 1: Roteiro Viral")

# Barra de Progresso Superior
cols_header = st.columns([3, 1])
with cols_header[0]:
    st.markdown(f"**Leitura:** {leitura['titulo']}")
    st.caption(f"Ref: {leitura['ref']} | Data: {data_str}")
with cols_header[1]:
    if st.button("🔙 Trocar Leitura"):
        st.switch_page("Inicio.py")

st.divider()

# --- COLUNA 1: TEXTO ORIGINAL (REFERÊNCIA) ---
col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.subheader("📖 Texto Original")
    with st.container(border=True):
        st.markdown(f"### {leitura['titulo']}")
        st.markdown(f"**{leitura['ref']}**")
        st.write(leitura['texto'])

# --- COLUNA 2: EDITOR DE ROTEIRO ---
with col_dir:
    st.subheader("✍️ Editor de Roteiro")
    
    # Campo para o Roteiro
    # Se já existir roteiro salvo no banco (dentro do JSON de progresso), carrega ele.
    # Caso contrário, sugere um template vazio.
    roteiro_salvo = progresso.get('texto_roteiro', '')
    
    if not roteiro_salvo:
        # Template Sugerido
        roteiro_salvo = f"""## Título: [Insira um título chamativo]

**Gancho (0-5s):**
Sabia que... [Curiosidade sobre {leitura['ref']}]?

**Desenvolvimento:**
Hoje a liturgia nos conta sobre...
{leitura['texto'][:100]}...

**Conclusão/Chamada:**
O que você acha disso? Comente 'Amém' se você crê!"""

    texto_roteiro = st.text_area(
        "Escreva ou gere seu roteiro aqui:",
        value=roteiro_salvo,
        height=500,
        help="Adapte o texto bíblico para um formato de vídeo curto (Reels/TikTok/Shorts)."
    )
    
    # Botões de Ação
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button("🤖 Sugerir Roteiro com IA", disabled=True, help="Configure sua chave de API para habilitar"):
            st.info("Funcionalidade de IA aguardando configuração de chave (Groq/OpenAI).")
    
    with c2:
        if st.button("💾 Salvar Roteiro", type="primary"):
            # Atualiza o dicionário de progresso
            progresso['texto_roteiro'] = texto_roteiro
            progresso['roteiro'] = True # Marca etapa como concluída
            
            # Salva no banco
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)
            
            st.success("Roteiro salvo com sucesso!")
            st.session_state['progresso_leitura_atual'] = progresso
            
            # Opcional: Avançar automaticamente
            # st.switch_page("pages/2_Thumbnail_AB.py")

# ---------------------------------------------------------------------
# 5. NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()
col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    # Botão para ir para a próxima etapa apenas se o roteiro estiver salvo
    if progresso.get('roteiro'):
        if st.button("Próximo: Criar Thumbnail ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/2_Thumbnail_AB.py")
    else:
        st.button("Próximo: Criar Thumbnail ➡️", disabled=True, use_container_width=True, help="Salve o roteiro primeiro.")
