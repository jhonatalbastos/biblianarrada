import streamlit as st
import os
import sys
import datetime
import json

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Módulo de banco de dados não encontrado.")
    st.stop()

st.set_page_config(page_title="5. Legendas", layout="wide")

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

progresso, _ = db.load_status(chave_progresso)

# ---------------------------------------------------------------------
# 3. INTERFACE
# ---------------------------------------------------------------------
st.title("💬 Passo 5: Legendas")

if st.button("🔙 Voltar para Overlay"):
    st.switch_page("pages/4_Overlay.py")

st.divider()

if not progresso.get('audio'):
    st.error("⚠️ Você precisa gerar o áudio primeiro (Passo 3).")
    st.stop()

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.subheader("Configuração")
    estilo = st.selectbox("Estilo da Legenda", ["Karaokê (Palavra por Palavra)", "Frase Completa", "Estilo TikTok"])
    cor = st.color_picker("Cor do Texto", "#FFFFFF")
    
    st.info("O sistema usará o roteiro original para sincronizar com o áudio.")

with col_dir:
    st.subheader("Gerar")
    
    if st.button("⚡ Gerar Legendas (Sincronizar)", type="primary"):
        # Simulação de geração de legendas (Whisper ou Force Alignment)
        legendas_simuladas = [
            {"start": 0.0, "end": 2.0, "text": "Proclamação do Evangelho..."},
            {"start": 2.0, "end": 5.0, "text": "Naquele tempo, disse Jesus..."}
        ]
        
        # SALVA NO BANCO (CRÍTICO PARA O PASSO 6)
        progresso['legendas_dados'] = legendas_simuladas
        progresso['legendas'] = True # <--- A CHAVE QUE O PASSO 6 PROCURA
        progresso['legenda_config'] = {"ativar": True, "cor": cor, "estilo": estilo}
        
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
        st.success("Legendas geradas e salvas!")
        st.rerun()

    if progresso.get('legendas'):
        st.success("✅ Legendas prontas para o vídeo.")
        st.json(progresso.get('legendas_dados', []))

# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
