import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
import googleapiclient.discovery
import requests

st.set_page_config(page_title="YouTube Automation MVP – Monitor", layout="wide")

# -------------------------------------------------------------------
# Configuração e Banco de Dados em Sessão
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

# -------------------------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------------------------
@st.cache_resource
def get_youtube_service():
    # Tenta pegar dos secrets, senão avisa
    if "YOUTUBE_API_KEY" in st.secrets:
        return googleapiclient.discovery.build(
            "youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"]
        )
    return None

youtube = get_youtube_service()

def gerar_id():
    return str(uuid.uuid4())[:8]

def obter_canal(canal_id):
    return db["canais"].get(canal_id)

def criar_video_com_liturgia(canal_id, dados_liturgia, data_escolhida):
    """
    Cria um novo vídeo no banco de dados preenchido com os dados da liturgia.
    """
    novo_vid_id = gerar_id()
    
    # Monta um texto base combinando as leituras
    texto_combinado = f"""
    LITURGIA DO DIA: {data_escolhida}
    
    PRIMEIRA LEITURA:
    {dados_liturgia.get('primeiraLeitura', 'Não encontrada')}
    
    SALMO:
    {dados_liturgia.get('salmo', 'Não encontrado')}
    
    SEGUNDA LEITURA (se houver):
    {dados_liturgia.get('segundaLeitura', '')}
    
    EVANGELHO:
    {dados_liturgia.get('evangelho', 'Não encontrado')}
    """

    titulo_sug = f"Liturgia de {data_escolhida} - Evangelho do Dia"

    novo_video = {
        "id": novo_vid_id,
        "titulo": titulo_sug,
        "criado_em": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat(),
        "status": {
            "1_roteiro": False,  # Vamos marcar como False para forçar revisão no passo 1
            "2_thumbnail": False,
            "3_audio": False,
            "4_video": False,
            "5_publicacao": False,
        },
        "artefatos": {
            "roteiro": {
                # Injetamos o texto da liturgia como ideia original/base
                "ideia_original": texto_combinado.strip(),
                "roteiro": {},       # Será gerado no passo 1
                "image_prompts": {}, # Será gerado no passo 1
                "titulo_video": titulo_sug
            },
            "imagens_roteiro": {},
            "audio_path": None,
            "video_path": None,
        },
    }
    
    # Salva no canal
    db["canais"][canal_id]["videos"][novo_vid_id] = novo_video
    return novo_vid_id

# -------------------------------------------------------------------
# Sidebar: Seleção de Canal
# -------------------------------------------------------------------
with st.sidebar:
    st.header("📢 Seleção de Canal")
    
    # Input para adicionar canal novo
    novo_canal_url = st.text_input("Cole o link do canal ou Handle (@...)")
    if st.button("Importar/Criar Canal"):
        if not novo_canal_url:
            st.warning("Cole uma URL válida.")
        else:
            # Lógica simplificada de extração (mock) ou via API se disponível
            c_id = gerar_id()
            nome_mock = f"Canal Importado {c_id}"
            
            # Tenta pegar info real se API estiver ativa
            if youtube:
                try:
                    # Lógica simples de busca (apenas exemplo, pode ser aprimorada)
                    res = youtube.search().list(part="snippet", q=novo_canal_url, type="channel").execute()
                    if res["items"]:
                        snippet = res["items"][0]["snippet"]
                        nome_mock = snippet["title"]
                        c_id = snippet["channelId"] # Usa ID real do YouTube se achar
                except Exception as e:
                    st.error(f"Erro na API YouTube: {e}")

            if c_id not in db["canais"]:
                db["canais"][c_id] = {
                    "nome": nome_mock,
                    "url": novo_canal_url,
                    "videos": {},
                    "preferencias_titulo": "" # vindo do lab
                }
                st.success(f"Canal '{nome_mock}' criado!")
                st.session_state.canal_atual_id = c_id
                st.rerun()
            else:
                st.info("Canal já existe.")
                st.session_state.canal_atual_id = c_id

    # Selectbox de canais existentes
    opcoes_canais = list(db["canais"].keys())
    nomes_canais = [db["canais"][k]["nome"] for k in opcoes_canais]
    
    idx_atual = 0
    if st.session_state.canal_atual_id in opcoes_canais:
        idx_atual = opcoes_canais.index(st.session_state.canal_atual_id)
    
    sel_canal = st.selectbox(
        "Trabalhar no canal:", 
        options=opcoes_canais, 
        format_func=lambda x: db["canais"][x]["nome"],
        index=idx_atual if opcoes_canais else None
    )

    if sel_canal:
        st.session_state.canal_atual_id = sel_canal
    
    st.markdown("---")
    
    # Se houver canal selecionado, lista vídeos para 'trocar' o contexto global
    if st.session_state.canal_atual_id:
        canal_obj = db["canais"][st.session_state.canal_atual_id]
        vids = canal_obj["videos"]
        if vids:
            st.subheader("Vídeo Ativo")
            vid_opts = list(vids.keys())
            # Ordenar por data decrescente (mais novos primeiro)
            vid_opts.sort(key=lambda k: vids[k]["criado_em"], reverse=True)
            
            vid_labels = [f"{vids[k].get('titulo','Sem Título')} ({k})" for k in vid_opts]
            
            idx_v = 0
            if st.session_state.video_atual_id in vid_opts:
                idx_v = vid_opts.index(st.session_state.video_atual_id)
            
            sel_vid = st.radio("Selecione o vídeo:", vid_opts, format_func=lambda x: vids[x].get("titulo", x), index=idx_v)
            if sel_vid:
                st.session_state.video_atual_id = sel_vid
        else:
            st.info("Nenhum vídeo neste canal.")

