import streamlit as st
import subprocess
import os
import tempfile
from datetime import datetime
from PIL import Image
import io

st.set_page_config(page_title="4 – Vídeo Final", layout="wide")
st.title("🎬 4 – Montagem do Vídeo Final (Imagem + Áudio)")

# -------------------------------------------------------------------
# Integra com o "banco" e seleção do monitor
# -------------------------------------------------------------------
def criar_db_vazio():
    return {"canais": {}}

if "db" not in st.session_state:
    st.session_state.db = criar_db_vazio()
db = st.session_state.db

if "canal_atual_id" not in st.session_state:
    st.session_state.canal_atual_id = None
if "video_atual_id" not in st.session_state:
    st.session_state.video_atual_id = None

canal_id = st.session_state.canal_atual_id
video_id = st.session_state.video_atual_id

if not canal_id or canal_id not in db["canais"]:
    st.error("Nenhum canal selecionado. Vá ao app principal (monitor) e escolha um canal/vídeo.")
    st.stop()

canal = db["canais"][canal_id]
videos = canal["videos"]
if not video_id or video_id not in videos:
    st.error("Nenhum vídeo selecionado. Vá ao monitor e escolha um vídeo para este canal.")
    st.stop()

video = videos[video_id]

# Garante estrutura de artefatos
if "video_path" not in video["artefatos"]:
    video["artefatos"]["video_path"] = None
if "video_info" not in video["artefatos"]:
    video["artefatos"]["video_info"] = {}

thumbs = video["artefatos"].get("thumbs", {})
audio_path = video["artefatos"].get("audio_path")

# -------------------------------------------------------------------
# Sidebar – contexto e opções de render
# -------------------------------------------------------------------
with st.sidebar:
    st.header("📺 Contexto")
    st.markdown(f"**Canal:** {canal.get('nome','')}")
    st.markdown(f"**Vídeo:** {video.get('titulo','')}")

    st.markdown("---")
    st.header("🎞 Fonte de imagem")

    thumb_vencedora = thumbs.get("vencedor")
    opcoes_img = []

    # Thumbnails salvas
    if isinstance(thumbs.get("img_a"), Image.Image):
        opcoes_img.append("Thumbnail A")
    if isinstance(thumbs.get("img_b"), Image.Image):
        opcoes_img.append("Thumbnail B")
    if isinstance(thumbs.get("img_c"), Image.Image):
        opcoes_img.append("Thumbnail C")

    opcoes_img.append("Upload manual")

    escolha_img = st.selectbox(
        "Imagem de fundo do vídeo",
        opcoes_img,
        index=opcoes_img.index(f"Thumbnail {thumb_vencedora}") if thumb_vencedora and f"Thumbnail {thumb_vencedora}" in opcoes_img else 0,
    )

    st.markdown("---")
    st.header("📐 Resolução e duração")

    resolucao = st.selectbox(
        "Resolução",
        ["1280x720 (HD)", "1920x1080 (Full HD)"],
        index=0,
    )

    fps = st.slider("FPS do vídeo", 24, 60, 30, 2)

    st.caption(
        "A duração final será automaticamente igual à duração do áudio, "
        "usando FFmpeg com -shortest."
    )

# -------------------------------------------------------------------
# Escolha/obtenção da imagem
# -------------------------------------------------------------------
st.subheader("🖼 Pré-visualização da imagem de fundo")

img_fundo = None

if escolha_img.startswith("Thumbnail"):
    qual = escolha_img.split()[-1]  # A/B/C
    chave = f"img_{qual.lower()}"
    img_fundo = thumbs.get(chave)

    if isinstance(img_fundo, Image.Image):
        st.image(img_fundo, caption=f"Usando {escolha_img} como fundo", width=400)
    else:
        st.warning(f"{escolha_img} não encontrada. Selecione outra opção ou gere thumbnails na etapa 2.")
elif escolha_img == "Upload manual":
    file_img = st.file_uploader("Envie uma imagem (JPG/PNG)", type=["jpg", "jpeg", "png"])
    if file_img is not None:
        img_fundo = Image.open(file_img)
        st.image(img_fundo, caption="Imagem enviada", width=400)

# -------------------------------------------------------------------
# Verificação do áudio
# -------------------------------------------------------------------
st.subheader("🎧 Áudio disponível")

if audio_path and os.path.exists(audio_path):
    st.audio(audio_path, format="audio/mpeg")
    st.caption("Áudio carregado da etapa 3 (TTS).")
else:
    st.error("Nenhum áudio encontrado para este vídeo. Gere o áudio na etapa 3 antes de montar o vídeo.")
    st.stop()

