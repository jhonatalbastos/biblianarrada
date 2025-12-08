import streamlit as st
import sys
import os
import re  # Importado para limpar o texto
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

# Tenta importar a biblioteca do Piper
try:
    from piper.voice import PiperVoice
except ImportError:
    st.warning("⚠️ Biblioteca 'piper' não detectada. O áudio pode não ser gerado localmente.")

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="3. Narração (Piper TTS)", layout="wide")

# ---------------------------------------------------------------------
# 3. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega do banco
progresso, em_producao = db.load_status(chave_progresso)
texto_roteiro = progresso.get('texto_roteiro_completo', progresso.get('texto_roteiro', ''))

# Se não tiver o texto completo, tenta montar com os blocos
if not texto_roteiro:
    b1 = progresso.get('bloco_leitura', '')
    b2 = progresso.get('bloco_reflexao', '')
    b3 = progresso.get('bloco_aplicacao', '')
    b4 = progresso.get('bloco_oracao', '')
    texto_roteiro = f"{b1}\n\n{b2}\n\n{b3}\n\n{b4}".strip()

# Inicializa o valor no session state se ainda não existir
if "editor_texto_audio" not in st.session_state:
    st.session_state["editor_texto_audio"] = texto_roteiro

# ---------------------------------------------------------------------
# 4. FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------

def limpar_texto_para_tts(texto):
    """Remove caracteres Markdown que podem confundir o gerador de áudio."""
    if not texto:
        return ""
    # Remove negrito/itálico Markdown (** ou *)
    texto_limpo = texto.replace("**", "").replace("*", "")
    # Remove cabeçalhos Markdown (##)
    texto_limpo = texto_limpo.replace("###", "").replace("##", "").replace("#", "")
    # Remove espaços duplos
    texto_limpo = re.sub(' +', ' ', texto_limpo)
    return texto_limpo.strip()

def gerar_audio_piper(texto, caminho_saida):
    """Gera áudio usando o modelo local do Piper (Escrevendo direto em binário)."""
    
    # Caminho do modelo
    model_path = os.path.join(parent_dir, "piper_models", "pt_BR-faber-medium.onnx")
    config_path = os.path.join(parent_dir, "piper_models", "pt_BR-faber-medium.onnx.json")
    
    if not os.path.exists(model_path):
        st.error(f"❌ Modelo de voz não encontrado em: {model_path}")
        return False
        
    if not os.path.exists(config_path):
        st.error(f"❌ Arquivo de configuração (.json) não encontrado em: {config_path}")
        return False

    try:
        # Carrega a voz
        voice = PiperVoice.load(model_path)
        
        # O Piper espera um objeto de arquivo binário padrão
        with open(caminho_saida, "wb") as arquivo_wav:
            voice.synthesize(texto, arquivo_wav)
        
        # Verificação final: se o arquivo for muito pequeno (só cabeçalho), falhou
        if os.path.exists(caminho_saida):
            tamanho_arquivo = os.path.getsize(caminho_saida)
            # 44 bytes é apenas o cabeçalho WAV. Se tiver menos de 1kb, provavelmente está mudo.
            if tamanho_arquivo <= 44: 
                st.error(f"⚠️ O arquivo foi criado mas está vazio ({tamanho_arquivo} bytes). O Piper não conseguiu ler o texto.")
                return False
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"❌ Erro crítico ao processar Piper TTS: {e}")
        return False

# ---------------------------------------------------------------------
# 5. INTERFACE
# ---------------------------------------------------------------------
st.title("🎙️ Passo 3: Narração (Piper TTS)")

cols_header = st.columns([3, 1])
with cols_header[0]:
    st.caption(f"Leitura: **{leitura['titulo']}** | Data: {data_str}")
with cols_header[1]:
    if st.button("🔙 Voltar"):
        st.switch_page("pages/2_Imagens.py")

st.divider()

if not texto_roteiro:
    st.error("❌ Nenhum roteiro encontrado. Volte ao Passo 1 e salve o roteiro primeiro.")
    if st.button("Ir para Roteiro"):
        st.switch_page("pages/1_Roteiro_Viral.py")
    st.stop()

