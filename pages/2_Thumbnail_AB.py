import os
import io
import uuid
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(page_title="2 – Thumbnails e Imagens", layout="wide")
st.title("🖼 2 – Gerador de Imagens do Vídeo (Pollinations)")

# -------------------------------------------------------------------
# Integra com o "banco"
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

if "artefatos" not in video:
    video["artefatos"] = {}

roteiro = video["artefatos"].get("roteiro")
if not roteiro or "image_prompts" not in roteiro:
    st.warning(
        "Este vídeo ainda não tem prompts de imagem salvos no roteiro "
        "(página 1). Gere o roteiro longo primeiro."
    )
    st.stop()

image_prompts = roteiro["image_prompts"]  # dict[bloco] -> [prompts]

# Estrutura onde salvaremos os caminhos das imagens
if "imagens_roteiro" not in video["artefatos"]:
    video["artefatos"]["imagens_roteiro"] = {}  # bloco -> lista de dicts {prompt, path}

imagens_roteiro = video["artefatos"]["imagens_roteiro"]

# -------------------------------------------------------------------
# Configurações Pollinations
# -------------------------------------------------------------------
with st.sidebar:
    st.header("📺 Contexto")
    st.markdown(f"**Canal:** {canal.get('nome','')}")
    st.markdown(f"**Vídeo:** {video.get('titulo','')}")

    st.markdown("---")
    st.header("⚙️ Pollinations")

    base_url = st.text_input(
        "Endpoint base",
        value="https://image.pollinations.ai/prompt",
        help="Endpoint público do Pollinations para geração de imagens a partir de prompt.",  # [web:350][web:361]
    )

    modelo_padrao = st.selectbox(
        "Modelo de imagem",
        ["turbo", "flux", "openai"],
        index=0,
        help="O modelo 'turbo' é o padrão ultra-rápido recomendado.",
    )  # [web:348][web:351]

    largura = st.number_input("Largura (px)", value=1280, min_value=512, max_value=2048, step=64)
    altura = st.number_input("Altura (px)", value=720, min_value=512, max_value=2048, step=64)

    st.caption(
        "As imagens são geradas chamando a API do Pollinations a partir dos prompts de cada parágrafo."
    )  # [web:350][web:361]

# -------------------------------------------------------------------
# Função para chamar Pollinations
# -------------------------------------------------------------------
def gerar_imagem_pollinations(prompt: str, model: str, width: int, height: int) -> bytes | None:
    """
    Usa o endpoint público do Pollinations para gerar uma imagem a partir do prompt.
    A API básica permite passar parâmetros via querystring. [web:350]
    """
    if not prompt:
        return None

    params = {
        "model": model,
        "width": width,
        "height": height,
    }
    try:
        # Prompt na URL; Pollinations interpreta automaticamente. [web:350]
        url = f"{base_url}/{requests.utils.quote(prompt)}"
        resp = requests.get(url, params=params, timeout=90)
        if resp.status_code != 200:
            st.error(f"Erro HTTP {resp.status_code} ao gerar imagem.")
            return None
        return resp.content
    except Exception as e:
        st.error(f"Erro ao chamar Pollinations: {e}")
        return None

# -------------------------------------------------------------------
# Listagem de prompts
# -------------------------------------------------------------------
st.subheader("🧾 Prompts de imagem vindos do roteiro")

blocos_ordenados = [
    "hook",
    "introducao",
    "capitulo_1",
    "capitulo_2",
    "capitulo_3",
    "capitulo_4",
    "capitulo_5",
    "conclusao",
]
labels = {
    "hook": "Hook",
    "introducao": "Introdução com CTA",
    "capitulo_1": "Capítulo 1",
    "capitulo_2": "Capítulo 2",
    "capitulo_3": "Capítulo 3",
    "capitulo_4": "Capítulo 4",
    "capitulo_5": "Capítulo 5",
    "conclusao": "Conclusão",
}

total_prompts = sum(len(image_prompts.get(b, []) or []) for b in blocos_ordenados)
st.write(f"Total de prompts de imagem detectados neste vídeo: **{total_prompts}**")

tabs = st.tabs([labels.get(b, b) for b in blocos_ordenados])