# -------------------------------------------------------------------
# Página Principal
# -------------------------------------------------------------------
st.title("📺 Monitor de Produção & Liturgia Diária")

# 1. Seção de Busca da Liturgia (Vercel API)
st.markdown("### 🕊️ Inspiração Diária: Liturgia")
with st.container(border=True):
    col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
    
    with col_l1:
        st.info("Utilize a data abaixo para buscar as leituras e criar um vídeo automaticamente.")
    
    with col_l2:
        data_busca = st.date_input("Data da Leitura", datetime.now())
    
    with col_l3:
        st.write("") # Espaçamento
        btn_buscar = st.button("🔍 Buscar Liturgia", type="primary", use_container_width=True)

    # Estado local para guardar o resultado da busca temporariamente
    if "resultado_liturgia" not in st.session_state:
        st.session_state.resultado_liturgia = None

    if btn_buscar:
        # Formata data para URL se necessário, mas a API aceita YYYY-MM-DD ou data normal
        # Endpoint comum da comunidade hospedado na Vercel
        url = f"https://api-liturgia-diaria.vercel.app/?date={data_busca.strftime('%Y-%m-%d')}"
        
        try:
            with st.spinner("Consultando API Vercel..."):
                resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                dados = resp.json()
                st.session_state.resultado_liturgia = dados
                st.success("Leituras encontradas!")
            else:
                st.error(f"Erro ao buscar liturgia: Status {resp.status_code}")
                st.session_state.resultado_liturgia = None
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            st.session_state.resultado_liturgia = None

    # Exibição e Criação do Vídeo
    if st.session_state.resultado_liturgia:
        dados = st.session_state.resultado_liturgia
        
        with st.expander("📖 Ver Leituras Retornadas", expanded=True):
            st.markdown(f"**Primeira Leitura:** {dados.get('primeiraLeitura', '')[:200]}...")
            st.markdown(f"**Salmo:** {dados.get('salmo', '')[:200]}...")
            st.markdown(f"**Evangelho:** {dados.get('evangelho', '')[:200]}...")
            
            st.caption("Texto completo será importado para o roteiro.")

        if st.button("🚀 Criar Projeto de Vídeo com esta Liturgia"):
            if not st.session_state.canal_atual_id:
                st.warning("⚠️ Selecione ou crie um canal na barra lateral antes de criar o vídeo.")
            else:
                novo_id = criar_video_com_liturgia(
                    st.session_state.canal_atual_id, 
                    dados, 
                    data_busca.strftime('%d/%m/%Y')
                )
                st.session_state.video_atual_id = novo_id
                st.success(f"Vídeo criado com sucesso! ID: {novo_id}")
                st.info("Vá para a página '1 - Roteiro Viral' para editar o conteúdo.")
                st.rerun()

st.markdown("---")

# 2. Monitor de Progresso (Código Original Melhorado)
st.header("📊 Resumo de progresso do canal")

if st.session_state.canal_atual_id:
    canal = db["canais"][st.session_state.canal_atual_id]
    videos = canal["videos"]
    
    if not videos:
        st.info("Este canal ainda não possui vídeos. Crie um acima usando a Liturgia ou manualmente.")
    else:
        contagem = {
            "Ideia / só criado": 0,
            "Roteiro pronto": 0,
            "Thumb pronta": 0,
            "Áudio pronto": 0,
            "Vídeo pronto": 0,
            "Publicado": 0,
        }

        # Converte para DataFrame para facilitar visualização
        lista_vids = []

        for vid_id, v in videos.items():
            stt = v["status"]
            status_str = "Ideia"
            
            if stt.get("5_publicacao"):
                contagem["Publicado"] += 1
                status_str = "Publicado"
            elif stt.get("4_video"):
                contagem["Vídeo pronto"] += 1
                status_str = "Vídeo Pronto"
            elif stt.get("3_audio"):
                contagem["Áudio pronto"] += 1
                status_str = "Áudio Pronto"
            elif stt.get("2_thumbnail"):
                contagem["Thumb pronta"] += 1
                status_str = "Thumb Pronta"
            elif stt.get("1_roteiro"):
                contagem["Roteiro pronto"] += 1
                status_str = "Roteiro Pronto"
            else:
                contagem["Ideia / só criado"] += 1
            
            lista_vids.append({
                "ID": vid_id,
                "Título": v.get("titulo", "Sem título"),
                "Atualizado em": v.get("ultima_atualizacao", ""),
                "Status": status_str
            })

        # Métricas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Vídeos", len(videos))
        c2.metric("Roteiros Prontos", contagem["Roteiro pronto"] + contagem["Thumb pronta"] + contagem["Áudio pronto"] + contagem["Vídeo pronto"] + contagem["Publicado"])
        c3.metric("Vídeos Finalizados", contagem["Vídeo pronto"] + contagem["Publicado"])
        c4.metric("Publicados", contagem["Publicado"])

        # Tabela Detalhada
        st.subheader("Lista de Vídeos")
        df = pd.DataFrame(lista_vids)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.warning("Nenhum canal selecionado na barra lateral.")
