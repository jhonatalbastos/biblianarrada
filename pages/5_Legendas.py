import streamlit as st
import os
import sys
import datetime
import wave
import contextlib
import re
import subprocess

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

st.set_page_config(page_title="5. Legendas (Debug)", layout="wide")

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
# 3. FUNÇÕES
# ---------------------------------------------------------------------

def get_audio_duration(file_path):
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        try:
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                return f.getnframes() / float(f.getframerate())
        except:
            return 0.0

def split_dynamic_turbo(text, max_words=3):
    """Algoritmo Turbo (TikTok Style) - Quebra a cada 3 palavras."""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        words = sentence.split()
        chunk = []
        for word in words:
            chunk.append(word)
            # Quebra agressiva para dinamismo
            if len(chunk) >= max_words or word.endswith(('.', '!', '?', ',', ':', ';')):
                final_segments.append(" ".join(chunk))
                chunk = []
        if chunk:
            final_segments.append(" ".join(chunk))
    return final_segments

def gerar_legendas(texto_input, audio_path):
    duration = get_audio_duration(audio_path)
    if duration <= 0: return [], 0
    
    # Segmenta
    segmentos = split_dynamic_turbo(texto_input, max_words=3)
    total_len = sum(len(seg) for seg in segmentos)
    
    if total_len == 0: return [], duration
    
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        weight = len(seg)
        # Sincronia Proporcional
        seg_duration = (weight / total_len) * duration
        legendas.append({
            "start": current_time,
            "end": current_time + seg_duration,
            "text": seg
        })
        current_time += seg_duration
        
    return legendas, duration

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("💬 Passo 5: Legendas (Modo Diagnóstico)")

if st.button("🔙 Voltar para Overlay"):
    st.switch_page("pages/4_Overlay.py")

st.divider()

if not progresso.get('audio'):
    st.error("⚠️ Áudio não encontrado.")
    st.stop()

audio_path = progresso.get('audio_path', '')
duracao_audio = get_audio_duration(audio_path)

# --- ÁREA DE DIAGNÓSTICO (O Segredo está aqui) ---
st.subheader("1. Diagnóstico do Texto")

# Inicializa o session_state do editor se não existir
if 'texto_legenda_editor' not in st.session_state:
    # Tenta pegar do banco primeiro
    texto_inicial = progresso.get('texto_roteiro_completo', '')
    # Se estiver vazio, tenta montar
    if not texto_inicial:
        b1 = progresso.get('bloco_leitura', '')
        b2 = progresso.get('bloco_reflexao', '')
        b3 = progresso.get('bloco_aplicacao', '')
        b4 = progresso.get('bloco_oracao', '')
        texto_inicial = f"{b1}\n{b2}\n{b3}\n{b4}".strip()
    
    st.session_state['texto_legenda_editor'] = texto_inicial

# Caixa de Texto vinculada ao Session State
texto_atual = st.text_area(
    "Cole o texto COMPLETO aqui:",
    value=st.session_state['texto_legenda_editor'],
    height=300,
    key='texto_legenda_editor'
)

# Cálculos em tempo real
chars = len(texto_atual)
palavras = len(texto_atual.split())
ratio = chars / duracao_audio if duracao_audio > 0 else 0

# Exibe Painel de Controle
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Duração Áudio", f"{duracao_audio:.1f}s")
with c2:
    st.metric("Tamanho Texto", f"{chars} caracteres", delta="Baixo" if chars < 200 else "Ok")
with c3:
    st.metric("Densidade", f"{ratio:.1f} chars/seg")

# Alerta Visual
if chars < 100 and duracao_audio > 30:
    st.error("🚨 **ALERTA CRÍTICO:** O texto é muito curto para este áudio!")
    st.markdown(f"Você tem **{duracao_audio:.0f} segundos** de áudio, mas apenas **{palavras} palavras** de texto.")
    st.markdown("👉 **AÇÃO:** Vá até o Roteiro, copie TUDO e cole na caixa acima antes de gerar.")
    bloqueado = True
else:
    st.success("✅ Texto parece compatível com o áudio.")
    bloqueado = False

st.divider()

col_btn_1, col_btn_2 = st.columns([1, 1])

with col_btn_1:
    if st.button("🗑️ Resetar Tudo (Emergência)"):
        progresso['legendas'] = False
        progresso['legendas_dados'] = []
        # Limpa o texto do banco para forçar você a colar de novo
        progresso['texto_roteiro_completo'] = "" 
        st.session_state['texto_legenda_editor'] = ""
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
        st.rerun()

with col_btn_2:
    if st.button("⚡ Gerar Legendas (Usando texto acima)", type="primary", disabled=bloqueado):
        # 1. Salva explicitamente o que está na caixa agora
        texto_para_usar = st.session_state['texto_legenda_editor']
        progresso['texto_roteiro_completo'] = texto_para_usar
        
        # 2. Gera
        legendas, _ = gerar_legendas(texto_para_usar, audio_path)
        
        if legendas:
            progresso['legendas_dados'] = legendas
            progresso['legendas'] = True
            progresso['legenda_config'] = {"estilo": "turbo"}
            
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
            st.success(f"Gerado! {len(legendas)} segmentos criados.")
            st.rerun()

# Preview
if progresso.get('legendas') and progresso.get('legendas_dados'):
    dados = progresso['legendas_dados']
    st.divider()
    st.markdown(f"### Resultado: {len(dados)} linhas")
    
    # Mostra tabela completa para você ter certeza
    with st.expander("Ver todas as linhas (Confira se vai até o final)", expanded=True):
        st.dataframe(dados)

# Navegação
st.divider()
if st.button("Ir para Renderização ➡️"):
    st.switch_page("pages/6_Video_Final.py")
