import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
import requests

st.set_page_config(page_title="Bíblia Narrada - Studio", layout="wide")

# -------------------------------------------------------------------
# Configuração Única do Canal "Bíblia Narrada"
# -------------------------------------------------------------------
CANAL_FIXO_ID = "biblia_narrada_oficial"
CANAL_FIXO_NOME = "Bíblia Narrada"
CANAL_FIXO_URL = "https://www.youtube.com/@BibliaNarrada"

def inicializar_db():
    if "db" not in st.session_state:
        st.session_state.db = {"canais": {}}
    
    # Garante que o canal oficial exista
    if CANAL_FIXO_ID not in st.session_state.db["canais"]:
        st.session_state.db["canais"][CANAL_FIXO_ID] = {
            "nome": CANAL_FIXO_NOME,
            "url": CANAL_FIXO_URL,
            "videos": {},
            "preferencias_titulo": "Bíblia, Oração, Deus, Fé"
        }
    
    # Força a seleção deste canal para todo o app
    st.session_state.canal_atual_id = CANAL_FIXO_ID

inicializar_db()

# Atalhos para variáveis globais
db = st.session_state.db
canal = db["canais"][CANAL_FIXO_ID]

# -------------------------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------------------------
def gerar_id():
    return str(uuid.uuid4())[:8]

def criar_video_com_liturgia(dados_liturgia, data_escolhida):
    """Cria o vídeo no banco com base na liturgia."""
    novo_vid_id = gerar_id()
    
    # Prepara o texto combinado
    leitura1 = dados_liturgia.get('primeiraLeitura', 'Leitura 1 não encontrada.')
    salmo = dados_liturgia.get('salmo', 'Salmo não encontrado.')
    evangelho = dados_liturgia.get('evangelho', 'Evangelho não encontrado.')
    segunda = dados_liturgia.get('segundaLeitura', '')

    texto_combinado = f"""LITURGIA DO DIA: {data_escolhida}

PRIMEIRA LEITURA:
{leitura1}

SALMO:
{salmo}

EVANGELHO:
{evangelho}
"""
    if segunda:
        texto_combinado += f"\nSEGUNDA LEITURA:\n{segunda}"

    titulo_sug = f"Evangelho do Dia - {data_escolhida}"

    novo_video = {
        "id": novo_vid_id,
        "titulo": titulo_sug,
        "criado_em": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat(),
        "status": {
            "1_roteiro": False,
            "2_thumbnail": False,
            "3_audio": False,
            "4_video": False,
            "5_publicacao": False,
        },
        "artefatos": {
            "roteiro": {
                "ideia_original": texto_combinado.strip(),
                "roteiro": {},
                "image_prompts": {},
                "titulo_video": titulo_sug
            },
            "imagens_roteiro": {},
            "audio_path": None,
            "video_path": None,
        },
    }
    
    canal["videos"][novo_vid_id] = novo_video
    return novo_vid_id

# -------------------------------------------------------------------
# Interface Principal
# -------------------------------------------------------------------
st.title(f"🎬 Studio {CANAL_FIXO_NOME}")
st.write("Bem-vindo ao painel de controle de produção.")

# --- SEÇÃO 1: BUSCA LITURGIA (CORRIGIDA) ---
st.markdown("### 🕊️ Nova Produção: Liturgia Diária")

