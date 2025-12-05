import streamlit as st
import uuid
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Bíblia Narrada - Dashboard", layout="wide")
st.title("📖 Bíblia Narrada: Gerenciador de Leituras")

# -------------------------------------------------------------------
# DB em sessão (Simplificado para Canal Único)
# -------------------------------------------------------------------
ID_CANAL_PADRAO = "biblia_narrada_v1"

def inicializar_db():
    # Se não existir DB, cria
    if "db" not in st.session_state:
        st.session_state.db = {"canais": {}}
    
    # Se não existir o canal padrão, cria automaticamente
    if ID_CANAL_PADRAO not in st.session_state.db["canais"]:
        st.session_state.db["canais"][ID_CANAL_PADRAO] = {
            "nome": "Bíblia Narrada",
            "nicho": "Espiritualidade Cristã",
            "videos": {},
            "preferencias_titulo": "Use títulos emotivos, curtos e com versículos chave."
        }
    
    # Define o canal atual fixo
    st.session_state.canal_atual_id = ID_CANAL_PADRAO

inicializar_db()

db = st.session_state.db
canal = db["canais"][ID_CANAL_PADRAO]

# Inicializa variável de vídeo atual se não existir
if "video_atual_id" not in st.session_state:
    st.session_state.video_atual_id = None

# -------------------------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------------------------
def gerar_id():
    return str(uuid.uuid4())[:8]

def criar_novo_video(titulo_ideia):
    vid_id = gerar_id()
    novo_video = {
        "id": vid_id,
        "titulo": titulo_ideia,
        "criado_em": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat(),
        "status": {
            "1_roteiro": False,
            "2_thumbnail": False,
            "3_audio": False,
            "4_video": False,
            "5_publicacao": False
        },
        "artefatos": {
            "roteiro": {},
            "imagens_roteiro": {},
            "audio_path": None,
            "video_path": None
        }
    }
    canal["videos"][vid_id] = novo_video
    st.session_state.video_atual_id = vid_id
    st.success(f"Leitura '{titulo_ideia}' iniciada!")
    st.rerun()

def selecionar_video(vid_id):
    st.session_state.video_atual_id = vid_id
    st.rerun()

def excluir_video(vid_id):
    if vid_id in canal["videos"]:
        del canal["videos"][vid_id]
        if st.session_state.video_atual_id == vid_id:
            st.session_state.video_atual_id = None
        st.rerun()

# -------------------------------------------------------------------
# Interface Principal
# -------------------------------------------------------------------

# Sidebar: Criar Nova Leitura
with st.sidebar:
    st.header("✨ Nova Leitura")
    novo_titulo = st.text_input("Tema ou Passagem (ex: Salmo 23)")
    if st.button("Iniciar Projeto", type="primary"):
        if novo_titulo:
            criar_novo_video(novo_titulo)
        else:
            st.warning("Digite um tema para começar.")
            
    st.markdown("---")
    st.info("Este aplicativo foi otimizado para gerar vídeos com a estrutura: Hook, Leitura, Reflexão, Aplicação e Oração.")

# Área Principal: Lista de Projetos
st.subheader("📅 Leituras em Produção")

if not canal["videos"]:
    st.info("Nenhuma leitura cadastrada. Use a barra lateral para criar a primeira.")
else:
    # Converte para DataFrame para facilitar a visualização
    lista_vids = []
    for vid_id, dados in canal["videos"].items():
        status = dados.get("status", {})
        # Barra de progresso visual simples
        progresso = sum([1 for k, v in status.items() if v]) 
        total_etapas = 5
        pct = int((progresso / total_etapas) * 100)
        
        lista_vids.append({
            "ID": vid_id,
            "Título": dados["titulo"],
            "Criado em": dados["criado_em"][:10], # Apenas a data
            "Progresso": f"{pct}%",
            "Etapa Atual": "Concluído" if pct == 100 else "Em andamento"
        })
    
    # Exibe em formato de cards ou tabela. Tabela é mais limpa.
    df = pd.DataFrame(lista_vids)
    
    # Layout de colunas para cada vídeo
    for vid_id, dados in canal["videos"].items():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"### 📜 {dados['titulo']}")
                st.caption(f"ID: {vid_id} | Criado: {dados['criado_em'][:16]}")
            
            with col2:
                # Indicadores de Status
                s = dados["status"]
                st.write(
                    f"{'✅' if s['1_roteiro'] else '⬜'} Roteiro\n\n"
                    f"{'✅' if s['2_thumbnail'] else '⬜'} Thumb\n\n"
                    f"{'✅' if s['3_audio'] else '⬜'} Áudio"
                )
            
            with col3:
                st.write(
                    f"{'✅' if s['4_video'] else '⬜'} Vídeo\n\n"
                    f"{'✅' if s['5_publicacao'] else '⬜'} Publicado"
                )

            with col4:
                if st.button("👉 Editar", key=f"sel_{vid_id}"):
                    selecionar_video(vid_id)
                
                if st.button("🗑️ Excluir", key=f"del_{vid_id}"):
                    excluir_video(vid_id)
            
            st.markdown("---")

# Rodapé de depuração (opcional)
if st.session_state.video_atual_id:
    st.success(f"Editando projeto atual: {canal['videos'][st.session_state.video_atual_id]['titulo']}")
