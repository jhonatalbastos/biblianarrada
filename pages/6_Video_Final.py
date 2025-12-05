import streamlit as st
import time

st.set_page_config(page_title="Renderizar Vídeo", page_icon="🎬", layout="wide")
st.session_state['current_page_name'] = 'pages/6_Video_Final.py'

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

render_navigation_bar("🎬 Renderização Final do Vídeo")

# --- Checagem de Assets ---
roteiro = st.session_state.get('roteiro_gerado')
imagens = st.session_state.get('imagens_geradas')
audios = st.session_state.get('audios_gerados')
overlay = st.session_state.get('overlay_config')
legenda = st.session_state.get('legenda_config')

falta_asset = False
if not roteiro: falta_asset = True; st.error("❌ Roteiro faltando")
if not imagens: falta_asset = True; st.error("❌ Imagens faltando")
if not audios: falta_asset = True; st.error("❌ Áudios faltando")
if not overlay: st.warning("⚠️ Overlay não configurado. Recomendado ir para a etapa Overlay.");
if not legenda: st.warning("⚠️ Legenda não configurada.");

if falta_asset:
    st.stop()

col_render, col_result = st.columns([1, 1])

with col_render:
    st.subheader("Detalhes da Renderização")
    st.write(f"**Blocos:** {len(roteiro)} cenas")
    st.write(f"**Overlay:** {'Ativo' if overlay else 'Inativo'}")
    st.write(f"**Legendas:** {'Ativas' if legenda and legenda['ativar'] else 'Inativas'}")
    
    if st.button("🚀 Renderizar Vídeo Final", type="primary"):
        progress_bar = st.progress(0, text="Iniciando MoviePy (Simulação)...")
        
        etapas = ["Carregando Imagens", "Sincronizando Áudio", "Aplicando Overlay", "Gerando Legendas", "Renderizando MP4"]
        for i, etapa in enumerate(etapas):
            time.sleep(1.0) 
            progress_bar.progress((i + 1) * 20, text=etapa)
        
        st.session_state['video_final_path'] = "video_final_simulado.mp4"
        
        # Atualiza Status
        data_str = st.session_state.get('data_atual_str', '')
        leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
        chave = f"{data_str}-{leitura_tipo}"
        if chave in st.session_state.get('progresso_leituras', {}):
            st.session_state['progresso_leituras'][chave]['video'] = True
            
        st.success("Vídeo Renderizado com Sucesso!")
        st.rerun()

with col_result:
    if 'video_final_path' in st.session_state:
        st.subheader("📺 Resultado")
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.video("https://www.w3schools.com/html/mov_bbb.mp4")
            st.caption("Preview (Tamanho Controlado)")
            
            st.download_button("📥 Baixar Vídeo MP4", data="fake content", file_name="video_final.mp4", use_container_width=True)
            
            if st.button("🚀 Ir para Publicação", use_container_width=True):
                st.switch_page("pages/7_Publicar.py")
