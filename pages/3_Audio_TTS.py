import streamlit as st
import sys
import os
import time
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CORREÇÃO DE IMPORTAÇÃO (CRÍTICO)
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
st.set_page_config(page_title="3. Narração (TTS)", layout="wide")

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

# Recupera o roteiro salvo no Passo 1
texto_roteiro = progresso.get('texto_roteiro', '')

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("🎙️ Passo 3: Narração (TTS)")

cols_header = st.columns([3, 1])
with cols_header[0]:
    st.caption(f"Leitura: **{leitura['titulo']}** | Data: {data_str}")
with cols_header[1]:
    if st.button("🔙 Voltar"):
        st.switch_page("pages/2_Thumbnail_AB.py") # Ajuste conforme o nome do seu arquivo anterior

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
    st.info("Este é o texto que será transformado em áudio.")
    
    with st.container(border=True):
        st.markdown(texto_roteiro)
    
    # Opção de edição rápida caso perceba erro
    with st.expander("✏️ Editar Roteiro (Ajuste Fino)"):
        texto_editado = st.text_area("Ajustar texto para áudio:", value=texto_roteiro, height=200)
        if st.button("Salvar Ajuste"):
            progresso['texto_roteiro'] = texto_editado
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)
            st.success("Texto atualizado!")
            st.rerun()

# --- COLUNA 2: GERADOR DE ÁUDIO ---
with col_dir:
    st.subheader("🎧 Gerar Áudio")
    
    # Configurações de Voz (Simulado por enquanto, preparatório para Edge-TTS)
    voz_selecionada = st.selectbox(
        "Selecione a Voz (Edge TTS)",
        ["pt-BR-FranciscaNeural (Feminina)", "pt-BR-AntonioNeural (Masculina)", "pt-BR-ThalitaNeural (Jovem)"]
    )
    
    velocidade = st.slider("Velocidade da Fala", 0.75, 1.5, 1.0, 0.05)
    
    st.markdown("---")
    
    # Verifica se já existe áudio gerado (salvo no progresso ou simulado)
    audio_path = progresso.get('audio_path', None)
    
    if st.button("▶️ Gerar Narração", type="primary", use_container_width=True):
        with st.spinner("Sintetizando voz com Inteligência Artificial..."):
            # AQUI ENTRARIA O CÓDIGO REAL DO EDGE-TTS
            # Por enquanto, vamos simular o sucesso e salvar o status
            time.sleep(2) # Simula processamento
            
            # Simula um caminho de arquivo (em produção, você salvaria o arquivo real em /temp ou /data)
            # Para testar sem gerar arquivo real, apenas marcamos como feito.
            fake_audio_path = "simulacao_audio.mp3" 
            
            progresso['audio'] = True
            progresso['audio_path'] = fake_audio_path # Salva caminho no banco
            progresso['voz_usada'] = voz_selecionada
            
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)
            
            st.success("Áudio gerado com sucesso!")
            st.rerun()

    # Se já tiver áudio (ou simulado)
    if progresso.get('audio'):
        st.success("✅ Áudio disponível")
        
        # Como estamos simulando, não temos o arquivo .mp3 real para tocar st.audio()
        # Se você tiver o arquivo real, descomente abaixo:
        # if os.path.exists(audio_path):
        #     st.audio(audio_path)
        # else:
        st.warning("⚠️ Modo Simulação: O arquivo de áudio seria reproduzido aqui.")
        
        st.info(f"Voz utilizada: {progresso.get('voz_usada', 'Padrão')}")

# ---------------------------------------------------------------------
# 5. NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()
col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    if progresso.get('audio'):
        # Supondo que o próximo arquivo seja 4_Video_Final.py
        if st.button("Próximo: Montar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/4_Video_Final.py")
    else:
        st.button("Próximo: Montar Vídeo ➡️", disabled=True, use_container_width=True, help="Gere o áudio primeiro.")
