import streamlit as st
import time

st.set_page_config(page_title="Gerar Imagens", page_icon="🎨", layout="wide")
st.session_state['current_page_name'] = 'pages/2_Imagens.py'

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


if 'roteiro_gerado' not in st.session_state:
    st.error("Roteiro não encontrado. Gere o roteiro primeiro.")
    if st.button("Voltar ao Roteiro"): st.switch_page("pages/1_Roteiro_Viral.py")
    st.stop()

roteiro = st.session_state['roteiro_gerado']
blocos = ["hook", "leitura", "reflexao", "aplicacao", "oracao"]

render_navigation_bar("🎨 Estúdio de Criação de Imagens")

# --- Interface ---
col_preview, col_action = st.columns([1, 1])

with col_preview:
    st.subheader("Conteúdo do Roteiro")
    tabs = st.tabs(["Hook", "Leitura", "Reflexão", "Aplicação", "Oração"])
    for i, tab in enumerate(tabs):
        with tab:
            st.info(roteiro[blocos[i]])

with col_action:
    st.subheader("Geração em Massa")
    estilo = st.selectbox("Estilo Visual", ["Realista Cinematic", "Aquarela Suave", "Minimalista", "Épico Bíblico"])
    
    if st.button("🚀 Gerar Todas as Imagens", type="primary"):
        prog_bar = st.progress(0, text="Iniciando...")
        status_text = st.empty()
        
        imagens_geradas = {}
        data_str = st.session_state.get('data_atual_str', '')
        leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
        chave = f"{data_str}-{leitura_tipo}"
        
        total_steps = len(blocos)
        for i, bloco in enumerate(blocos):
            status_text.markdown(f"**Etapa {i+1}/{total_steps}:** Criando Prompt para *{bloco.upper()}*...")
            time.sleep(0.5) 
            
            status_text.markdown(f"**Etapa {i+1}/{total_steps}:** Renderizando imagem ({estilo})...")
            time.sleep(1.5) 
            
            imagens_geradas[bloco] = f"https://placehold.co/600x400?text={bloco.upper()}+{estilo.replace(' ', '+')}"
            
            prog = (i + 1) / total_steps
            prog_bar.progress(prog, text=f"Progresso: {int(prog*100)}%")

        st.session_state['imagens_geradas'] = imagens_geradas
        
        if chave in st.session_state.get('progresso_leituras', {}):
            st.session_state['progresso_leituras'][chave]['imagens'] = True
            
        st.success("✅ Todas as imagens foram geradas!")
        st.rerun()

st.divider()

# --- Galeria de Resultados ---
if 'imagens_geradas' in st.session_state:
    st.subheader("🖼️ Galeria Gerada")
    imgs = st.session_state['imagens_geradas']
    
    c1, c2, c3, c4, c5 = st.columns(5)
    cols = [c1, c2, c3, c4, c5]
    
    for i, bloco in enumerate(blocos):
        with cols[i]:
            st.markdown(f"**{bloco.capitalize()}**")
            st.image(imgs[bloco], use_container_width=True)

    if st.button("🔊 Ir para Estúdio de Áudio", use_container_width=True):
        st.switch_page("pages/3_Audio_TTS.py")
