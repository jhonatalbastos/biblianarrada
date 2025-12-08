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

def split_standard(text, max_chars=80):
    """Quebra tradicional por pontuação (Frases longas)."""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        if len(sentence) <= max_chars:
            final_segments.append(sentence)
        else:
            parts = re.split(r'(?<=[,;])\s+', sentence)
            current = ""
            for part in parts:
                if len(current) + len(part) < max_chars:
                    current += part + " "
                else:
                    if current: final_segments.append(current.strip())
                    current = part + " "
            if current: final_segments.append(current.strip())
    return final_segments

def split_dynamic(text, words_per_chunk=4):
    """
    Estilo Dinâmico/TikTok: Quebra por contagem de palavras.
    Gera blocos pequenos para leitura rápida.
    """
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    segments = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        
        # Quebra se atingir o limite de palavras OU se tiver pontuação forte
        has_punctuation = word.endswith(('.', '?', '!', ':', ';'))
        
        if len(current_chunk) >= words_per_chunk or (has_punctuation and len(current_chunk) > 2):
            segments.append(" ".join(current_chunk))
            current_chunk = []
            
    if current_chunk:
        segments.append(" ".join(current_chunk))
        
    return segments

def split_karaoke(text):
    """
    Estilo Karaokê: 1 ou 2 palavras por vez no máximo.
    """
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    segments = []
    
    # Agrupa de 2 em 2 palavras para não ficar frenético demais, 
    # mas ainda muito rápido
    for i in range(0, len(words), 2):
        chunk = words[i:i+2]
        segments.append(" ".join(chunk))
        
    return segments

def gerar_legendas_proporcionais(texto_completo, audio_path, modo="dynamic"):
    """
    Gera legendas proporcionais com base no modo escolhido.
    """
    duration = get_audio_duration_wave(audio_path)
    if duration <= 0: return []

    # Seleciona o algoritmo de quebra
    if modo == "standard":
        segmentos = split_standard(texto_completo, max_chars=80)
    elif modo == "karaoke":
        segmentos = split_karaoke(texto_completo)
    else: # dynamic (default)
        segmentos = split_dynamic(texto_completo, words_per_chunk=4)
    
    # Calcula total de caracteres (peso visual)
    total_len = sum(len(seg) for seg in segmentos)
    if total_len == 0: return []
    
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        # Peso do segmento no tempo total
        # Adiciona um pequeno "peso base" para segmentos muito curtos não piscarem rápido demais
        weight = len(seg)
        seg_duration = (weight / total_len) * duration
        
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
    
    texto_roteiro = progresso.get('texto_roteiro_completo', '')
    if not texto_roteiro:
        b1 = progresso.get('bloco_leitura', '')
        b2 = progresso.get('bloco_reflexao', '')
        b3 = progresso.get('bloco_aplicacao', '')
        b4 = progresso.get('bloco_oracao', '')
        texto_roteiro = f"{b1} {b2} {b3} {b4}"

    st.text_area("Texto Base (Leitura)", value=texto_roteiro, height=300, disabled=True)
    
    # NOVO SELETOR DE ESTILO
    st.markdown("### Estilo da Legenda")
    estilo_selecionado = st.radio(
        "Escolha a dinâmica:",
        ["🚀 Dinâmico (Reels/TikTok - Recomendado)", "🔥 Karaokê (Palavra por Palavra)", "🟢 Padrão (Frases Completas)"],
        index=0
    )
    
    # Mapeia a escolha para a string interna
    modo_map = {
        "🚀 Dinâmico (Reels/TikTok - Recomendado)": "dynamic",
        "🔥 Karaokê (Palavra por Palavra)": "karaoke",
        "🟢 Padrão (Frases Completas)": "standard"
    }
    modo_interno = modo_map[estilo_selecionado]
    
    cor = st.color_picker("Cor de Referência", "#FFFFFF", help="A cor real será definida na renderização.")

with col_dir:
    st.subheader("Gerar")
    
    audio_path = progresso.get('audio_path')
    
    if st.button("⚡ Gerar Legendas (Sincronizar)", type="primary"):
        if not audio_path or not os.path.exists(audio_path):
            st.error("Arquivo de áudio não encontrado no disco.")
        else:
            with st.spinner(f"Gerando legendas no modo {modo_interno.upper()}..."):
                
                legendas_reais = gerar_legendas_proporcionais(texto_roteiro, audio_path, modo=modo_interno)
                
                if legendas_reais:
                    progresso['legendas_dados'] = legendas_reais
                    progresso['legendas'] = True
                    progresso['legenda_config'] = {"ativar": True, "cor": cor, "estilo": modo_interno}
                    
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
                    st.success(f"Sucesso! {len(legendas_reais)} segmentos gerados.")
                    st.rerun()
                else:
                    st.error("Falha ao gerar legendas.")

    # Visualização
    if progresso.get('legendas') and progresso.get('legendas_dados'):
        dados = progresso['legendas_dados']
        st.success(f"✅ Legendas prontas ({len(dados)} blocos)")
        
        with st.expander("🔍 Pré-visualizar Segmentação"):
            # Mostra apenas texto para facilitar leitura
            for item in dados[:10]: # Mostra só os 10 primeiros
                st.text(f"[{item['start']:.2f}s - {item['end']:.2f}s]: {item['text']}")
            if len(dados) > 10:
                st.text(f"... e mais {len(dados)-10} linhas.")

# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