col_esq, col_dir = st.columns([1, 1])

# --- COLUNA 1: VISUALIZAR E EDITAR ROTEIRO ---
with col_esq:
    st.subheader("📜 Roteiro Confirmado")
    st.info("Abaixo está o texto que será lido. Edite se necessário.")
    
    # CORREÇÃO: Usando key para vincular diretamente ao session_state
    texto_editado = st.text_area(
        "Editor de Texto para Áudio", 
        value=st.session_state["editor_texto_audio"], 
        height=400,
        key="editor_texto_audio"
    )
    
    # Atualiza o banco se houver mudança
    if texto_editado != progresso.get('texto_roteiro_completo'):
        progresso['texto_roteiro_completo'] = texto_editado
        # Não salvamos no banco a cada digitação para não travar, 
        # mas o botão de gerar usará o valor atual da caixa.

# --- COLUNA 2: GERADOR DE ÁUDIO PIPER ---
with col_dir:
    st.subheader("🎧 Gerar Áudio")
    
    st.markdown("""
    **Motor de Áudio:** Piper TTS (Local)  
    **Voz Padrão:** `Faber Medium (pt-BR)`  
    *O áudio é gerado localmente via CPU.*
    """)
    
    st.divider()
    
    # Define caminhos
    nome_arquivo = f"audio_{data_str}_{leitura['tipo'].replace(' ', '_')}.wav"
    caminho_relativo = os.path.join("data", "audios")
    caminho_completo_pasta = os.path.join(parent_dir, caminho_relativo)
    
    # Cria pasta se não existir
    if not os.path.exists(caminho_completo_pasta):
        os.makedirs(caminho_completo_pasta, exist_ok=True)
        
    caminho_final_arquivo = os.path.join(caminho_completo_pasta, nome_arquivo)
    
    if st.button("▶️ Gerar Narração com Piper", type="primary", use_container_width=True):
        
        # 1. Pega o texto diretamente do estado da caixa de texto
        texto_bruto = st.session_state["editor_texto_audio"]
        
        # 2. Limpa o texto (remove Markdown)
        texto_para_falar = limpar_texto_para_tts(texto_bruto)
        
        # Debug visual (opcional, ajuda a entender o que está indo para o Piper)
        with st.expander("Ver texto limpo enviado para IA", expanded=False):
            st.code(texto_para_falar)

        if not texto_para_falar:
            st.error("O texto está vazio após a limpeza! Escreva algo na caixa de texto.")
        else:
            with st.spinner("🔊 Sintetizando voz (isso pode levar alguns segundos)..."):
                sucesso = gerar_audio_piper(texto_para_falar, caminho_final_arquivo)
                
                if sucesso:
                    # Salva status
                    progresso['audio'] = True
                    progresso['audio_path'] = caminho_final_arquivo
                    progresso['voz_usada'] = "Piper - Faber Medium"
                    progresso['texto_roteiro_completo'] = texto_bruto # Salva a versão final usada
                    
                    # Código da etapa 3 = Audio
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
                    
                    st.success("Áudio gerado com sucesso!")
                    st.rerun()

    # Se já tiver áudio
    if progresso.get('audio') and progresso.get('audio_path'):
        audio_file_path = progresso['audio_path']
        
        st.success("✅ Áudio Gerado")
        
        # Exibe player de áudio
        if os.path.exists(audio_file_path):
            st.audio(audio_file_path, format="audio/wav")
            
            # Botão de download
            with open(audio_file_path, "rb") as file:
                st.download_button(
                    label="📥 Baixar Áudio WAV",
                    data=file,
                    file_name=nome_arquivo,
                    mime="audio/wav"
                )
        else:
            st.error(f"⚠️ Arquivo não encontrado no disco: {audio_file_path}")

# ---------------------------------------------------------------------
# 6. NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()
col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    if progresso.get('audio'):
        if st.button("Próximo: Overlay e Legendas ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/4_Overlay.py")
    else:
        st.button("Próximo ➡️", disabled=True, use_container_width=True, help="Gere o áudio primeiro.")
