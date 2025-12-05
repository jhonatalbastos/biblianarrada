import streamlit as st
# from groq import Groq # Importar Groq se a chave for configurada

st.set_page_config(page_title="Publicar", page_icon="🚀", layout="wide")
st.session_state['current_page_name'] = 'pages/7_Publicar.py'

# --- Utility Function for Navigation Bar (Identical in all pages 1-7) ---
def render_navigation_bar(current_page_title):
    progresso_leituras = st.session_state.get('progresso_leituras', {})
    leitura_atual = st.session_state.get('leitura_atual')
    data_atual_str = st.session_state.get('data_atual_str')
    
    # Check for selected video
    if not leitura_atual or not data_atual_str:
        st.error("Nenhuma leitura selecionada. Por favor, volte ao Dashboard (Início).")
        if st.button("🏠 Voltar ao Início"):
            st.switch_page("Inicio.py")
        st.stop()
        return

    # Key for the currently active production
    chave_atual = f"{data_atual_str}-{leitura_atual['tipo']}"
    progresso = progresso_leituras.get(chave_atual, {})
    
    # --- Rótulo e Título ---
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    st.caption(f"📖 Em Produção: **{leitura_atual['tipo']}** ({data_atual_str}) - *Ref: {leitura_atual.get('ref', '')}*")

    # --- Layout da Barra de Navegação de Etapas ---
    cols_nav = st.columns([1, 1, 1, 1, 1, 1, 1])
    
    # Check if the mandatory assets for the subsequent steps are ready
    midia_pronta = progresso.get('imagens', False) and progresso.get('audio', False)

    stages = [
        ('Roteiro', 'roteiro', 'pages/1_Roteiro_Viral.py', '📝', '📝', True),
        ('Imagens', 'imagens', 'pages/2_Imagens.py', '🎨', '🔒', progresso.get('roteiro', False)),
        ('Áudio', 'audio', 'pages/3_Audio_TTS.py', '🔊', '🔒', progresso.get('roteiro', False)),
        ('Overlay', 'overlay', 'pages/4_Overlay.py', '🖼️', '🔒', midia_pronta),
        ('Legendas', 'legendas', 'pages/5_Legendas.py', '💬', '🔒', midia_pronta),
        ('Vídeo', 'video', 'pages/6_Video_Final.py', '🎬', '🔒', midia_pronta),
        ('Publicar', 'publicacao', 'pages/7_Publicar.py', '🚀', '🔒', progresso.get('video', False))
    ]

    # Render Buttons
    current_page = st.session_state['current_page_name']
    
    for i, (label, key, page, icon_on, icon_off, base_enabled) in enumerate(stages):
        status = progresso.get(key, False)
        is_current = current_page == page
        
        icon = icon_on if status or is_current else icon_off
        display_icon = f"✅ {icon}" if status and not is_current else icon
        
        # Enable logic
        enabled = base_enabled
        btn_disabled = not enabled and not status and not is_current
        
        with cols_nav[i]:
            btn_style = "primary" if is_current else "secondary"
            if st.button(display_icon, key=f"nav_btn_{key}", type=btn_style, disabled=btn_disabled, help=f"{label} ({'Pronto' if status else 'Pendente'})"):
                st.switch_page(page)

    st.markdown("---")
# --- End Utility Function ---


if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

leitura = st.session_state['leitura_atual']
roteiro = st.session_state.get('roteiro_gerado', {})
data_str = st.session_state.get('data_atual_str', '')

render_navigation_bar("🚀 Central de Publicação")

# --- Interface ---
# SIMULANDO GROQ/IA
if 'video_final_path' not in st.session_state:
    st.warning("A etapa Vídeo Final não foi concluída. Gere o vídeo antes de publicar.")
    st.stop()
    
#client = Groq(api_key=st.secrets.get("GROQ_API_KEY"))

col_input, col_output = st.columns(2)

with col_input:
    st.subheader("Conteúdo para Geração IA")
    st.info(f"Base: {leitura['tipo']} - {leitura.get('ref')}")
    st.text_area("Roteiro Base (Hook)", roteiro.get('hook', 'Texto indisponível'), height=150, disabled=True)
    
    if st.button("✨ Gerar Títulos com IA (Simulação)", type="primary"):
        # SIMULAÇÃO DE RESPOSTA DA IA
        
        resposta_ia = f"""
        **Sugestões para YouTube Shorts (Máx 100 chars):**
        1. A Colheita é Grande: O Desafio de Jesus
        2. Por que Jesus Enviou 72 Discípulos?
        3. ⚠️ Oração Poderosa para Chamado Urgente! ⚠️
        4. O Segredo dos Trabalhadores da Última Hora
        5. O que Lucas 10:1-10 ensina sobre a Missão?

        **Sugestões para TikTok (Estilo Curiosidade):**
        * VOCÊ NÃO VAI ACREDITAR no que Jesus disse a 72 pessoas!
        * O número 72 na Bíblia esconde um segredo!
        * Tudo o que você precisa saber antes de sair de casa hoje (Lucas 10)

        **Descrição Curta e Hashtags:**
        O Evangelho do dia nos lembra que a missão é urgente! Peça ao Senhor da colheita que envie mais trabalhadores. Qual o seu papel? #BibliaNarrada #EvangelhoDoDia #ShortsDeFe #Lucas10 #Igreja
        """
        st.session_state['metadados_pub'] = resposta_ia

with col_output:
    st.subheader("📋 Metadados Gerados")
    
    if 'metadados_pub' in st.session_state:
        st.markdown(st.session_state['metadados_pub'])
        
        if st.button("✅ Marcar como Publicado", use_container_width=True, type="secondary"):
            # Atualiza Status Final
            chave = f"{data_str}-{leitura['tipo']}"
            if chave in st.session_state.get('progresso_leituras', {}):
                st.session_state['progresso_leituras'][chave]['publicacao'] = True
            
            st.success("🎉 Projeto concluído e marcado como Publicado! Ele será removido do painel principal.")
            if st.button("🏠 Voltar ao Início (Novo Projeto)"):
                st.switch_page("Inicio.py")
    else:
        st.info("Clique em gerar para ver as sugestões de metadados.")
