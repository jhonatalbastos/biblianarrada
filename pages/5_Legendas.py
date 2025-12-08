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
# 3. FUNÇÕES
# ---------------------------------------------------------------------

def get_audio_duration(file_path):
    """Tenta obter duração exata do áudio."""
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

def split_dynamic_smart(text, max_words=4):
    """
    Algoritmo Inteligente para Legendas Dinâmicas (Estilo TikTok).
    Evita deixar palavras órfãs e respeita pontuação.
    """
    # Remove espaços duplos e quebras de linha
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 1. Separa por pontuação forte primeiro para criar "frases lógicas"
    # Mantém a pontuação junto com a palavra
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        
        words = sentence.split()
        chunk = []
        
        for word in words:
            chunk.append(word)
            
            # Condições de quebra:
            # 1. Pontuação final (. ! ?) -> Quebra imediata
            # 2. Pontuação de pausa (, ; :) -> Quebra se já tivermos algumas palavras
            # 3. Limite de palavras atingido
            
            is_end = word.endswith(('.', '!', '?'))
            is_pause = word.endswith((',', ':', ';'))
            
            if is_end:
                final_segments.append(" ".join(chunk))
                chunk = []
            elif is_pause and len(chunk) >= 2:
                final_segments.append(" ".join(chunk))
                chunk = []
            elif len(chunk) >= max_words:
                final_segments.append(" ".join(chunk))
                chunk = []
        
        if chunk:
            final_segments.append(" ".join(chunk))
            
    return final_segments

def gerar_legendas(texto_completo, audio_path):
    duration = get_audio_duration(audio_path)
    if duration <= 0: return [], 0
    
    # Segmenta
    segmentos = split_dynamic_smart(texto_completo, max_words=4)
    
    # Calcula peso (tamanho do texto)
    total_len = sum(len(seg) for seg in segmentos)
    if total_len == 0: return [], duration
    
    legendas = []
    current_time = 0.0
    
    # Distribuição Proporcional
    for seg in segmentos:
        weight = len(seg)
        # Regra de 3: Se texto total tem X chars e dura Y seg, 
        # segmento com Z chars dura (Z/X)*Y
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
st.title("💬 Passo 5: Legendas")
st.caption("Ajuste a sincronia do texto com o áudio.")

if st.button("🔙 Voltar para Overlay"):
    st.switch_page("pages/4_Overlay.py")

st.divider()

if not progresso.get('audio'):
    st.error("⚠️ Áudio não encontrado. Gere o áudio primeiro.")
    st.stop()

audio_path = progresso.get('audio_path', '')
duracao_audio = get_audio_duration(audio_path)

# --- COLUNA DE STATUS ---
col_info, col_reset = st.columns([3, 1])
with col_info:
    st.info(f"🔊 Duração do Áudio Detectada: **{duracao_audio:.1f} segundos**")
with col_reset:
    if st.button("🔄 Forçar Recarga do Texto Completo"):
        # Reconstrói o texto a partir dos blocos originais
        b1 = progresso.get('bloco_leitura', '')
        b2 = progresso.get('bloco_reflexao', '')
        b3 = progresso.get('bloco_aplicacao', '')
        b4 = progresso.get('bloco_oracao', '')
        texto_completo_reset = f"{b1}\n{b2}\n{b3}\n{b4}".strip()
        
        # Salva na sessão e força atualização
        st.session_state['editor_legendas'] = texto_completo_reset
        progresso['texto_roteiro_completo'] = texto_completo_reset
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
        st.success("Texto recarregado!")
        st.rerun()

# --- EDITOR DE TEXTO ---
st.subheader("1. Texto para Sincronia")
st.warning("⚠️ Importante: O texto abaixo deve ser IDÊNTICO ao que é falado no áudio. Se estiver faltando partes, a legenda ficará lenta.")

# Pega texto inicial
texto_banco = progresso.get('texto_roteiro_completo', '')
if 'editor_legendas' not in st.session_state:
    st.session_state['editor_legendas'] = texto_banco

texto_final = st.text_area(
    "Edite o texto aqui se necessário:",
    value=st.session_state['editor_legendas'],
    height=300,
    key='editor_legendas'
)

# Mostra contagem de caracteres para debug
st.caption(f"Tamanho do texto: {len(texto_final)} caracteres.")

st.divider()

# --- BOTÃO DE GERAR ---
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("2. Estilo")
    cor = st.color_picker("Cor de Referência (Apenas Visualização)", "#FFFFFF")
    st.info("O estilo final (fonte, tamanho, cor) é aplicado na Renderização (Passo 6).")

with c2:
    st.subheader("3. Processar")
    if st.button("⚡ Gerar Legendas Agora", type="primary"):
        if len(texto_final) < 50:
            st.error("O texto parece muito curto! Clique em 'Forçar Recarga' lá em cima.")
        else:
            with st.spinner("Sincronizando..."):
                legendas, _ = gerar_legendas(texto_final, audio_path)
                
                if legendas:
                    progresso['legendas_dados'] = legendas
                    progresso['legendas'] = True
                    # Salva também o texto usado para garantir consistência
                    progresso['texto_roteiro_completo'] = texto_final
                    
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
                    st.success(f"Legendas geradas com sucesso! ({len(legendas)} segmentos)")
                    st.rerun()
                else:
                    st.error("Erro na geração.")

# --- PREVIEW ---
if progresso.get('legendas') and progresso.get('legendas_dados'):
    dados = progresso['legendas_dados']
    st.divider()
    st.subheader(f"✅ Resultado: {len(dados)} legendas")
    
    with st.expander("Ver detalhes linha a linha", expanded=True):
        # Mostra as primeiras 5 e as últimas 5 para conferência rápida
        st.markdown("**Início:**")
        for item in dados[:5]:
            st.text(f"[{item['start']:.2f}s - {item['end']:.2f}s]: {item['text']}")
        
        if len(dados) > 10:
            st.markdown("...")
            st.markdown("**Final:**")
            for item in dados[-5:]:
                st.text(f"[{item['start']:.2f}s - {item['end']:.2f}s]: {item['text']}")

st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
