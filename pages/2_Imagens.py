import streamlit as st
import time

st.set_page_config(page_title="Gerar Imagens", page_icon="🎨", layout="wide")

if 'roteiro_gerado' not in st.session_state:
    st.error("Roteiro não encontrado. Gere o roteiro primeiro.")
    if st.button("Voltar"): st.switch_page("pages/1_Roteiro_Viral.py")
    st.stop()

roteiro = st.session_state['roteiro_gerado']
blocos = ["hook", "leitura", "reflexao", "aplicacao", "oracao"]

st.title("🎨 Estúdio de Criação de Imagens")
st.caption("Geração de Prompts e Imagens via IA para cada bloco do roteiro.")

# --- Configuração ---
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
        
        total_steps = len(blocos)
        for i, bloco in enumerate(blocos):
            # 1. Gerar Prompt (Simulação)
            status_text.markdown(f"**Etapa {i+1}/{total_steps}:** Criando Prompt para *{bloco.upper()}*...")
            time.sleep(0.5) 
            prompt_ia = f"Prompt para {estilo}: Uma cena representando {roteiro[bloco][:30]}..."
            
            # 2. Gerar Imagem (Simulação)
            status_text.markdown(f"**Etapa {i+1}/{total_steps}:** Renderizando imagem ({estilo})...")
            time.sleep(1.5) # Simula tempo de API de imagem
            
            # Salva url ou placeholder
            imagens_geradas[bloco] = f"https://placehold.co/600x400?text={bloco.upper()}+{estilo.replace(' ', '+')}"
            
            prog = (i + 1) / total_steps
            prog_bar.progress(prog, text=f"Progresso: {int(prog*100)}%")

        st.session_state['imagens_geradas'] = imagens_geradas
        
        # Atualiza Status Global
        leitura = st.session_state.get('leitura_atual', {})
        data_str = st.session_state.get('data_atual_str', '')
        chave = f"{data_str}-{leitura.get('tipo', '')}"
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
            st.caption(f"Prompt IA: ... (Oculto)")

    st.button("🔊 Ir para Estúdio de Áudio", on_click=lambda: st.switch_page("pages/3_Audio_TTS.py"), use_container_width=True)
