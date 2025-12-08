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
# 3. FUNÇÕES DE PROCESSAMENTO
# ---------------------------------------------------------------------

def get_audio_duration(file_path):
    """Obtém duração via ffprobe (mais robusto) ou wave (fallback)."""
    # Tenta FFprobe primeiro (precisão)
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        # Fallback para Wave
        try:
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except:
            return 0.0

def split_dynamic_v2(text, max_words=4):
    """
    Algoritmo Otimizado para estilo TikTok/Reels.
    - Mantém média de 3-4 palavras.
    - Quebra forçada em pontuações fortes (. ! ?).
    - Tenta não separar artigos de substantivos se possível (simples).
    """
    # Limpeza inicial
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Primeiro, divide por pontuação forte para garantir que frases não se misturem
    # Ex: "Glória a vós, Senhor! Naquele tempo..." -> ["Glória a vós, Senhor!", "Naquele tempo..."]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    final_segments = []
    
    for sentence in sentences:
        if not sentence: continue
        
        words = sentence.split()
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            
            # Condições para fechar o bloco:
            # 1. Atingiu limite de palavras
            # 2. A palavra tem pontuação final (ex: "Senhor!")
            # 3. A palavra tem pontuação de pausa (ex: "Lucas,") E já temos pelo menos 2 palavras
            
            has_end_punct = word.endswith(('.', '!', '?'))
            has_pause_punct = word.endswith((',', ':', ';'))
            
            should_break = False
            if len(current_chunk) >= max_words:
                should_break = True
            elif has_end_punct:
                should_break = True
            elif has_pause_punct and len(current_chunk) >= 2:
                should_break = True
                
            if should_break:
                final_segments.append(" ".join(current_chunk))
                current_chunk = []
        
        # Adiciona o resto da frase
        if current_chunk:
            final_segments.append(" ".join(current_chunk))
            
    return final_segments

def gerar_legendas_proporcionais(texto_completo, audio_path):
    """Distribui o tempo do áudio proporcionalmente aos caracteres."""
    duration = get_audio_duration(audio_path)
    if duration <= 0: return [], 0
    
    segmentos = split_dynamic_v2(texto_completo, max_words=4)
    
    # Calcula peso visual (número de caracteres)
    # Adicionamos um peso extra fixo por segmento para compensar o tempo de leitura mental
    total_weight = sum(len(seg) for seg in segmentos)
    
    if total_weight == 0: return [], duration
    
    legendas = []
    current_time = 0.0
    
    for seg in segmentos:
        # O tempo de cada segmento é a fração do seu tamanho no total
        weight = len(seg)
        seg_duration = (weight / total_weight) * duration
        
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
st.title("💬 Passo 5: Legendas (Dinâmicas)")

if st.button("🔙 Voltar para Overlay"):
    st.switch_page("pages/4_Overlay.py")

st.divider()

if not progresso.get('audio'):
    st.error("⚠️ Áudio não encontrado. Gere o áudio primeiro.")
    st.stop()

# --- ÁREA DE TEXTO (CRUCIAL: O USUÁRIO DEVE VER O TEXTO COMPLETO) ---
st.subheader("1. Verifique o Texto")
st.info("Este é o texto que será sincronizado. Se estiver incompleto, cole o texto total aqui.")

# Recupera texto (Prioridade: Texto Editado > Texto Completo > Blocos Concatenados)
texto_inicial = progresso.get('texto_roteiro_completo', '')
if not texto_inicial or len(texto_inicial) < 50:
    # Se estiver vazio ou muito curto, tenta reconstruir dos blocos
    b1 = progresso.get('bloco_leitura', '')
    b2 = progresso.get('bloco_reflexao', '')
    b3 = progresso.get('bloco_aplicacao', '')
    b4 = progresso.get('bloco_oracao', '')
    texto_inicial = f"{b1}\n\n{b2}\n\n{b3}\n\n{b4}".strip()

texto_editavel = st.text_area("Texto para Sincronia", value=texto_inicial, height=300)

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.subheader("2. Estilo")
    # Apenas informativo, pois o algoritmo v2 já é o dinâmico
    st.success("Modo Ativo: 🚀 Dinâmico (Reels/TikTok)")
    st.caption("Quebra automática em 3-4 palavras.")

with col_dir:
    st.subheader("3. Gerar")
    audio_path = progresso.get('audio_path')
    
    if st.button("⚡ Gerar Legendas", type="primary"):
        if not audio_path or not os.path.exists(audio_path):
            st.error("Arquivo de áudio não encontrado.")
        else:
            # Validação de Segurança
            if len(texto_editavel) < 100:
                st.warning(f"⚠️ Atenção: Seu texto tem apenas {len(texto_editavel)} caracteres. Se o áudio for longo, as legendas ficarão lentas demais.")
            
            with st.spinner("Processando..."):
                # Salva o texto editado para garantir consistência
                progresso['texto_roteiro_completo'] = texto_editavel
                
                legendas, duracao = gerar_legendas_proporcionais(texto_editavel, audio_path)
                
                if legendas:
                    progresso['legendas_dados'] = legendas
                    progresso['legendas'] = True
                    progresso['legenda_config'] = {"estilo": "dynamic"}
                    
                    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 5)
                    st.success(f"Legendas geradas! (Áudio: {duracao:.1f}s | Blocos: {len(legendas)})")
                    st.rerun()
                else:
                    st.error("Erro ao gerar. Verifique o áudio.")

# --- Visualização ---
if progresso.get('legendas') and progresso.get('legendas_dados'):
    dados = progresso['legendas_dados']
    st.divider()
    st.markdown(f"### ✅ Resultado ({len(dados)} linhas)")
    
    # Mostra os primeiros itens para conferência
    cols_preview = st.columns(3)
    for i in range(min(6, len(dados))):
        item = dados[i]
        with cols_preview[i%3]:
            st.info(f"⏱️ {item['start']:.2f} - {item['end']:.2f}\n\n**{item['text']}**")

# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('legendas'):
        if st.button("Próximo: Renderizar Vídeo ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/6_Video_Final.py")
