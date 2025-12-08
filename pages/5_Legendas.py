import streamlit as st
import os
import sys
import datetime
import wave
import contextlib
import re

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
# 3. FUNÇÕES DE PROCESSAMENTO
# ---------------------------------------------------------------------

def get_audio_duration_wave(file_path):
    """Obtém a duração exata do arquivo WAV em segundos."""
    try:
        with contextlib.closing(wave.open(file_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"Erro ao ler WAV: {e}")
        return 0.0

def split_into_segments(text, max_chars=80):
    """
    Quebra o texto em segmentos menores para caber na tela.
    Tenta quebrar por pontuação ou por tamanho máximo.
    """
    # Remove quebras de linha extras e normaliza espaços
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Divide primeiro por pontuação forte para garantir pausas lógicas
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        
        # Se a frase for curta, adiciona direto
        if len(sentence) <= max_chars:
            final_segments.append(sentence)
        else:
            # Se for longa, quebra por vírgulas ou espaço
            parts = re.split(r'(?<=[,;])\s+', sentence)
            current_part = ""
            
            for part in parts:
                if len(current_part) + len(part) < max_chars:
                    current_part += part + " "
                else:
                    if current_part:
                        final_segments.append(current_part.strip())
                    current_part = part + " "
            
            if current_part:
                final_segments.append(current_part.strip())
                
    return final_segments

def gerar_legendas_proporcionais(texto_completo, audio_path):
    """
    Gera legendas baseadas na duração proporcional dos caracteres.
    Não é perfeito como IA (Whisper), mas garante que todo texto apareça.
    """
    duration = get_audio_duration_wave(audio_path)
    if duration <= 0:
        return []

    # 1. Segmenta o texto em linhas legíveis
    segmentos = split_into_segments(texto_completo, max_chars=90)
    
    # 2. Calcula total de caracteres (ignorando espaços vazios excessivos)
    total_chars = sum(len(seg) for seg in segmentos)
    if total_chars == 0: return []
    
    # 3. Distribui o tempo
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        # Tempo proporcional ao tamanho do texto
        seg_duration = (len(seg) / total_chars) * duration
        
        # Ajuste fino: garante mínimo de 1.5s para leitura se possível
        # (Isso pode distorcer o final, então usamos com cuidado ou apenas o proporcional puro)
        
        legendas.append({
            "start": current_time,
            "end": current_time + seg_duration,
            "text": seg
        })
        current_time += seg_duration
        
    return legendas

# ---------------------------------------------------------------------
# 4. INTERFACE
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
    
    # Recupera o texto completo usado no áudio
    texto_roteiro = progresso.get('texto_roteiro_completo', '')
    if not texto_roteiro:
        # Fallback se não tiver o completo salvo
        b1 = progresso.get('bloco_leitura', '')
        b2 = progresso.get('bloco_reflexao', '')
        b3 = progresso.get('bloco_aplicacao', '')
        b4 = progresso.get('bloco_oracao', '')
        texto_roteiro = f"{b1} {b2} {b3} {b4}"

    st.text_area("Texto Base para Legenda (Somente Leitura)", value=texto_roteiro, height=300, disabled=True)
    
    estilo = st.selectbox("Algoritmo de Sincronia", ["Proporcional (Padrão)", "Estilo TikTok (Rápido)"])
    cor = st.color_picker("Cor de Referência", "#FFFFFF", help="A cor final é definida na renderização.")

with col_dir:
    st.subheader("Gerar")
    
    audio_path = progresso.get('audio_path')
    
    if st.button("⚡ Gerar Legendas (Sincronizar)", type="primary"):
        if not audio_path or not os.path.exists(audio_path):
            st.error("Arquivo de áudio não encontrado no disco.")
        else:
            with st.spinner("Calculando tempos e segmentando texto..."):
                # GERAÇÃO REAL AGORA
                legendas_reais = gerar_legendas_proporcionais(texto_roteiro, audio_path)
                
                if legendas_reais:
                    # SALVA NO BANCO
                    progresso['legendas_dados'] = legendas_reais
                    progresso['legendas'] = True
                    progresso['legenda_config'] = {"ativar": True, "cor": cor, "estilo": estilo}
                    
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
                    st.success(f"Sucesso! {len(legendas_reais)} linhas de legenda geradas.")
                    st.rerun()
                else:
                    st.error("Falha ao gerar legendas. Verifique se o áudio e o texto estão válidos.")

    # Visualização dos dados gerados
    if progresso.get('legendas') and progresso.get('legendas_dados'):
        dados = progresso['legendas_dados']
        st.success(f"✅ Legendas prontas ({len(dados)} segmentos)")
        
        with st.expander("Ver tabela de tempos"):
            st.dataframe(dados)

# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
