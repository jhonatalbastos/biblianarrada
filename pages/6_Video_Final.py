import streamlit as st
import os
import sys
import time
import datetime
import subprocess
import json

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

# Tenta importar ffmpeg-python para verificação (opcional, pois usaremos subprocess para robustez)
try:
    import ffmpeg
except ImportError:
    pass

st.set_page_config(page_title="Renderizar Vídeo (FFmpeg)", page_icon="🎬", layout="wide")
st.session_state['current_page_name'] = 'pages/6_Video_Final.py'

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada. Volte ao Início.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega progresso do banco
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

render_navigation_bar("🎬 Renderização Final (Engine: FFmpeg)")

# ---------------------------------------------------------------------
# 3. FUNÇÕES FFMPEG
# ---------------------------------------------------------------------

def get_audio_duration(audio_path):
    """Obtém a duração do áudio usando ffprobe."""
    try:
        # Comando: ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.wav
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            audio_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Erro ao ler duração do áudio: {e}")
        return None

def criar_arquivo_concat(imagens, duracao_por_imagem, output_txt):
    """Cria um arquivo de texto para o demuxer concat do FFmpeg."""
    with open(output_txt, 'w', encoding='utf-8') as f:
        for img_path in imagens:
            # Caminho seguro para ffmpeg (escape de aspas simples)
            safe_path = img_path.replace("'", "'\\''") 
            f.write(f"file '{safe_path}'\n")
            f.write(f"duration {duracao_por_imagem:.2f}\n")
        # Repete a última imagem para evitar glitch no final se o áudio for um pouco maior
        safe_last = imagens[-1].replace("'", "'\\''")
        f.write(f"file '{safe_last}'\n")

def gerar_video_ffmpeg(imagens, audio_path, output_video, status_container):
    """Renderiza o vídeo final usando FFmpeg via subprocess."""
    
    if not imagens or not audio_path:
        return False, "Assets faltando."

    # 1. Analisa Áudio
    status_container.write("🎵 Analisando duração do áudio...")
    duracao_audio = get_audio_duration(audio_path)
    if not duracao_audio:
        return False, "Não foi possível ler o arquivo de áudio."
    
    # 2. Calcula tempos
    qtd_imgs = len(imagens)
    tempo_por_img = duracao_audio / qtd_imgs
    status_container.write(f"⏱️ Duração: {duracao_audio:.1f}s | {qtd_imgs} Imagens ({tempo_por_img:.1f}s cada)")

    # 3. Cria lista de concatenação (Slideshow)
    concat_txt = os.path.join(parent_dir, "temp_concat.txt")
    criar_arquivo_concat(imagens, tempo_por_img, concat_txt)
    
    # 4. Comando FFmpeg
    # -f concat -safe 0 -i lista.txt : Input de imagens
    # -i audio.wav : Input de áudio
    # -c:v libx264 : Codec de vídeo leve e compatível
    # -pix_fmt yuv420p : Garante compatibilidade com QuickTime/Windows
    # -shortest : Encerra o vídeo quando o menor input (áudio ou vídeo) acabar
    
    cmd = [
        "ffmpeg", "-y",                # Sobrescrever
        "-f", "concat",                # Formato concat
        "-safe", "0",                  # Permitir caminhos absolutos
        "-i", concat_txt,              # Lista de imagens
        "-i", audio_path,              # Áudio
        "-c:v", "libx264",             # Codec vídeo
        "-r", "30",                    # 30 fps
        "-pix_fmt", "yuv420p",         # Pixel format padrão
        "-shortest",                   # Cortar no final do áudio
        output_video
    ]
    
    status_container.write("⚙️ Iniciando renderização FFmpeg...")
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Limpa arquivo temporário
        if os.path.exists(concat_txt):
            os.remove(concat_txt)
            
        if process.returncode == 0:
            return True, "Sucesso"
        else:
            return False, f"Erro FFmpeg: {process.stderr}"
            
    except Exception as e:
        return False, str(e)

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------

# Checagem de Assets
tem_roteiro = progresso.get('roteiro') or progresso.get('texto_roteiro_completo')
tem_imagens = progresso.get('imagens') 
tem_audio = progresso.get('audio')
tem_overlay = progresso.get('overlay')
tem_legendas = progresso.get('legendas')

# Exibe status
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.markdown(f"{'✅' if tem_roteiro else '❌'} **Roteiro**")
    st.markdown(f"{'✅' if tem_imagens else '❌'} **Imagens**")
with col_s2:
    st.markdown(f"{'✅' if tem_audio else '❌'} **Áudio**")
    st.markdown(f"{'✅' if tem_overlay else '⚠️'} **Overlay**")
with col_s3:
    st.markdown(f"{'✅' if tem_legendas else '⚠️'} **Legendas**")

st.divider()

if not (tem_imagens and tem_audio):
    st.error("❌ Impossível renderizar: Faltam Imagens ou Áudio.")
    st.stop()

col_render, col_result = st.columns([1, 1])

with col_render:
    st.subheader("🚀 Gerar Vídeo")
    st.info("Usando motor FFmpeg (Rápido & Compatível)")
    
    if st.button("Renderizar Vídeo MP4", type="primary"):
        box = st.status("Iniciando processo...", expanded=True)
        
        # Coleta caminhos
        lista_imagens = progresso.get('imagens_paths', [])
        path_audio = progresso.get('audio_path', '')
        
        # Validação extra de arquivos
        arquivos_ok = True
        if not os.path.exists(path_audio):
            box.error(f"Arquivo de áudio não encontrado: {path_audio}")
            arquivos_ok = False
        
        for img in lista_imagens:
            if not os.path.exists(img):
                box.error(f"Imagem não encontrada: {img}")
                arquivos_ok = False
                
        if arquivos_ok:
            # Define saída
            folder_video = os.path.join(parent_dir, "data", "videos")
            os.makedirs(folder_video, exist_ok=True)
            video_filename = f"video_{data_str}_{leitura['tipo'].replace(' ', '_')}.mp4"
            output_path = os.path.join(folder_video, video_filename)
            
            # Chama função de renderização
            sucesso, msg = gerar_video_ffmpeg(lista_imagens, path_audio, output_path, box)
            
            if sucesso:
                progresso['video'] = True
                progresso['video_path'] = output_path
                db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 6)
                
                box.update(label="✅ Vídeo Renderizado com Sucesso!", state="complete", expanded=False)
                st.rerun()
            else:
                box.update(label="❌ Erro na renderização", state="error")
                st.error(msg)
        else:
             box.update(label="❌ Arquivos perdidos", state="error")

with col_result:
    if progresso.get('video') and progresso.get('video_path'):
        video_file = progresso['video_path']
        
        st.subheader("📺 Resultado")
        
        if os.path.exists(video_file):
            st.video(video_file)
            
            with open(video_file, 'rb') as f:
                st.download_button(
                    label="📥 Baixar Vídeo MP4",
                    data=f,
                    file_name=os.path.basename(video_file),
                    mime="video/mp4"
                )
            
            st.divider()
            if st.button("🚀 Ir para Publicação"):
                st.switch_page("pages/7_Publicar.py")
        else:
            st.error("O arquivo de vídeo consta no banco mas não está no disco.")
