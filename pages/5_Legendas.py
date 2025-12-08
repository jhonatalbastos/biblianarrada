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
    """Obtém duração exata do áudio (FFprobe > Wave)."""
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
    Algoritmo Turbo: Quebra texto em blocos minúsculos (máx 3 palavras).
    Ignora pontuação complexa para focar em velocidade.
    """
    # Limpa espaços
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    
    segments = []
    chunk = []
    
    for word in words:
        chunk.append(word)
        
        # Fecha o bloco se atingir 3 palavras OU se tiver pontuação forte
        # Isso garante que a legenda "corra" e não fique parada
        if len(chunk) >= max_words or word.endswith(('.', '!', '?', ':', ';')):
            segments.append(" ".join(chunk))
            chunk = []
            
    if chunk:
        segments.append(" ".join(chunk))
        
    return segments

def gerar_legendas(texto_usuario, audio_path):
    duration = get_audio_duration(audio_path)
    if duration <= 0: return [], 0
    
    # Usa o texto EXATO que o usuário digitou/colou
    segmentos = split_dynamic_turbo(texto_usuario, max_words=3)
    
    # Se não gerou segmentos (texto vazio), retorna erro
    if not segmentos: return [], duration

    # Calcula o tamanho total (sem espaços) para proporção
    total_chars = sum(len(seg) for seg in segmentos)
    if total_chars == 0: return [], duration
    
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        # Peso proporcional
        weight = len(seg)
        seg_duration = (weight / total_chars) * duration
        
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
st.title("💬 Passo 5: Legendas (Manual)")
st.caption("Controle total sobre o texto e a sincronia.")

if st.button("🔙 Voltar para Overlay"):
    st.switch_page("pages/4_Overlay.py")

st.divider()

if not progresso.get('audio'):
    st.error("⚠️ Áudio não encontrado. Gere o áudio primeiro.")
    st.stop()

audio_path = progresso.get('audio_path', '')
duracao_audio = get_audio_duration(audio_path)

# --- STATUS DO ÁUDIO ---
st.info(f"🔊 Áudio detectado: **{duracao_audio:.2f} segundos**")

# --- ÁREA DE TEXTO LIVRE ---
st.subheader("1. Cole o Texto Completo Aqui")
st.markdown("""
**Instrução:** Apague o que estiver na caixa abaixo e **cole o roteiro completo** (Evangelho + Reflexão + Oração).
*Se a caixa tiver pouco texto, a legenda vai ficar lenta e travar o vídeo.*
""")

# Carrega valor inicial (apenas uma vez)
if 'texto_legenda_manual' not in st.session_state:
    # Tenta pegar do banco, se falhar, deixa vazio para obrigar usuário a colar
    txt_banco = progresso.get('texto_roteiro_completo', '')
    st.session_state['texto_legenda_manual'] = txt_banco

# Caixa de texto sem "value" fixo, controlada pelo session_state
texto_input = st.text_area(
    "Roteiro Completo:",
    key="texto_legenda_manual",
    height=400
)

# --- DIAGNÓSTICO EM TEMPO REAL ---
palavras = len(texto_input.split())
caracteres = len(texto_input)

col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
col_metrics1.metric("Palavras no Texto", palavras)
col_metrics2.metric("Caracteres", caracteres)
col_metrics3.metric("Duração Áudio", f"{duracao_audio:.1f}s")

# Alerta visual se houver discrepância
if duracao_audio > 30 and palavras < 50:
    st.error("🚨 **ALERTA:** Você tem muito áudio (+30s) para pouquíssimo texto (-50 palavras). A legenda VAI ficar lenta. Por favor, cole o texto completo acima!")
    pode_gerar = False
else:
    st.success("✅ Proporção Texto/Áudio parece correta.")
    pode_gerar = True

st.divider()

# --- BOTÃO DE GERAR ---
if st.button("⚡ Gerar Legendas (Modo Turbo)", type="primary", disabled=not pode_gerar):
    with st.spinner("Processando..."):
        # 1. Gera as legendas
        legendas, dur = gerar_legendas(texto_input, audio_path)
        
        if legendas:
            # 2. Salva no banco
            progresso['legendas_dados'] = legendas
            progresso['legendas'] = True
            progresso['texto_roteiro_completo'] = texto_input # Atualiza o banco com o texto que você colou
            
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
            
            st.success(f"Sucesso! Criados {len(legendas)} segmentos de legenda.")
            st.rerun()
        else:
            st.error("Erro ao processar legendas.")

# --- VISUALIZAÇÃO DOS RESULTADOS ---
if progresso.get('legendas') and progresso.get('legendas_dados'):
    dados = progresso['legendas_dados']
    st.divider()
    
    st.subheader(f"📊 Resultado: {len(dados)} blocos de legenda")
    st.caption("Verifique se o tempo final (última linha) bate com o tempo do áudio.")

    # Tabela simples para conferência
    with st.expander("Ver todas as linhas de tempo", expanded=True):
        # Mostra em formato de tabela simples
        tabela_view = []
        for item in dados:
            tabela_view.append({
                "Início (s)": f"{item['start']:.2f}",
                "Fim (s)": f"{item['end']:.2f}",
                "Texto": item['text']
            })
        st.table(tabela_view[:10]) # Mostra as 10 primeiras
        if len(dados) > 10:
            st.write(f"... e mais {len(dados)-10} linhas.")
            st.write(f"**Última Linha:** [{dados[-1]['start']:.2f}s - {dados[-1]['end']:.2f}s] {dados[-1]['text']}")

st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
