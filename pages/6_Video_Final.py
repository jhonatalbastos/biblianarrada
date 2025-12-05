import streamlit as st
import time

st.set_page_config(page_title="Renderizar Vídeo", page_icon="🎬", layout="wide")

if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

st.title("🎬 Renderização Final do Vídeo")
st.markdown("Montagem de todos os assets: Imagens, Áudio, Overlay e Legendas.")

# --- Checagem de Assets ---
roteiro = st.session_state.get('roteiro_gerado')
imagens = st.session_state.get('imagens_geradas')
audios = st.session_state.get('audios_gerados') # Nomes dos arquivos wav
overlay = st.session_state.get('overlay_config')
legenda = st.session_state.get('legenda_config')

falta_asset = False
if not roteiro: st.error("❌ Roteiro faltando"); falta_asset = True
if not imagens: st.error("❌ Imagens faltando"); falta_asset = True
if not audios: st.error("❌ Áudios faltando"); falta_asset = True
if not overlay: st.warning("⚠️ Overlay não configurado (vídeo ficará sem textos topo)");
if not legenda: st.warning("⚠️ Legenda não configurada");

if falta_asset:
    st.stop()

col_render, col_result = st.columns([1, 1])

with col_render:
    st.subheader("Detalhes da Renderização")
    st.write(f"**Blocos:** {len(roteiro)} cenas")
    st.write(f"**Overlay:** {'Ativo' if overlay else 'Inativo'}")
    st.write(f"**Legendas:** {'Ativas' if legenda and legenda['ativar'] else 'Inativas'}")
    
    if st.button("🚀 Renderizar Vídeo Final", type="primary"):
        progress_bar = st.progress(0, text="Iniciando MoviePy...")
        
        # --- Simulação do Processo de Renderização (MoviePy) ---
        # No ambiente real, aqui você usaria:
        # 1. ImageClip(img).set_duration(audio_duration)
        # 2. CompositeVideoClip([img_clip, text_clip_overlay])
        # 3. Concatenate(clips)
        
        etapas = ["Carregando Imagens", "Sincronizando Áudio", "Aplicando Overlay", "Gerando Legendas", "Renderizando MP4"]
        for i, etapa in enumerate(etapas):
            time.sleep(1.5) # Simula processamento pesado
            progress_bar.progress((i + 1) * 20, text=etapa)
        
        # Caminho simulado
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
        
        # Layout centralizado para evitar vídeo gigante
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            # st.video usa largura do container, então as colunas ajudam a reduzir
            st.video("https://www.w3schools.com/html/mov_bbb.mp4") # Placeholder
            st.caption("Preview (Tamanho Reduzido)")
            
            st.download_button("📥 Baixar Vídeo MP4", data="fake content", file_name="video_final.mp4")
            
            if st.button("🚀 Ir para Publicação"):
                st.switch_page("pages/7_Publicar.py")
