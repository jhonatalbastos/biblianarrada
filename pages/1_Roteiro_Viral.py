import streamlit as st
import sys
import os
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE IMPORTAÇÃO (Para encontrar modules/database.py)
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro Crítico: Módulo 'modules/database.py' não encontrado. Verifique a estrutura de pastas.")
    st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="1. Roteiro Viral",
    page_icon="✍️",
    layout="wide"
)

# ---------------------------------------------------------------------
# 3. VERIFICAÇÃO DE SEGURANÇA (Sessão)
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    st.info("Vá para a página inicial e escolha uma liturgia.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

# Recupera dados da sessão
leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega progresso do banco
progresso, em_producao = db.load_status(chave_progresso)

# Recupera blocos salvos anteriormente (se houver)
blocos_salvos = progresso.get('roteiro_blocos', {})

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("📝 Passo 1: Roteiro Estruturado")

# Cabeçalho
with st.container(border=True):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"**Tema:** {leitura['titulo']} | **Ref:** {leitura['ref']}")
    with c2:
        if st.button("🏠 Home"):
            st.switch_page("Inicio.py")

st.divider()

col_esq, col_dir = st.columns([1, 1.2])

# --- COLUNA ESQUERDA: TEXTO BÍBLICO (FONTE) ---
with col_esq:
    st.subheader("📖 Texto Original")
    with st.container(border=True, height=700):
        st.caption("Use este texto como base para preencher os blocos ao lado.")
        st.markdown(f"### {leitura['titulo']}")
        st.markdown("---")
        st.write(leitura['texto'])

# --- COLUNA DIREITA: EDITOR EM 4 BLOCOS ---
with col_dir:
    st.subheader("✍️ Editor Viral")
    
    with st.form("form_roteiro_blocos"):
        st.info("Preencha os 4 passos para garantir a retenção do vídeo.")

        # 1. GANCHO
        st.markdown("### 🪝 1. O Gancho (0-5s)")
        texto_gancho = st.text_area(
            label="Chame a atenção imediatamente:",
            value=blocos_salvos.get('gancho', f"Você sabia que [curiosidade sobre {leitura['ref']}]?"),
            height=100,
            help="Uma frase impactante ou pergunta curiosa para prender a pessoa."
        )

        # 2. CONTEÚDO
        st.markdown("### 📜 2. A Mensagem (Corpo)")
        texto_corpo = st.text_area(
            label="O ensinamento bíblico resumido:",
            value=blocos_salvos.get('corpo', f"A leitura de hoje nos ensina que... (Resumo: {leitura['texto'][:80]}...)"),
            height=150,
            help="Explique o texto bíblico de forma simples e direta."
        )

        # 3. APLICAÇÃO
        st.markdown("### 💡 3. Aplicação Prática")
        texto_app = st.text_area(
            label="Como aplicar isso hoje?",
            value=blocos_salvos.get('aplicacao', "Então, no dia de hoje, tente..."),
            height=100,
            help="Traga o ensinamento para a realidade do ouvinte."
        )

        # 4. CTA
        st.markdown("### 📢 4. Chamada (CTA)")
        texto_cta = st.text_area(
            label="Engajamento:",
            value=blocos_salvos.get('cta', "Se você recebe essa palavra, digite AMÉM!"),
            height=80,
            help="Peça like, comentário ou compartilhamento."
        )

        st.markdown("---")
        
        # Botão de Salvar
        btn_salvar = st.form_submit_button("💾 Salvar Roteiro", type="primary", use_container_width=True)

        if btn_salvar:
            # 1. Salva os blocos estruturados (para reedição futura)
            progresso['roteiro_blocos'] = {
                'gancho': texto_gancho,
                'corpo': texto_corpo,
                'aplicacao': texto_app,
                'cta': texto_cta
            }

            # 2. Concatena tudo para o Texto-para-Fala (TTS)
            # Adiciona quebras de linha duplas para pausas naturais na fala
            texto_final_concatenado = f"{texto_gancho}\n\n{texto_corpo}\n\n{texto_app}\n\n{texto_cta}"
            progresso['texto_roteiro'] = texto_final_concatenado
            
            # 3. Marca etapa como concluída
            progresso['roteiro'] = True

            # 4. Salva no Banco de Dados
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1) # Etapa 1
            
            # Atualiza sessão
            st.session_state['progresso_leitura_atual'] = progresso
            
            st.success("✅ Roteiro salvo com sucesso! O texto foi unido para a narração.")

# --- NAVEGAÇÃO PARA PRÓXIMA PÁGINA ---
if progresso.get('roteiro'):
    st.divider()
    col_nav = st.columns([1, 2, 1])
    with col_nav[1]:
        if st.button("Próximo: Criar Capa (Thumbnail) ➡️", type="secondary", use_container_width=True):
            st.switch_page("pages/2_Thumbnail_AB.py")
