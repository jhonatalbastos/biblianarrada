import streamlit as st
import os
import sys
import datetime
import subprocess
import math

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

st.set_page_config(page_title="Renderizar Vídeo (FFmpeg)", page_icon="🎬", layout="wide")
st.session_state['current_page_name'] = 'pages/6_Video_Final.py'

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada. Volte ao Início.")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

progresso, _ = db.load_status(chave_progresso)

# --- Navegação Visual ---
def render_navigation_bar(current_page_title):
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    
    stages = [
        ('Roteiro', 'pages/1_Roteiro_Viral.py'),
        ('Imagens', 'pages/2_Imagens.py'),
        ('Áudio', 'pages/3_Audio_TTS.py'),
        ('Overlay', 'pages/4_Overlay.py'),
        ('Legendas', 'pages/5_Legendas.py'),
        ('Vídeo', 'pages/6_Video_Final.py'),
        ('Publicar', 'pages/7_Publicar.py')
    ]
    
    cols = st.columns(len(stages))
    for i, (label, page) in enumerate(stages):
        with cols[i]:
            if st.session_state['current_page_name'] == page:
                st.button(f"📍 {label}", key=f"nav_{i}", type="primary", disabled=True)
            else:
                if st.button(f"{label}", key=f"nav_{i}"):
                    st.switch_page(page)
    st.markdown("---")

render_navigation_bar("🎬 Renderização Final (Com Legendas)")

# ---------------------------------------------------------------------
# 3. FUNÇÕES UTILITÁRIAS (FFMPEG + SRT)
# ---------------------------------------------------------------------

def format_timestamp(seconds):
    """Converte segundos (float) para formato SRT (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def criar_arquivo_srt(legendas_dados, output_path):
    """Cria um arquivo .srt a partir da lista de dicionários de legendas."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, item in enumerate(legendas_dados):
                start = format_timestamp(item['start'])
                end = format_timestamp(item['end'])
                text = item['text']
                
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        return True
    except Exception as e:
        print(f"Erro ao criar SRT: {e}")
        return False

def get_audio_duration(audio_path):
    """Obtém a duração do áudio usando ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 0.0

def criar_arquivo_concat(imagens, duracao_por_imagem, output_txt):
    """Cria lista de concatenação para o FFmpeg."""
    with open(output_txt, 'w', encoding='utf-8') as f:
        for img_path in imagens:
            # Escape simples para caminhos
            safe_path = img_path.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
            f.write(f"duration {duracao_por_imagem:.2f}\n")
        # Repete a última imagem
        if imagens:
            safe_last = imagens[-1].replace("'", "'\\''")
            f.write(f"file '{safe_last}'\n")

def gerar_video_ffmpeg(imagens, audio_path, output_video, srt_path, status_container):
    """Renderiza vídeo + áudio + legendas (burn-in)."""
    
    # 1. Analisa Áudio
    duracao_audio = get_audio_duration(audio_path)
    if duracao_audio <= 0:
        return False, "Erro ao ler duração do áudio."
    
    qtd_imgs = len(imagens)
    if qtd_imgs == 0:
        return False, "Lista de imagens vazia."
        
    tempo_por_img = duracao_audio / qtd_imgs
    
    # 2. Cria arquivo de concatenação (slideshow)
    concat_txt = os.path.join(parent_dir, "temp_concat.txt")
    criar_arquivo_concat(imagens, tempo_por_img, concat_txt)
    
    # 3. Monta comando FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_txt,  # Input Vídeo
        "-i", audio_path,                                # Input Áudio
    ]

    # Configuração de Filtros (Legendas)
    filtros = []
    
    if srt_path and os.path.exists(srt_path):
        # Transforma caminho para formato aceito pelo FFmpeg
        # No Linux (seu ambiente), caminhos normais funcionam bem.
        # Asseguramos apenas que não haja caracteres estranhos.
        srt_safe = srt_path
        
        # CORREÇÃO DO ERRO: force_style (minúsculo)
        style = "force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=20'"
        
        # Monta o filtro: subtitles='caminho':force_style='...'
        filtros.append(f"subtitles='{srt_safe}':{style}")
    
    # Adiciona filtros se houver
    if filtros:
        cmd.extend(["-vf", ",".join(filtros)])

    # Configurações finais de codec
    cmd.extend([
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_video
    ])
    
    status_container.code(" ".join(cmd)) # Mostra comando para debug
    status_container.write("⚙️ Renderizando com FFmpeg...")
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Limpa temp
        if os.path.exists(concat_txt): os.remove(concat_txt)
        
        if process.returncode == 0:
            return True, "Sucesso"
        else:
            return False, f"Erro FFmpeg: {process.stderr}"
    except Exception as e:
        return False, str(e)

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------

# Verificação de status
tem_img = progresso.get('imagens')
tem_aud = progresso.get('audio')
tem_leg = progresso.get('legendas')
dados_leg = progresso.get('legendas_dados', [])

col1, col2 = st.columns(2)
with col1:
    st.info(f"Imagens: {len(progresso.get('imagens_paths', []))} arquivos")
    st.info(f"Áudio: {'OK' if tem_aud else 'Pendente'}")
with col2:
    st.info(f"Legendas: {'OK' if tem_leg and dados_leg else 'Não configurado'}")

st.divider()

if not (tem_img and tem_aud):
    st.error("Faltam imagens ou áudio.")
    st.stop()

if st.button("🎬 Renderizar Vídeo Final", type="primary"):
    box = st.status("Preparando arquivos...", expanded=True)
    
    # 1. Caminhos
    folder_video = os.path.join(parent_dir, "data", "videos")
    os.makedirs(folder_video, exist_ok=True)
    
    path_audio = progresso.get('audio_path', '')
    path_imgs = progresso.get('imagens_paths', [])
    path_video = os.path.join(folder_video, f"video_{data_str}_{leitura['tipo'].replace(' ', '_')}.mp4")
    
    # 2. Gera SRT temporário se houver legendas
    path_srt = None
    if tem_leg and dados_leg:
        box.write("📝 Criando arquivo de legendas (.srt)...")
        path_srt = os.path.join(folder_video, "temp_subs.srt")
        criar_arquivo_srt(dados_leg, path_srt)
    else:
        box.warning("Sem legendas selecionadas. O vídeo será gerado sem texto.")

    # 3. Renderiza
    sucesso, msg = gerar_video_ffmpeg(path_imgs, path_audio, path_video, path_srt, box)
    
    # 4. Limpeza SRT
    if path_srt and os.path.exists(path_srt):
        os.remove(path_srt)

    if sucesso:
        progresso['video'] = True
        progresso['video_path'] = path_video
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 6)
        
        box.update(label="✅ Vídeo Pronto!", state="complete", expanded=False)
        st.success("Renderização concluída!")
        st.rerun()
    else:
        box.update(label="❌ Falha na renderização", state="error")
        st.error(msg)

# Exibe Resultado
if progresso.get('video') and progresso.get('video_path'):
    path_v = progresso['video_path']
    if os.path.exists(path_v):
        st.subheader("📺 Visualização")
        st.video(path_v)
        with open(path_v, 'rb') as f:
            st.download_button("📥 Baixar Vídeo", f, file_name=os.path.basename(path_v))
        
        if st.button("Ir para Publicação ➡️"):
            st.switch_page("pages/7_Publicar.py")
    else:
        st.warning("Vídeo consta como pronto, mas arquivo não encontrado.")
