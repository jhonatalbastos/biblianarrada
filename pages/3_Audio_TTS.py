import streamlit as st
import sys
import os
import re
import subprocess  # Adicionado para fallback
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Módulo de banco de dados não encontrado.")
    st.stop()

# Tenta importar Piper
HAS_PIPER_LIB = False
try:
    from piper.voice import PiperVoice
    HAS_PIPER_LIB = True
except ImportError:
    pass

st.set_page_config(page_title="3. Narração (Piper TTS)", layout="wide")

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

progresso, _ = db.load_status(chave_progresso)
texto_roteiro = progresso.get('texto_roteiro_completo', progresso.get('texto_roteiro', ''))

if not texto_roteiro:
    # Tenta montar com blocos isolados
    b1 = progresso.get('bloco_leitura', '')
    b2 = progresso.get('bloco_reflexao', '')
    b3 = progresso.get('bloco_aplicacao', '')
    b4 = progresso.get('bloco_oracao', '')
    texto_roteiro = f"{b1}\n\n{b2}\n\n{b3}\n\n{b4}".strip()

# Inicializa editor
if "editor_texto_audio" not in st.session_state:
    st.session_state["editor_texto_audio"] = texto_roteiro

# ---------------------------------------------------------------------
# 3. FUNÇÕES DE GERAÇÃO (HÍBRIDA)
# ---------------------------------------------------------------------
def limpar_texto(texto):
    """Remove caracteres que quebram o TTS."""
    if not texto: return ""
    # Remove markdown
    t = texto.replace("**", "").replace("*", "").replace("###", "").replace("##", "").replace("#", "")
    t = re.sub(r'\s+', ' ', t).strip() # Remove espaços extras
    return t

def gerar_audio_sistema(texto, caminho_onnx, caminho_saida):
    """Tenta gerar via comando de terminal (Fallback se a lib falhar)."""
    try:
        # Comando: echo 'texto' | piper -m modelo.onnx -f saida.wav
        cmd = [
            "piper",
            "--model", caminho_onnx,
            "--output_file", caminho_saida
        ]
        
        # Executa processo
        process = subprocess.Popen(
            cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=texto.encode('utf-8'))
        
        if process.returncode == 0 and os.path.exists(caminho_saida) and os.path.getsize(caminho_saida) > 100:
            return True, "Sucesso via CLI"
        else:
            return False, f"Erro CLI: {stderr.decode()}"
    except Exception as e:
        return False, str(e)

def gerar_audio_piper_hibrido(texto, caminho_saida):
    """Tenta via Python Lib, se falhar (0 bytes), tenta via Sistema."""
    model_path = os.path.join(parent_dir, "piper_models", "pt_BR-faber-medium.onnx")
    config_path = os.path.join(parent_dir, "piper_models", "pt_BR-faber-medium.onnx.json")

    if not os.path.exists(model_path):
        st.error(f"Arquivo de modelo não encontrado: {model_path}")
        return False

    # 1. TENTATIVA VIA BIBLIOTECA PYTHON (Preferencial)
    if HAS_PIPER_LIB:
        try:
            voice = PiperVoice.load(model_path, config_path=config_path)
            with open(caminho_saida, "wb") as f:
                voice.synthesize(texto, f)
            
            # Verifica sucesso
            if os.path.exists(caminho_saida) and os.path.getsize(caminho_saida) > 1000:
                return True
            else:
                print("Python Lib gerou arquivo vazio. Tentando fallback...")
        except Exception as e:
            print(f"Erro Python Lib: {e}")

    # 2. TENTATIVA VIA FALLBACK (CLI DO SISTEMA)
    # Útil se houver problema de dependência C++ na biblioteca Python
    sucesso_cli, msg = gerar_audio_sistema(texto, model_path, caminho_saida)
    if sucesso_cli:
        return True
    
    st.error(f"Falha na geração de áudio. O arquivo final ficou vazio.\nDiagnóstico: {msg}")
    return False

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("🎙️ Passo 3: Narração (Piper TTS)")

cols_header = st.columns([3, 1])
with cols_header[0]:
    st.caption(f"Leitura: **{leitura['titulo']}**")
with cols_header[1]:
    if st.button("🔙 Voltar"):
        st.switch_page("pages/2_Imagens.py")

st.divider()

if not texto_roteiro:
    st.error("Roteiro vazio.")
    st.stop()

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.subheader("📜 Texto para Narração")
    texto_editado = st.text_area(
        "Edite o texto aqui se necessário:",
        value=st.session_state["editor_texto_audio"],
        height=400,
        key="editor_texto_audio"
    )

with col_dir:
    st.subheader("🎧 Gerar e Ouvir")
    st.info("Usando motor: Piper TTS (Local)")
    
    # Prepara caminhos
    nome_arquivo = f"audio_{data_str}_{leitura['tipo'].replace(' ', '_')}.wav"
    pasta_audios = os.path.join(parent_dir, "data", "audios")
    os.makedirs(pasta_audios, exist_ok=True)
    caminho_final = os.path.join(pasta_audios, nome_arquivo)
    
    if st.button("▶️ Gerar Áudio Agora", type="primary"):
        texto_limpo = limpar_texto(texto_editado)
        
        if not texto_limpo:
            st.warning("O texto está vazio após a limpeza.")
        else:
            with st.spinner("Sintetizando áudio..."):
                if gerar_audio_piper_hibrido(texto_limpo, caminho_final):
                    progresso['audio'] = True
                    progresso['audio_path'] = caminho_final
                    progresso['voz_usada'] = "Piper Faber Medium"
                    progresso['texto_roteiro_completo'] = texto_editado
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
                    st.success("Áudio criado com sucesso!")
                    st.rerun()

    # Player
    if progresso.get('audio') and progresso.get('audio_path'):
        path = progresso['audio_path']
        if os.path.exists(path):
            st.audio(path, format="audio/wav")
            with open(path, "rb") as f:
                st.download_button("📥 Baixar WAV", f, file_name=nome_arquivo)
        else:
            st.error("Arquivo consta no banco mas não existe no disco.")

# Navegação
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('audio'):
        if st.button("Próximo: Overlay ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/4_Overlay.py")
