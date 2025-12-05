import streamlit as st
from datetime import datetime
import os

st.set_page_config(page_title="5 – Publicar / Upload", layout="wide")
st.title("📤 5 – Publicação do Vídeo (YouTube manual / API futura)")

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

# Garante campos de artefatos
if "youtube_url" not in video["artefatos"]:
    video["artefatos"]["youtube_url"] = None
if "publicacao_info" not in video["artefatos"]:
    video["artefatos"]["publicacao_info"] = {}

roteiro = video["artefatos"].get("roteiro")
video_path = video["artefatos"].get("video_path")

# -------------------------------------------------------------------
# Sidebar – contexto e passo a passo
# -------------------------------------------------------------------
with st.sidebar:
    st.header("📺 Contexto")
    st.markdown(f"**Canal:** {canal.get('nome','')}")
    st.markdown(f"**Vídeo:** {video.get('titulo','')}")

    st.markdown("---")
    st.header("🎯 Objetivo desta etapa")

    st.markdown(
        "- Revisar **título, descrição e tags** gerados na etapa 1.\n"
        "- Baixar o MP4 final (etapa 4).\n"
        "- Publicar manualmente no YouTube Studio.\n"
        "- Registrar o **link do vídeo** e marcar esta etapa como concluída.\n\n"
        "_Integração automática com API YouTube pode ser adicionada depois "
        "(usando `videos.insert` da YouTube Data API)._"
    )

# -------------------------------------------------------------------
# 1. Dados recomendados para publicar (do roteiro)
# -------------------------------------------------------------------
st.subheader("📝 Metadados recomendados (a partir do roteiro)")

titulo_sug = roteiro.get("titulo_video") if isinstance(roteiro, dict) else video.get("titulo")
desc_sug = roteiro.get("descricao") if isinstance(roteiro, dict) else ""
tags_sug = roteiro.get("tags") if isinstance(roteiro, dict) else []

col_m1, col_m2 = st.columns(2)
with col_m1:
    titulo_pub = st.text_input(
        "Título para publicação",
        value=titulo_sug or video.get("titulo", ""),
    )
    tags_str = ", ".join(tags_sug) if tags_sug else ""
    tags_pub = st.text_input(
        "Tags (separadas por vírgula)",
        value=tags_str,
    )
with col_m2:
    desc_pub = st.text_area(
        "Descrição para YouTube",
        value=desc_sug,
        height=120,
    )

st.markdown(
    "_Dica: copie esses campos direto para o YouTube Studio quando for fazer o upload._"
)

# -------------------------------------------------------------------
# 2. Download do vídeo final para upload manual
# -------------------------------------------------------------------
st.subheader("📥 Vídeo final para upload")

if video_path and os.path.exists(video_path):
    st.video(video_path)

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        with open(video_path, "rb") as f:
            st.download_button(
                "💾 Baixar MP4 para enviar no YouTube",
                data=f.read(),
                file_name=f"video_{video.get('titulo','video')[:20]}.mp4",
                mime="video/mp4",
            )
    with col_v2:
        info = video["artefatos"].get("video_info", {})
        st.markdown("**Configurações do vídeo:**")
        st.caption(
            f"Resolução: {info.get('resolucao','-')}  \n"
            f"FPS: {info.get('fps','-')}  \n"
            f"Imagem origem: {info.get('imagem_origem','-')}  \n"
            f"Gerado em: {info.get('gerado_em','')[:16]}"
        )
else:
    st.warning(
        "Nenhum vídeo final encontrado para este vídeo. Gere o vídeo na etapa 4 antes de publicar."
    )

st.markdown("---")

# -------------------------------------------------------------------
# 3. Registro da publicação (manual) + status
# -------------------------------------------------------------------
st.subheader("🔗 Registro da publicação no YouTube")

youtube_url_atual = video["artefatos"].get("youtube_url") or ""
youtube_url_input = st.text_input(
    "Cole aqui o link do vídeo publicado no YouTube (quando já estiver no ar)",
    value=youtube_url_atual,
    placeholder="https://www.youtube.com/watch?v=xxxxxxxxxxx",
)

privacidade = st.selectbox(
    "Status de privacidade no YouTube",
    ["public", "unlisted", "private"],
    index=["public", "unlisted", "private"].index(
        video["artefatos"]["publicacao_info"].get("privacy", "public")
        if video["artefatos"].get("publicacao_info")
        else "public"
    ),
)

data_pub = st.date_input(
    "Data de publicação (real ou planejada)",
    value=datetime.now().date(),
)

hora_pub = st.time_input(
    "Horário de publicação (opcional)",
    value=datetime.now().time().replace(second=0, microsecond=0),
)

col_p1, col_p2 = st.columns(2)
with col_p1:
    if st.button("✅ Marcar como publicado (manual)"):
        if not youtube_url_input.strip():
            st.warning("Cole o link do vídeo no YouTube para marcar como publicado.")
        else:
            video["artefatos"]["youtube_url"] = youtube_url_input.strip()
            video["artefatos"]["publicacao_info"] = {
                "title": titulo_pub,
                "description": desc_pub,
                "tags": [t.strip() for t in tags_pub.split(",") if t.strip()],
                "privacy": privacidade,
                "published_at": datetime.combine(data_pub, hora_pub).isoformat(),
                "registrado_em": datetime.now().isoformat(),
                "modo": "manual",
            }
            video["status"]["5_publicacao"] = True
            video["ultima_atualizacao"] = datetime.now().isoformat()
            st.success("Publicação registrada e etapa 5 marcada como concluída.")

with col_p2:
    if st.button("🗑 Limpar informação de publicação"):
        video["artefatos"]["youtube_url"] = None
        video["artefatos"]["publicacao_info"] = {}
        video["status"]["5_publicacao"] = False
        video["ultima_atualizacao"] = datetime.now().isoformat()
        st.success("Informações de publicação removidas deste vídeo.")

st.markdown("---")

# -------------------------------------------------------------------
# 4. Resumo da publicação
# -------------------------------------------------------------------
st.subheader("📊 Resumo atual de publicação")

if video["artefatos"].get("youtube_url"):
    info = video["artefatos"].get("publicacao_info", {})
    st.success(f"Vídeo publicado em: {video['artefatos']['youtube_url']}")
    st.caption(
        f"Privacidade: {info.get('privacy','-')}  \n"
        f"Publicado em: {info.get('published_at','')[:16]}  \n"
        f"Registrado no sistema em: {info.get('registrado_em','')[:16]}"
    )
else:
    st.info(
        "Nenhum link de publicação registrado ainda. "
        "Depois que o vídeo estiver no YouTube, cole o link acima e marque como publicado."
    )

st.markdown("---")
st.caption(
    "No futuro, esta página pode ser expandida para upload automático via YouTube Data API "
    "(método `videos.insert`) com OAuth2, caso você queira automatizar este passo."
)
