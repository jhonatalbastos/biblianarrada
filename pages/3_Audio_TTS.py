import streamlit as st
import time

st.set_page_config(page_title="Gerar Áudio TTS", page_icon="🔊", layout="wide")
st.session_state['current_page_name'] = 'pages/3_Audio_TTS.py'

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
    st.error("Roteiro não encontrado.")
    st.stop()

roteiro = st.session_state['roteiro_gerado']
blocos = ["hook", "leitura", "reflexao", "aplicacao", "oracao"]

render_navigation_bar("🔊 Estúdio de Narração (Piper TTS)")

# --- Interface ---
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("### Configuração de Voz")
    voz = st.selectbox("Modelo de Voz Piper", ["pt_BR-faber-medium", "pt_BR-edresson-low"])
    velocidade = st.slider("Velocidade da Fala", 0.8, 1.5, 1.0)
    
    st.info("Nota: O Piper TTS deve estar instalado no servidor para funcionar. Aqui simularemos o processo.")

with c2:
    st.markdown("### Processamento em Massa")
    if st.button("🎙️ Gerar Todos os Áudios", type="primary", use_container_width=True):
        
        prog_bar = st.progress(0, text="Inicializando Piper...")
        status = st.empty()
        audios_gerados = {}
        data_str = st.session_state.get('data_atual_str', '')
        leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
        chave = f"{data_str}-{leitura_tipo}"
        
        total = len(blocos)
        
        for i, bloco in enumerate(blocos):
            status.markdown(f"**Processando:** {bloco.upper()}...")
            time.sleep(2) 
            
            audios_gerados[bloco] = f"audio_{bloco}.wav" 
            
            prog = (i + 1) / total
            prog_bar.progress(prog, text=f"Concluído: {int(prog*100)}%")
        
        st.session_state['audios_gerados'] = audios_gerados
        
        if chave in st.session_state.get('progresso_leituras', {}):
            st.session_state['progresso_leituras'][chave]['audio'] = True
            
        st.success("Áudios gerados com sucesso!")
        st.rerun()

st.divider()

if 'audios_gerados' in st.session_state:
    st.subheader("🎧 Resultado Final")
    
    for bloco in blocos:
        with st.container():
            col_txt, col_player = st.columns([3, 2])
            with col_txt:
                st.markdown(f"**{bloco.upper()}**")
                st.caption(roteiro[bloco][:100] + "...")
            with col_player:
                st.warning("Arquivo de áudio simulado (Placeholder).")
    
    if st.button("🖼️ Ir para Configuração de Overlay", use_container_width=True):
        st.switch_page("pages/4_Overlay.py")
