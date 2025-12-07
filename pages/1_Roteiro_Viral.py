import streamlit as st
import sys
import os
import json
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CORREÇÃO DE IMPORTAÇÃO (IMPORTANTE PARA A PASTA PAGES)
# ---------------------------------------------------------------------
# Adiciona o diretório pai (raiz do projeto) ao caminho do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    # Tenta fallback caso a estrutura de pastas seja diferente no deploy
    try:
        from modules import database as db
    except ImportError:
        st.error("🚨 Erro Crítico: Não foi possível importar 'modules/database.py'. Verifique se a pasta 'modules' existe na raiz.")
        st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="1. Roteiro Viral", layout="wide")

# ---------------------------------------------------------------------
# 3. VERIFICAÇÃO DE SEGURANÇA (SESSÃO)
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada para produção.")
    st.info("Por favor, vá para a página inicial e selecione uma liturgia.")
    if st.button("🏠 Ir para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

# Recupera dados da sessão
leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))

# Define a chave única para buscar no banco
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega o status atual do banco de dados
progresso, em_producao = db.load_status(chave_progresso)

# ---------------------------------------------------------------------
# 4. INTERFACE DO EDITOR
# ---------------------------------------------------------------------

st.title("📝 Passo 1: Criação do Roteiro")

# Cabeçalho com Metadados
with st.container(border=True):
    col_meta1, col_meta2 = st.columns([3, 1])
    with col_meta1:
        st.markdown(f"**Leitura:** {leitura['titulo']}")
        st.caption(f"Ref: {leitura['ref']} | Data Litúrgica: {data_str}")
        
        # Barra de progresso visual do pipeline
        etapas_concluidas = sum(progresso.values())
        st.progress(etapas_concluidas/7, text=f"Progresso Geral: {etapas_concluidas}/7")
        
    with col_meta2:
        if st.button("🏠 Voltar ao Painel"):
            st.switch_page("Inicio.py")

st.divider()

# Layout de Colunas (Texto Original vs Editor)
col_orig, col_edit = st.columns([1, 1])

# --- COLUNA DA ESQUERDA: TEXTO BÍBLICO ---
with col_orig:
    st.subheader("📖 Texto Original")
    st.info("Use este texto como base para o seu roteiro.")
    
    with st.container(border=True, height=600):
        st.markdown(f"### {leitura['titulo']}")
        st.markdown(f"**{leitura['ref']}**")
        st.markdown("---")
        # Exibe o texto com quebras de linha corretas
        st.write(leitura['texto'])

# --- COLUNA DA DIREITA: EDITOR DE ROTEIRO ---
with col_edit:
    st.subheader("✍️ Seu Roteiro")
    
    # Verifica se já existe texto salvo, senão cria um template
    roteiro_atual = progresso.get('texto_roteiro', '')
    
    if not roteiro_atual:
        # Template padrão para facilitar
        roteiro_atual = f"""## Título: [Escreva um título chamativo]

**Gancho (0-5s):**
Você sabia que [Curiosidade sobre {leitura['ref']}]?

**Corpo do Vídeo:**
A liturgia de hoje nos ensina que...
(Resumo: {leitura['texto'][:80]}...)

**Aplicação Prática:**
Por isso, hoje tente...

**Chamada para Ação:**
Comente "Amém" se você recebe essa palavra!"""

    # Área de Texto Editável
    texto_final = st.text_area(
        "Edite seu roteiro aqui:",
        value=roteiro_atual,
        height=500,
        help="Escreva o texto exatamente como ele deve ser falado no vídeo."
    )
    
    # Botões de Ação
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("") # Espaçamento
        # Futura implementação de IA
        # if st.button("✨ Melhorar com IA"): ...
            
    with c2:
        if st.button("💾 Salvar Roteiro", type="primary", use_container_width=True):
            # Atualiza o dicionário de progresso
            progresso['texto_roteiro'] = texto_final
            progresso['roteiro'] = True  # Marca etapa como concluída
            
            # Salva no banco de dados
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)
            
            st.success("Roteiro salvo com sucesso!")
            # Atualiza a sessão para refletir a mudança imediatamente
            st.session_state['progresso_leitura_atual'] = progresso
            
            # Opcional: Recarregar para atualizar a barra de progresso
            # st.rerun()

# ---------------------------------------------------------------------
# 5. NAVEGAÇÃO PARA PRÓXIMA ETAPA
# ---------------------------------------------------------------------
st.divider()
col_nav_L, col_nav_R = st.columns([1, 4])

with col_nav_R:
    # Botão para avançar (Habilitado apenas se tiver roteiro salvo)
    if progresso.get('roteiro'):
        if st.button("Próximo: Gerar Imagens (Thumbnails) ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/2_Thumbnail_AB.py")
    else:
        st.button("Próximo: Gerar Imagens ➡️", disabled=True, use_container_width=True, help="Você precisa salvar o roteiro antes de avançar.")
