import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="6 – Dashboard de Resultados", layout="wide")
st.title("📊 6 – Dashboard de Resultados dos Vídeos")

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

if not canal_id or canal_id not in db["canais"]:
    st.error("Nenhum canal selecionado. Vá ao app principal (monitor) e escolha um canal.")
    st.stop()

canal = db["canais"][canal_id]
videos = canal["videos"]

# -------------------------------------------------------------------
# Sidebar – seleção de vídeo e modo de visualização
# -------------------------------------------------------------------
with st.sidebar:
    st.header("📺 Contexto")
    st.markdown(f"**Canal:** {canal.get('nome','')}")
    st.markdown(f"**Nicho:** {canal.get('nicho','')}")

    st.markdown("---")
    st.header("🎯 Escopo")

    modo = st.radio(
        "O que deseja ver?",
        ["Resumo de todos os vídeos", "Detalhe de um vídeo"],
        index=0,
    )

    video_id = None
    if modo == "Detalhe de um vídeo" and videos:
        vids_ids = list(videos.keys())
        vids_titulos = [videos[vid]["titulo"] for vid in vids_ids]
        idx_video = st.selectbox(
            "Vídeo",
            options=range(len(vids_ids)),
            format_func=lambda i: vids_titulos[i],
            index=0,
        )
        video_id = vids_ids[idx_video]
        st.session_state.video_atual_id = video_id

# -------------------------------------------------------------------
# Helper – montar DataFrame com informações de publicação
# -------------------------------------------------------------------
def montar_df_videos(canal_obj):
    linhas = []
    for vid, v in canal_obj["videos"].items():
        pub_info = v["artefatos"].get("publicacao_info", {}) if v.get("artefatos") else {}
        url = v["artefatos"].get("youtube_url") if v.get("artefatos") else None

        linhas.append(
            {
                "video_id": vid,
                "Título": v.get("titulo", ""),
                "Publicado?": "Sim" if v["status"].get("5_publicacao") else "Não",
                "URL YouTube": url or "",
                "Privacidade": pub_info.get("privacy", "-"),
                "Data publicação": pub_info.get("published_at", "")[:16],
                "Criado no sistema": v.get("criado_em", "")[:16],
                # Campos para futuras métricas (manual ou API)
                "Views (manual)": pub_info.get("manual_views", None),
                "CTR (manual)": pub_info.get("manual_ctr", None),
                "Watch time (min, manual)": pub_info.get("manual_watch_time", None),
            }
        )
    if not linhas:
        return pd.DataFrame()
    return pd.DataFrame(linhas)

# -------------------------------------------------------------------
# Modo 1 – Resumo de todos os vídeos
# -------------------------------------------------------------------
if modo == "Resumo de todos os vídeos":
    st.subheader("📚 Visão geral dos vídeos do canal")

    df = montar_df_videos(canal)
    if df.empty:
        st.info("Ainda não há vídeos cadastrados para este canal.")
        st.stop()

    # KPIs simples
    total_videos = len(df)
    publicados = (df["Publicado?"] == "Sim").sum()
    nao_pub = total_videos - publicados

    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.metric("Vídeos no sistema", total_videos)
    with col_k2:
        st.metric("Vídeos publicados", publicados)
    with col_k3:
        st.metric("A publicar", nao_pub)

    st.markdown("### 📋 Tabela de vídeos")
    st.dataframe(
        df[["Título", "Publicado?", "Privacidade", "Data publicação", "URL YouTube"]],
        use_container_width=True,
        height=260,
    )

    st.markdown("---")
    st.subheader("📈 Espaço para métricas manuais (views, CTR, watch time)")

    st.caption(
        "Por enquanto, este dashboard usa apenas dados manuais. "
        "Você pode copiar números do YouTube Studio e registrar abaixo; "
        "depois isso pode ser automatizado via YouTube Analytics API."
    )

    # Formulário para atualizar métricas manuais de um vídeo específico
    vids_ids = df["video_id"].tolist()
    vids_titulos = df["Título"].tolist()
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        idx_ed = st.selectbox(
            "Escolha o vídeo para atualizar métricas manuais",
            options=range(len(vids_ids)),
            format_func=lambda i: vids_titulos[i],
        )
        vid_sel = vids_ids[idx_ed]
        v_obj = canal["videos"][vid_sel]
        pub_info = v_obj["artefatos"].get("publicacao_info", {})

    with col_f2:
        views_manual = st.number_input(
            "Views (manual, do YouTube Studio)",
            min_value=0,
            value=int(pub_info.get("manual_views", 0) or 0),
        )
        ctr_manual = st.number_input(
            "CTR (%) manual",
            min_value=0.0,
            max_value=100.0,
            value=float(pub_info.get("manual_ctr", 0.0) or 0.0),
            step=0.1,
        )
        wt_manual = st.number_input(
            "Watch time (minutos, manual)",
            min_value=0.0,
            value=float(pub_info.get("manual_watch_time", 0.0) or 0.0),
            step=1.0,
        )

    if st.button("💾 Salvar métricas manuais"):
        if "publicacao_info" not in v_obj["artefatos"]:
            v_obj["artefatos"]["publicacao_info"] = {}
        v_obj["artefatos"]["publicacao_info"].update(
            {
                "manual_views": views_manual,
                "manual_ctr": ctr_manual,
                "manual_watch_time": wt_manual,
                "manual_atualizado_em": datetime.now().isoformat(),
            }
        )
        v_obj["ultima_atualizacao"] = datetime.now().isoformat()
        st.success("Métricas manuais salvas para este vídeo.")
        st.experimental_rerun()

    st.markdown("---")
    st.caption(
        "No futuro, esta aba poderá puxar métricas automaticamente da "
        "YouTube Analytics API (views, watch time, CTR, etc.) e gerar gráficos "
        "mais avançados. Por enquanto, serve como diário de resultados."
    )

