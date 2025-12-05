import streamlit as st
import subprocess
import os
import time
from datetime import datetime

st.set_page_config(page_title="3 – Áudio TTS (Piper)", layout="wide")
st.title("🎙 3 – Gerador de Áudio (Piper TTS Local)")

# -------------------------------------------------------------------
# Configurações e Banco de Dados
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

# Verificações de segurança
if not canal_id or canal_id not in db["canais"]:
    st.error("Nenhum canal selecionado. Vá ao app principal e selecione um canal.")
    st.stop()

canal = db["canais"][canal_id]
videos = canal["videos"]

if not video_id or video_id not in videos:
    st.error("Nenhum vídeo selecionado. Vá ao app principal e selecione um vídeo.")
    st.stop()

video = videos[video_id]

# Garante a estrutura de artefatos
if "artefatos" not in video:
    video["artefatos"] = {}
if "roteiro" not in video["artefatos"]:
    video["artefatos"]["roteiro"] = {}
if "audio_path" not in video["artefatos"]:
    video["artefatos"]["audio_path"] = None

# Caminho para o modelo Piper (Voz Faber)
# Certifique-se de que a pasta 'piper_models' e os arquivos .onnx e .onnx.json estão na raiz
MODELO_PIPER = "piper_models/pt_BR-faber-medium.onnx"

# -------------------------------------------------------------------
# Funções do Piper
# -------------------------------------------------------------------
def verificar_piper():
    """Verifica se o binário do piper está acessível e se o modelo existe."""
    # 1. Verifica modelo
    if not os.path.exists(MODELO_PIPER):
        return False, f"Modelo não encontrado em: {MODELO_PIPER}. Verifique se a pasta 'piper_models' foi enviada."
    
    # 2. Verifica binário (tenta chamar version)
    try:
        subprocess.run(["piper", "--version"], capture_output=True, check=True)
        return True, "Piper instalado e modelo encontrado."
    except FileNotFoundError:
        return False, "O comando 'piper' não foi encontrado no sistema. Verifique se o pacote 'piper-tts' está instalado corretamente."
    except Exception as e:
        return False, f"Erro ao testar Piper: {e}"

def gerar_audio_piper(texto_completo, caminho_saida):
    """Gera áudio usando o Piper via subprocesso."""
    try:
        # Comando: echo 'texto' | piper --model modelo.onnx --output_file saida.wav
        # Usamos input=texto para evitar problemas de escaping no shell com echo
        cmd = [
            "piper",
            "--model", MODELO_PIPER,
            "--output_file", caminho_saida
        ]
        
        processo = subprocess.run(
            cmd,
            input=texto_completo.encode("utf-8"),
            capture_output=True,
            check=True
        )
        return True, "Áudio gerado com sucesso."
    except subprocess.CalledProcessError as e:
        erro_log = e.stderr.decode("utf-8") if e.stderr else str(e)
        return False, f"Erro na execução do Piper: {erro_log}"
    except Exception as ex:
        return False, f"Erro inesperado: {ex}"

# -------------------------------------------------------------------
# Interface Principal
# -------------------------------------------------------------------

# 1. Edição do Texto do Roteiro
st.subheader("📝 Revisão do Texto para Narração")

roteiro_dados = video["artefatos"].get("roteiro", {})
roteiro_blocos = roteiro_dados.get("roteiro", {})

texto_consolidado = ""

# Se tiver blocos estruturados (do passo 1)
if roteiro_blocos:
    lista_textos = []
    for bloco, paragrafos in roteiro_blocos.items():
        if isinstance(paragrafos, list):
            lista_textos.extend(paragrafos)
        elif isinstance(paragrafos, dict):
            # Ordena por índice se for dicionário
            indices = sorted([int(k) for k in paragrafos.keys()])
            for idx in indices:
                lista_textos.append(paragrafos[str(idx)])
    texto_consolidado = "\n".join(lista_textos)
else:
    # Fallback se não tiver estrutura, pega a ideia original ou vazio
    texto_consolidado = roteiro_dados.get("ideia_original", "")

# Área de texto editável para o usuário fazer ajustes finos antes de gerar o áudio
texto_para_narraçao = st.text_area(
    "Edite o texto abaixo exatamente como deve ser falado:",
    value=texto_consolidado,
    height=300,
    help="Dica: O Piper lê melhor se você remover caracteres especiais estranhos e usar pontuação correta."
)

st.info(f"Caracteres totais: {len(texto_para_narraçao)}")

# 2. Geração do Áudio
st.markdown("---")
st.subheader("⚙️ Gerar Áudio")

col_g1, col_g2 = st.columns([1, 2])

with col_g1:
    st.markdown("**Configuração:**")
    st.markdown(f"- **Modelo:** `pt_BR-faber-medium`")
    st.markdown("- **Engine:** Piper TTS (Local)")
    
    status_piper, msg_piper = verificar_piper()
    if status_piper:
        st.success("✅ Sistema pronto")
    else:
        st.error(f"❌ {msg_piper}")

with col_g2:
    if st.button("🎙️ Renderizar Narração", type="primary", disabled=not status_piper, use_container_width=True):
        if not texto_para_narraçao.strip():
            st.warning("O texto está vazio.")
        else:
            with st.spinner("O Piper está narrando seu roteiro... aguarde..."):
                # Cria nome de arquivo único
                nome_limpo = video.get("titulo", "video")[:15].replace(" ", "_")
                filename = f"audio_{video_id}_{nome_limpo}.wav"
                path_final = os.path.join(os.getcwd(), filename)
                
                start_time = time.time()
                sucesso, msg = gerar_audio_piper(texto_para_narraçao, path_final)
                end_time = time.time()
                
                if sucesso:
                    st.success(f"Áudio gerado em {end_time - start_time:.2f}s!")
                    
                    # Salva no estado
                    video["artefatos"]["audio_path"] = path_final
                    video["artefatos"]["audio_info"] = {
                        "motor": "piper",
                        "modelo": "pt_BR-faber-medium",
                        "gerado_em": datetime.now().isoformat()
                    }
                    video["status"]["3_audio"] = True
                    video["ultima_atualizacao"] = datetime.now().isoformat()
                    st.rerun()
                else:
                    st.error(msg)

# 3. Player e Validação
st.markdown("---")
st.subheader("🎧 Resultado Final")

path_atual = video["artefatos"].get("audio_path")

if path_atual and os.path.exists(path_atual):
    st.audio(path_atual, format="audio/wav")
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("Arquivo de áudio vinculado ao projeto.")
    with c2:
        with open(path_atual, "rb") as f:
            st.download_button(
                "💾 Baixar WAV",
                data=f,
                file_name=os.path.basename(path_atual),
                mime="audio/wav"
            )
            
    if st.button("🗑️ Descartar este áudio (Apagar)"):
        video["artefatos"]["audio_path"] = None
        video["status"]["3_audio"] = False
        st.rerun()

elif path_atual:
    st.warning("O arquivo de áudio consta no registro mas não foi encontrado no disco. Gere novamente.")
else:
    st.info("Nenhum áudio gerado para este vídeo ainda.")
