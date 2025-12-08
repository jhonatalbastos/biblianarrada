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

def split_dynamic_turbo(text, max_words=3):
    """
    Algoritmo Turbo para TikTok.
    Quebra o texto em blocos muito curtos (máx 3 palavras) para dar dinamismo.
    """
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Divide por pontuação forte
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        
        words = sentence.split()
        chunk = []
        
        for word in words:
            chunk.append(word)
            # Quebra se atingir 3 palavras ou se tiver pontuação
            if len(chunk) >= max_words or word.endswith(('.', '!', '?', ',', ':', ';')):
                final_segments.append(" ".join(chunk))
                chunk = []
        
        if chunk:
            final_segments.append(" ".join(chunk))
            
    return final_segments

def gerar_legendas(texto_completo, audio_path):
    duration = get_audio_duration(audio_path)
    if duration <= 0: return [], 0
    
    # Segmenta
    segmentos = split_dynamic_turbo(texto_completo, max_words=3)
    
    total_len = sum(len(seg) for seg in segmentos)
    if total_len == 0: return [], duration
    
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        weight = len(seg)
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
    st.info(f"🔊 Áudio Detectado: **{duracao_audio:.1f} segundos**")
with col_reset:
    if st.button("🗑️ Limpar Legendas Antigas", type="secondary"):
        progresso['legendas'] = False
        progresso['legendas_dados'] = []
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
        st.success("Limpo! Recarregando...")
        st.rerun()

st.divider()

# --- EDITOR DE TEXTO ---
st.subheader("1. Texto para Sincronia (Obrigatório)")

# Tenta recuperar o texto completo. Se falhar, tenta reconstruir.
texto_banco = progresso.get('texto_roteiro_completo', '')
if not texto_banco or len(texto_banco) < 50:
     # Tenta montar o texto novamente com os blocos
    b1 = progresso.get('bloco_leitura', '')
    b2 = progresso.get('bloco_reflexao', '')
    b3 = progresso.get('bloco_aplicacao', '')
    b4 = progresso.get('bloco_oracao', '')
    texto_banco = f"{b1}\n{b2}\n{b3}\n{b4}".strip()

# Caixa de edição
texto_final = st.text_area(
    "Verifique se o texto abaixo é o roteiro COMPLETO. Se estiver curto, cole o texto certo aqui:",
    value=texto_banco,
    height=400
)

chars_count = len(texto_final)
st.caption(f"Tamanho do texto: {chars_count} caracteres.")

if chars_count < 100:
    st.error("🚨 **ERRO: TEXTO MUITO CURTO!**")
    st.markdown("""
    O sistema detectou que você tem pouco texto (provavelmente apenas o título). 
    Se você gerar legendas agora, elas ficarão paradas por 40 segundos.
    
    **Solução:**
    1. Vá na página **1. Roteiro Viral**.
    2. Copie todo o texto gerado.
    3. Volte aqui e **cole na caixa acima**.
    """)
    bloquear_botao = True
else:
    bloquear_botao = False

st.divider()

# --- BOTÃO DE GERAR ---
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("2. Estilo")
    st.success("Modo Turbo (TikTok/Reels)")
    st.caption("Legendas rápidas (3 palavras por vez).")

with c2:
    st.subheader("3. Processar")
    if st.button("⚡ Gerar Legendas (Sincronizar)", type="primary", disabled=bloquear_botao):
        with st.spinner("Sincronizando..."):
            # Salva o texto que o usuário colou para não perder
            progresso['texto_roteiro_completo'] = texto_final
            
            legendas, duracao = gerar_legendas(texto_final, audio_path)
            
            if legendas:
                progresso['legendas_dados'] = legendas
                progresso['legendas'] = True
                progresso['legenda_config'] = {"estilo": "turbo"}
                
                db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
                st.success(f"Sucesso! Geradas {len(legendas)} linhas de legenda.")
                st.rerun()
            else:
                st.error("Erro na geração.")

# --- PREVIEW ---
if progresso.get('legendas') and progresso.get('legendas_dados'):
    dados = progresso['legendas_dados']
    st.divider()
    st.markdown(f"### ✅ Resultado: {len(dados)} legendas")
    
    with st.expander("Verificar tempos (Início e Fim)", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Começo:**")
            for item in dados[:5]:
                st.text(f"{item['start']:.1f}s: {item['text']}")
        with col_b:
            st.markdown("**Final:**")
            for item in dados[-5:]:
                st.text(f"{item['start']:.1f}s: {item['text']}")

st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
