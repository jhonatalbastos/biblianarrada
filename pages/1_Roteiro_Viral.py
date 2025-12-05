import streamlit as st
import time

st.set_page_config(page_title="Gerar Roteiro", page_icon="📝", layout="wide")
st.session_state['current_page_name'] = 'pages/1_Roteiro_Viral.py'

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
    st.warning("Nenhuma leitura selecionada. Volte ao Início.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', '')
chave_progresso = f"{data_str}-{leitura['tipo']}"

render_navigation_bar("📝 Roteiro Viral")

# Layout: Texto Original vs Roteiro Gerado
c1, c2 = st.columns(2)

with c1:
    st.subheader("Texto Bíblico Original")
    with st.container(height=500):
        st.write(leitura['texto'])

with c2:
    st.subheader("Roteiro Viral (5 Blocos)")
    
    # Placeholder para simular IA
    def simular_ia(prompt_type, texto_base):
        time.sleep(0.5) 
        return f"[Conteúdo Gerado por IA para {prompt_type}]\nBaseado em: {texto_base[:50]}..."

    # Formulário para geração
    with st.form("form_roteiro"):
        st.info("A IA irá estruturar o texto em 5 blocos: Hook, Leitura, Reflexão, Aplicação, Oração.")
        submitted = st.form_submit_button("✨ Gerar Roteiro Agora")
    
    if submitted:
        progress = st.progress(0, text="Analisando texto...")
        
        progress.progress(20, text="Criando Hook Viral...")
        b1 = simular_ia("Hook + CTA", leitura['texto'])
        
        progress.progress(40, text="Formatando Leitura...")
        b2 = leitura['texto'] 
        
        progress.progress(60, text="Escrevendo Reflexão Teológica...")
        b3 = simular_ia("Reflexão Curta", leitura['texto'])
        
        progress.progress(80, text="Criando Aplicação Prática...")
        b4 = simular_ia("Aplicação Prática", leitura['texto'])
        
        progress.progress(95, text="Finalizando com Oração...")
        b5 = simular_ia("Oração Final", leitura['texto'])
        
        progress.progress(100, text="Concluído!")
        
        st.session_state['roteiro_gerado'] = {
            "hook": b1, "leitura": b2, "reflexao": b3, "aplicacao": b4, "oracao": b5
        }
        
        # Atualizar status no Pipeline
        if 'progresso_leituras' in st.session_state:
             st.session_state['progresso_leituras'][chave_progresso]['roteiro'] = True

        st.rerun()

    # Exibir Roteiro se já existir
    if 'roteiro_gerado' in st.session_state:
        rg = st.session_state['roteiro_gerado']
        
        st.success("Roteiro Gerado com Sucesso! Confirme os textos abaixo.")
        
        st.markdown("**1. Hook + CTA**")
        st.text_area("Bloco 1", rg['hook'], height=100)
        
        st.markdown("**2. Leitura**")
        st.text_area("Bloco 2", rg['leitura'], height=150)
        
        st.markdown("**3. Reflexão**")
        st.text_area("Bloco 3", rg['reflexao'], height=150)
        
        st.markdown("**4. Aplicação**")
        st.text_area("Bloco 4", rg['aplicacao'], height=100)
        
        st.markdown("**5. Oração**")
        st.text_area("Bloco 5", rg['oracao'], height=100)
        
        if st.button("🎨 Prosseguir para Imagens", use_container_width=True):
            st.switch_page("pages/2_Imagens.py")