with st.container(border=True):
    c1, c2 = st.columns([1, 4])
    with c1:
        data_busca = st.date_input("Escolha a data", datetime.now())
    with c2:
        st.write("") 
        st.write("") 
        btn_buscar = st.button("🔍 Buscar Leituras na API", type="primary")

    if "liturgia_temp" not in st.session_state:
        st.session_state.liturgia_temp = None

    if btn_buscar:
        # Formata a data para o padrão da API: YYYY-MM-DD
        data_str = data_busca.strftime('%Y-%m-%d')
        # URL da API Comunitária
        url = f"https://api-liturgia-diaria.vercel.app/?date={data_str}"
        
        try:
            with st.spinner(f"Consultando liturgia de {data_str}..."):
                # Header as vezes ajuda a não ser bloqueado
                headers = {'User-Agent': 'Mozilla/5.0'} 
                resp = requests.get(url, headers=headers, timeout=15)
                
            if resp.status_code == 200:
                dados = resp.json()
                # Validação simples se veio conteúdo
                if 'evangelho' in dados or 'primeiraLeitura' in dados:
                    st.session_state.liturgia_temp = dados
                    st.success("Leituras encontradas com sucesso!")
                else:
                    st.warning("A API retornou 200 OK, mas os campos esperados (evangelho/leitura) estão vazios.")
                    st.json(dados) # Mostra o que veio pra debug
                    st.session_state.liturgia_temp = None
            else:
                st.error(f"Erro na API: Status {resp.status_code}")
                st.write(resp.text)
                st.session_state.liturgia_temp = None
                
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            st.session_state.liturgia_temp = None

    # Exibição do Resultado
    if st.session_state.liturgia_temp:
        dados = st.session_state.liturgia_temp
        
        # Expander para ver se os dados estão lá mesmo
        with st.expander("📖 Visualizar Leituras (Expandir)", expanded=True):
            st.markdown(f"**Evangelho:** {dados.get('evangelho', 'Não encontrado')[:300]}...")
            st.markdown(f"**Salmo:** {dados.get('salmo', 'Não encontrado')[:150]}...")
            
            # Debug para usuário ver o JSON completo se achar que está em branco
            if st.checkbox("Ver JSON Bruto (Debug)"):
                st.json(dados)

        if st.button("🚀 Iniciar Projeto com esta Liturgia"):
            novo_id = criar_video_com_liturgia(dados, data_busca.strftime('%d/%m/%Y'))
            st.session_state.video_atual_id = novo_id
            st.success("Projeto criado! Vá para a página '1 - Roteiro' na barra lateral.")
            st.rerun()

st.markdown("---")

# --- SEÇÃO 2: DASHBOARD DO CANAL ---
st.subheader("📊 Projetos em Andamento")

videos = canal["videos"]

if not videos:
    st.info("Nenhum projeto criado ainda. Use a busca acima para começar.")
else:
    # Lógica de seleção do vídeo ativo
    st.write("Selecione qual vídeo você quer editar agora:")
    
    # Prepara lista para o selectbox
    lista_vids_ordenada = sorted(videos.items(), key=lambda x: x[1]['criado_em'], reverse=True)
    opcoes_ids = [v[0] for v in lista_vids_ordenada]
    
    # Função para mostrar o nome bonito no selectbox
    def formatar_opcao(vid_id):
        v = videos[vid_id]
        status_txt = "Novo"
        if v["status"]["5_publicacao"]: status_txt = "Publicado ✅"
        elif v["status"]["4_video"]: status_txt = "Vídeo Pronto 🎬"
        elif v["status"]["1_roteiro"]: status_txt = "Roteiro OK 📝"
        return f"{v.get('titulo', 'Sem Título')} ({status_txt})"

    idx_atual = 0
    if st.session_state.video_atual_id in opcoes_ids:
        idx_atual = opcoes_ids.index(st.session_state.video_atual_id)

    escolha = st.selectbox(
        "Projetos Recentes:", 
        options=opcoes_ids, 
        format_func=formatar_opcao,
        index=idx_atual
    )
    
    if escolha:
        st.session_state.video_atual_id = escolha
        v_sel = videos[escolha]
        
        # Mini resumo do vídeo selecionado
        st.info(f"Editando: **{v_sel.get('titulo')}** | ID: {escolha}")
        
        # Tabela simples de status
        status = v_sel["status"]
        cols = st.columns(5)
        cols[0].checkbox("Roteiro", value=status["1_roteiro"], disabled=True)
        cols[1].checkbox("Thumb", value=status["2_thumbnail"], disabled=True)
        cols[2].checkbox("Áudio", value=status["3_audio"], disabled=True)
        cols[3].checkbox("Vídeo", value=status["4_video"], disabled=True)
        cols[4].checkbox("Publicado", value=status["5_publicacao"], disabled=True)

# Rodapé simples
st.markdown("---")
st.caption("Biblia Narrada Studio v2.0 - Integração Vercel API")