# -------------------------------------------------------------------
# Função para salvar imagem temporária
# -------------------------------------------------------------------
def salvar_imagem_temp(imagem: Image.Image, resolucao_str: str) -> str | None:
    import tempfile

    if not isinstance(imagem, Image.Image):
        return None

    w, h = [int(x) for x in resolucao_str.split("x")]
    img_resized = imagem.resize((w, h))

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img_resized.save(tmp, format="PNG")
    tmp.close()
    return tmp.name

# -------------------------------------------------------------------
# Função para chamar FFmpeg simples (imagem estática + áudio -> MP4)
# -------------------------------------------------------------------
def gerar_video_ffmpeg(img_path: str, audio_path: str, resolucao: str, fps: int) -> str | None:
    """
    Usa ffmpeg para combinar uma imagem estática + áudio em um MP4.
    Comando aproximado (linha única):

    ffmpeg -loop 1 -i image.png -i audio.mp3 -c:v libx264 -tune stillimage \
           -c:a aac -b:a 192k -pix_fmt yuv420p -shortest -r 30 output.mp4
    """  # [web:43][web:45]

    import tempfile

    out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    out_path = out.name
    out.close()

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        img_path,
        "-i",
        audio_path,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-shortest",
        out_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            st.error("Erro ao executar FFmpeg.")
            st.code(result.stderr[-2000:], language="bash")
            return None
        return out_path
    except FileNotFoundError:
        st.error(
            "FFmpeg não encontrado no ambiente.\n"
            "Certifique-se de que o binário 'ffmpeg' está instalado e no PATH."
        )
        return None

# -------------------------------------------------------------------
# Botão principal de geração de vídeo
# -------------------------------------------------------------------
st.subheader("🎬 Gerar vídeo final")

if not isinstance(img_fundo, Image.Image):
    st.warning("Escolha ou envie uma imagem de fundo antes de gerar o vídeo.")
else:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if st.button("🚀 Gerar vídeo (FFmpeg)", type="primary"):
            with st.spinner("Montando vídeo com FFmpeg..."):
                img_temp = salvar_imagem_temp(img_fundo, resolucao.split()[0])
                if not img_temp:
                    st.error("Falha ao preparar imagem temporária.")
                else:
                    video_path = gerar_video_ffmpeg(
                        img_temp, audio_path, resolucao.split()[0], fps
                    )
                    if video_path and os.path.exists(video_path):
                        video["artefatos"]["video_path"] = video_path
                        video["artefatos"]["video_info"] = {
                            "resolucao": resolucao.split()[0],
                            "fps": fps,
                            "imagem_origem": escolha_img,
                            "audio_origem": audio_path,
                            "gerado_em": datetime.now().isoformat(),
                        }
                        video["status"]["4_video"] = True
                        video["ultima_atualizacao"] = datetime.now().isoformat()
                        st.success("Vídeo gerado e etapa 4 marcada como concluída.")
    with col_g2:
        if st.button("🗑 Remover vídeo gerado"):
            video["artefatos"]["video_path"] = None
            video["artefatos"]["video_info"] = {}
            video["status"]["4_video"] = False
            video["ultima_atualizacao"] = datetime.now().isoformat()
            st.success("Vídeo removido deste vídeo.")

st.markdown("---")

# -------------------------------------------------------------------
# Player e download do vídeo gerado
# -------------------------------------------------------------------
st.subheader("📺 Preview do vídeo gerado")

video_path_salvo = video["artefatos"].get("video_path")
if video_path_salvo and os.path.exists(video_path_salvo):
    st.video(video_path_salvo)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        with open(video_path_salvo, "rb") as f:
            st.download_button(
                "💾 Baixar MP4",
                data=f.read(),
                file_name=f"video_{video.get('titulo','video')[:20]}.mp4",
                mime="video/mp4",
            )
    with col_d2:
        info = video["artefatos"].get("video_info", {})
        st.markdown("**Configurações do vídeo:**")
        st.caption(
            f"Resolução: {info.get('resolucao','-')}  \n"
            f"FPS: {info.get('fps','-')}  \n"
            f"Imagem origem: {info.get('imagem_origem','-')}  \n"
            f"Gerado em: {info.get('gerado_em','')[:16]}"
        )
else:
    st.info("Nenhum vídeo final disponível ainda. Gere o vídeo acima.")

st.markdown("---")
st.caption(
    "Após gerar o vídeo final, volte ao **Monitor de Produção** para seguir "
    "para a etapa 5 (Publicação / Upload)."
)