# -------------------------------------------------------------------
# Modo 2 – Detalhe de um vídeo
# -------------------------------------------------------------------
else:
    if not video_id or video_id not in videos:
        st.warning("Selecione um vídeo na barra lateral.")
        st.stop()

    v = videos[video_id]
    pub_info = v["artefatos"].get("publicacao_info", {})
    youtube_url = v["artefatos"].get("youtube_url")

    st.subheader("🎬 Detalhes do vídeo")

    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.markdown(f"### {v.get('titulo','(sem título)')}")
        st.caption(v.get("descricao", ""))

        if youtube_url:
            st.markdown(f"[🔗 Abrir no YouTube]({youtube_url})")
        else:
            st.caption("Nenhum link de YouTube registrado ainda.")

    with col_v2:
        st.metric(
            "Publicado?",
            "Sim ✅" if v["status"].get("5_publicacao") else "Não",
        )
        st.metric(
            "Canal pronto?",
            "Sim ✅" if v["status"].get("0_canal") else "Não",
        )

    st.markdown("---")

    # Linha do tempo das etapas
    st.subheader("🧩 Linha do tempo das etapas")

    etapas = [
        ("0_canal", "Canal pronto"),
        ("1_roteiro", "Roteiro"),
        ("2_thumbnail", "Thumbnails"),
        ("3_audio", "Áudio"),
        ("4_video", "Vídeo final"),
        ("5_publicacao", "Publicação"),
        ("6_dashboard", "Dashboard"),
    ]

    cols = st.columns(len(etapas))
    for (key, nome), c in zip(etapas, cols):
        with c:
            status = v["status"].get(key, False)
            icone = "✅" if status else "⭕"
            st.markdown(f"{icone}\n\n{nome}")

    st.markdown("---")

    # Métricas manuais específicas
    st.subheader("📈 Métricas manuais (preenchidas a partir do YouTube Studio)")

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Views (manual)", int(pub_info.get("manual_views", 0) or 0))
    with col_m2:
        st.metric("CTR (%) manual", f"{float(pub_info.get('manual_ctr', 0.0) or 0.0):.1f}%")
    with col_m3:
        st.metric(
            "Watch time (min)",
            int(float(pub_info.get("manual_watch_time", 0.0) or 0.0)),
        )

    if pub_info.get("manual_atualizado_em"):
        st.caption(f"Última atualização manual: {pub_info['manual_atualizado_em'][:16]}")

    st.markdown("---")

    st.caption(
        "Por enquanto, este dashboard é baseado em dados manuais e no status interno do pipeline. "
        "Posteriormente, pode ser integrado à YouTube Analytics API para buscar métricas em tempo real."
    )