for bloco, tab in zip(blocos_ordenados, tabs):
    prompts = image_prompts.get(bloco, []) or []
    with tab:
        if not prompts:
            st.info("Nenhum prompt de imagem para este bloco.")
        else:
            for i, p in enumerate(prompts):
                st.markdown(f"**Parágrafo {i+1} – Prompt:**")
                st.code(p or "(vazio)", language="text")

# -------------------------------------------------------------------
# Geração de imagens
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("🖼 Geração de imagens com Pollinations")

col_g1, col_g2 = st.columns(2)

with col_g1:
    if st.button("🚀 Gerar TODAS as imagens em sequência (modelo turbo)"):
        if total_prompts == 0:
            st.warning("Nenhum prompt encontrado no roteiro.")
        else:
            with st.spinner("Gerando todas as imagens com Pollinations..."):
                geradas = 0
                for bloco in blocos_ordenados:
                    prompts = image_prompts.get(bloco, []) or []
                    if bloco not in imagens_roteiro:
                        imagens_roteiro[bloco] = []

                    # Garante lista de mesmo tamanho
                    if len(imagens_roteiro[bloco]) < len(prompts):
                        imagens_roteiro[bloco] += [
                            None
                        ] * (len(prompts) - len(imagens_roteiro[bloco]))

                    for idx, prompt in enumerate(prompts):
                        if not prompt:
                            continue

                        # Se já existe imagem para esse índice, pula
                        entrada_existente = imagens_roteiro[bloco][idx]
                        if entrada_existente and entrada_existente.get("path"):
                            continue

                        conteudo = gerar_imagem_pollinations(
                            prompt=prompt,
                            model=modelo_padrao or "turbo",
                            width=largura,
                            height=altura,
                        )
                        if conteudo:
                            nome_arquivo = f"img_{video_id}_{bloco}_{idx}_{uuid.uuid4().hex[:6]}.png"
                            pasta = "imagens_video"
                            os.makedirs(pasta, exist_ok=True)
                            caminho = os.path.join(pasta, nome_arquivo)
                            with open(caminho, "wb") as f:
                                f.write(conteudo)

                            imagens_roteiro[bloco][idx] = {
                                "prompt": prompt,
                                "path": caminho,
                                "modelo": modelo_padrao,
                                "width": largura,
                                "height": altura,
                                "gerado_em": datetime.now().isoformat(),
                            }
                            geradas += 1

                video["artefatos"]["imagens_roteiro"] = imagens_roteiro
                video["status"]["2_thumbnails"] = True
                video["ultima_atualizacao"] = datetime.now().isoformat()
                st.success(f"Imagens geradas/salvas: {geradas}")

with col_g2:
    if st.button("🗑 Limpar todas as imagens geradas"):
        video["artefatos"]["imagens_roteiro"] = {}
        video["status"]["2_thumbnails"] = False
        video["ultima_atualizacao"] = datetime.now().isoformat()
        st.success("Todas as imagens deste vídeo foram desvinculadas (arquivos no disco permanecem).")

# -------------------------------------------------------------------
# Visualização das imagens salvas
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("🖼 Imagens já geradas")

imagens_roteiro = video["artefatos"].get("imagens_roteiro", {}) or {}

if not imagens_roteiro:
    st.info("Nenhuma imagem gerada ainda. Use o botão acima para gerar todas.")
else:
    for bloco in blocos_ordenados:
        lista = imagens_roteiro.get(bloco, []) or []
        if not lista:
            continue

        st.markdown(f"### {labels.get(bloco, bloco)}")
        cols = st.columns(3)
        col_idx = 0
        for idx, item in enumerate(lista):
            if not item or not item.get("path") or not os.path.exists(item["path"]):
                continue
            with cols[col_idx]:
                st.image(item["path"], caption=f"{bloco} – parágrafo {idx+1}")
                st.caption(f"Modelo: {item.get('modelo','-')}")
            col_idx = (col_idx + 1) % len(cols)

st.markdown("---")
st.caption(
    "Estas imagens são geradas a partir dos prompts de cada parágrafo do roteiro. "
    "Use-as como thumbnails, cenas de vídeo ou material de apoio na edição."
)
