import streamlit as st
import sys
import os
import wave
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

# ---------------------------------------------------------------------
# 4. FUNÇÃO DE GERAÇÃO PIPER TTS (CORRIGIDO FINAL)
# ---------------------------------------------------------------------
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
        
        # CORREÇÃO PRINCIPAL:
        # O Piper espera um objeto de arquivo binário padrão, não um objeto wave.
        # Ele mesmo escreve os headers do WAV.
        with open(caminho_saida, "wb") as arquivo_wav:
            voice.synthesize(texto, arquivo_wav)
        
        # Verificação final: se o arquivo for muito pequeno (só cabeçalho), falhou
        if os.path.exists(caminho_saida):
            tamanho_arquivo = os.path.getsize(caminho_saida)
            if tamanho_arquivo <= 44: # 44 bytes é apenas o cabeçalho WAV
                st.error("⚠️ O arquivo de áudio foi criado mas parece vazio. Verifique se o texto não está em branco.")
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

# --- COLUNA 1: VISUALIZAR ROTEIRO ---
with col_esq:
    st.subheader("📜 Roteiro Confirmado")
    st.info("Este é o texto que será narrado.")
    
    with st.container(border=True):
        st.markdown(texto_roteiro)
    
    with st.expander("✏️ Editar Roteiro (Ajuste Final)"):
        texto_editado = st.text_area("Ajustar texto para áudio:", value=texto_roteiro, height=300)
        if st.button("Salvar Ajuste de Texto"):
            progresso['texto_roteiro_completo'] = texto_editado
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 3)
            st.success("Texto atualizado!")
            st.rerun()

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
        
        texto_para_falar = texto_editado if 'texto_editado' in locals() else texto_roteiro
        
        # Limpeza básica para evitar erros no TTS
        texto_para_falar = texto_para_falar.strip()
        if not texto_para_falar:
            st.error("O texto está vazio!")
        else:
            with st.spinner("🔊 Sintetizando voz (isso pode levar alguns segundos)..."):
                sucesso = gerar_audio_piper(texto_para_falar, caminho_final_arquivo)
                
                if sucesso:
                    # Salva status
                    progresso['audio'] = True
                    progresso['audio_path'] = caminho_final_arquivo
                    progresso['voz_usada'] = "Piper - Faber Medium"
                    
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
