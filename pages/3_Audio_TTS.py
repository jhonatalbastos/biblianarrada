import streamlit as st
import sys
import os
import subprocess
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

# Carrega status atual do banco
progresso, em_producao = db.load_status(chave_progresso)

# Inicializa dicionário de caminhos de áudio se não existir
if 'caminhos_audios' not in progresso:
    progresso['caminhos_audios'] = {}

# ---------------------------------------------------------------------
# 4. CONFIGURAÇÃO DO PIPER TTS
# ---------------------------------------------------------------------
# Caminho para os modelos na raiz do projeto
pasta_modelos = os.path.join(parent_dir, "piper_models")
caminho_modelo_onnx = os.path.join(pasta_modelos, "pt_BR-faber-medium.onnx")

# Verifica se o modelo existe
if not os.path.exists(caminho_modelo_onnx):
    st.error(f"🚨 Modelo Piper não encontrado em: {caminho_modelo_onnx}")
    st.info("Certifique-se de que a pasta 'piper_models' está na raiz do projeto e contém o arquivo .onnx")
    st.stop()

def gerar_audio_piper(texto, caminho_saida):
    """
    Gera áudio usando o binário do Piper via subprocesso.
    """
    try:
        # Comando: echo "texto" | piper --model modelo.onnx --output_file saida.wav
        # Usamos subprocess para evitar problemas de shell e aspas
        
        comando = [
            "piper",
            "--model", caminho_modelo_onnx,
            "--output_file", caminho_saida
        ]
        
        # Executa o comando passando o texto via STDIN
        processo = subprocess.run(
            comando,
            input=texto,
            text=True, # Garante que o input é tratado como string
            capture_output=True
        )
        
        if processo.returncode == 0:
            return True
        else:
            st.error(f"Erro no Piper: {processo.stderr}")
            return False
            
    except FileNotFoundError:
        st.error("🚨 O executável 'piper' não foi encontrado. Verifique se ele está instalado e no PATH do sistema.")
        return False
    except Exception as e:
        st.error(f"Erro desconhecido ao gerar áudio: {e}")
        return False

def garantir_pasta_audio():
    """Cria a pasta de destino se não existir."""
    pasta = os.path.join(parent_dir, "generated_audio", data_str, leitura['tipo'])
    os.makedirs(pasta, exist_ok=True)
    return pasta

# ---------------------------------------------------------------------
# 5. INTERFACE
# ---------------------------------------------------------------------

st.title("🎙️ Passo 3: Narração (Piper TTS)")

cols_header = st.columns([3, 1])
with cols_header[0]:
    st.markdown(f"**Leitura:** {leitura['titulo']}")
    st.caption("Modelo de Voz: pt_BR-faber-medium")
with cols_header[1]:
    if st.button("🔙 Voltar às Imagens"):
        st.switch_page("pages/2_Imagens.py")

st.divider()

# Recupera textos dos blocos
blocos_texto = {
    "bloco_1": {"titulo": "1. Leitura", "texto": progresso.get('bloco_leitura', '')},
    "bloco_2": {"titulo": "2. Reflexão", "texto": progresso.get('bloco_reflexao', '')},
    "bloco_3": {"titulo": "3. Aplicação", "texto": progresso.get('bloco_aplicacao', '')},
    "bloco_4": {"titulo": "4. Oração", "texto": progresso.get('bloco_oracao', '')},
}

col_info, col_acao = st.columns([2, 1])
with col_info:
    st.info("O Piper gera arquivos .wav de alta qualidade localmente.")

with col_acao:
    if st.button("🎙️ Gerar Todos os Áudios", type="primary", use_container_width=True):
        pasta_destino = garantir_pasta_audio()
        progress_bar = st.progress(0)
        total = len(blocos_texto)
        
        for i, (chave, dados) in enumerate(blocos_texto.items()):
            if dados['texto']:
                nome_arquivo = f"{chave}.wav" # Piper gera wav
                caminho_completo = os.path.join(pasta_destino, nome_arquivo)
                
                sucesso = gerar_audio_piper(dados['texto'], caminho_completo)
                
                if sucesso:
                    progresso['caminhos_audios'][chave] = caminho_completo
            
            progress_bar.progress((i + 1) / total)
        
        # Salva status
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
        st.success("Todos os áudios foram gerados!")
        st.rerun()

st.divider()

# --- ABAS PARA CADA BLOCO ---
tabs = st.tabs([b['titulo'] for b in blocos_texto.values()])

for i, (chave, dados) in enumerate(blocos_texto.items()):
    with tabs[i]:
        col_txt, col_audio = st.columns([1, 1])
        
        with col_txt:
            st.subheader(f"Texto: {dados['titulo']}")
            if not dados['texto']:
                st.warning("Texto vazio. Volte ao Passo 1.")
            else:
                st.markdown(f"*{dados['texto'][:300]}...*")
                
        with col_audio:
            st.subheader("Áudio Gerado")
            
            caminho_existente = progresso['caminhos_audios'].get(chave)
            
            # Botão de gerar individual
            if st.button(f"Gerar Áudio - {dados['titulo']}", key=f"btn_{chave}"):
                if dados['texto']:
                    with st.spinner("Gerando áudio com Piper..."):
                        pasta = garantir_pasta_audio()
                        nome_arquivo = f"{chave}.wav"
                        caminho_completo = os.path.join(pasta, nome_arquivo)
                        
                        sucesso = gerar_audio_piper(dados['texto'], caminho_completo)
                        
                        if sucesso:
                            progresso['caminhos_audios'][chave] = caminho_completo
                            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
                            st.rerun()
            
            # Player de áudio
            if caminho_existente and os.path.exists(caminho_existente):
                st.audio(caminho_existente, format="audio/wav")
                st.success("✅ Áudio pronto.")
            else:
                st.info("Ainda não gerado.")

# ---------------------------------------------------------------------
# 6. NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()

audios = progresso.get('caminhos_audios', {})
tem_todos = all(k in audios for k in ["bloco_1", "bloco_2", "bloco_3", "bloco_4"])

col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    if tem_todos:
        if st.button("Próximo: Montar Vídeo ➡️", type="primary", use_container_width=True):
            progresso['audios_prontos'] = True
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
            # st.switch_page("pages/4_Video.py") 
            st.info("Próxima página: Edição de Vídeo")
    else:
        st.button("Próximo ➡️", disabled=True, use_container_width=True, help="Gere os 4 áudios para continuar.")
