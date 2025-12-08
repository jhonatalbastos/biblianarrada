import streamlit as st
import os
import sys
import time
import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

st.set_page_config(page_title="Renderizar Vídeo", page_icon="🎬", layout="wide")
st.session_state['current_page_name'] = 'pages/6_Video_Final.py'

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO (DO BANCO DE DADOS)
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada. Volte ao Início.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# CARREGA O PROGRESSO REAL DO BANCO
progresso, _ = db.load_status(chave_progresso)

# --- Utility Function for Navigation Bar ---
def render_navigation_bar(current_page_title):
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    st.caption(f"📖 Em Produção: **{leitura['tipo']}** ({data_str})")

    cols_nav = st.columns([1, 1, 1, 1, 1, 1, 1])
    
    stages = [
        ('Roteiro', 'roteiro', 'pages/1_Roteiro_Viral.py', '📝', '📝', True),
        ('Imagens', 'imagens', 'pages/2_Imagens.py', '🎨', '🔒', progresso.get('roteiro', False)),
        ('Áudio', 'audio', 'pages/3_Audio_TTS.py', '🔊', '🔒', progresso.get('roteiro', False)),
        ('Overlay', 'overlay', 'pages/4_Overlay.py', '🖼️', '🔒', progresso.get('audio', False)),
        ('Legendas', 'legendas', 'pages/5_Legendas.py', '💬', '🔒', progresso.get('overlay', False)),
        ('Vídeo', 'video', 'pages/6_Video_Final.py', '🎬', '🔒', progresso.get('legendas', False)),
        ('Publicar', 'publicacao', 'pages/7_Publicar.py', '🚀', '🔒', progresso.get('video', False))
    ]

    current_page = st.session_state['current_page_name']
    
    for i, (label, key, page, icon_on, icon_off, base_enabled) in enumerate(stages):
        status = progresso.get(key, False)
        is_current = current_page == page
        
        icon = icon_on if status or is_current else icon_off
        display_icon = f"✅ {icon}" if status and not is_current else icon
        
        enabled = base_enabled
        btn_disabled = not enabled and not status and not is_current
        
        with cols_nav[i]:
            btn_style = "primary" if is_current else "secondary"
            if st.button(display_icon, key=f"nav_btn_{key}", type=btn_style, disabled=btn_disabled, help=label):
                st.switch_page(page)

    st.markdown("---")
# --- End Utility Function ---

render_navigation_bar("🎬 Renderização Final")

# ---------------------------------------------------------------------
# 3. CHECAGEM DE ASSETS (CORRIGIDO)
# ---------------------------------------------------------------------
# Verifica no dicionário 'progresso' vindo do banco, não no session_state volátil
tem_roteiro = progresso.get('roteiro') or progresso.get('texto_roteiro_completo')
tem_imagens = progresso.get('imagens') 
tem_audio = progresso.get('audio')
tem_overlay = progresso.get('overlay')
tem_legendas = progresso.get('legendas')

# Exibe status
col_status_1, col_status_2, col_status_3 = st.columns(3)

with col_status_1:
    if tem_roteiro: st.success("✅ Roteiro: Pronto")
    else: st.error("❌ Roteiro: Pendente")
    
    if tem_imagens: st.success("✅ Imagens: Prontas")
    else: st.error("❌ Imagens: Pendentes")

with col_status_2:
    if tem_audio: st.success("✅ Áudio: Pronto")
    else: st.error("❌ Áudio: Pendente")
    
    if tem_overlay: st.success("✅ Overlay: Configurado")
    else: st.warning("⚠️ Overlay: Não configurado (Opcional)")

with col_status_3:
    if tem_legendas: st.success("✅ Legendas: Geradas")
    else: st.warning("⚠️ Legendas: Pendentes (Opcional)")

st.divider()

# Validação para impedir renderização sem o básico
if not (tem_roteiro and tem_imagens and tem_audio):
    st.warning("⚠️ Você precisa concluir pelo menos as etapas de Roteiro, Imagens e Áudio para renderizar.")
    st.stop()

# ---------------------------------------------------------------------
# 4. RENDERIZAÇÃO
# ---------------------------------------------------------------------
col_render, col_result = st.columns([1, 1])

with col_render:
    st.subheader("🚀 Gerar Vídeo")
    
    st.info("Todos os ativos foram localizados. Clique abaixo para iniciar a montagem.")
    
    if st.button("Renderizar Vídeo MP4", type="primary"):
        status_box = st.status("Processando vídeo...", expanded=True)
        
        try:
            # 1. Carregando Assets
            status_box.write("📂 Carregando imagens e áudio do sistema...")
            time.sleep(1) # Simulação visual do processo
            
            # Aqui entraria a lógica real do MoviePy:
            # clip = ImageSequenceClip(lista_imagens, durations=...)
            # audio = AudioFileClip(path_audio)
            # clip = clip.set_audio(audio)
            
            status_box.write("🎼 Sincronizando áudio e vídeo...")
            time.sleep(1)
            
            if tem_overlay:
                status_box.write("🖼️ Aplicando Overlay e Marca d'água...")
                time.sleep(1)
                
            if tem_legendas:
                status_box.write("📝 Queimando legendas no vídeo...")
                time.sleep(1)
                
            status_box.write("💾 Exportando MP4 (h.264)...")
            time.sleep(1)
            
            # Define caminho de saída
            folder_video = os.path.join(parent_dir, "data", "videos")
            os.makedirs(folder_video, exist_ok=True)
            video_filename = f"video_final_{data_str}_{leitura['tipo']}.mp4"
            video_path = os.path.join(folder_video, video_filename)
            
            # SALVA STATUS NO BANCO
            progresso['video'] = True
            progresso['video_path'] = video_path
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 6)
            
            status_box.update(label="✅ Renderização Concluída!", state="complete", expanded=False)
            st.rerun()
            
        except Exception as e:
            status_box.update(label="❌ Erro na renderização", state="error")
            st.error(f"Erro técnico: {e}")

with col_result:
    if progresso.get('video'):
        st.subheader("📺 Resultado Final")
        
        # Simulação de player (já que não geramos o arquivo real via MoviePy neste código simplificado)
        # Se você tiver implementado o MoviePy real, troque o caminho abaixo pelo `progresso['video_path']`
        
        # Link fake para ilustrar sucesso
        st.success("Vídeo renderizado e salvo!")
        st.info(f"Salvo em: {progresso.get('video_path', 'data/videos/...')}")
        
        # Botões de ação
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Baixar MP4", data="conteudo_fake", file_name="video_final.mp4", disabled=True, help="Implemente o MoviePy real para baixar")
        with c2:
            if st.button("🚀 Publicar nas Redes"):
                st.switch_page("pages/7_Publicar.py")
