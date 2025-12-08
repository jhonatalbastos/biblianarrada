import streamlit as st
import os
import sys
import datetime
import requests
from PIL import Image
from io import BytesIO

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

st.set_page_config(page_title="2. Criar Imagens", layout="wide")
st.session_state['current_page_name'] = 'pages/2_Imagens.py'

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

progresso, _ = db.load_status(chave_progresso)

# Recupera prompts do passo anterior
prompts = progresso.get('prompts_imagem', {})

# ---------------------------------------------------------------------
# 3. FUNÇÕES
# ---------------------------------------------------------------------
def gerar_imagem_placeholder(texto, index):
    """Gera uma imagem de placeholder usando serviço online (Lorem Picsum/Placehold)."""
    # Em produção, substitua por DALL-E, Stable Diffusion, etc.
    try:
        url = f"https://placehold.co/1080x1920/202020/FFF.png?text=Cena+{index+1}\n{texto[:20]}..."
        resp = requests.get(url)
        if resp.status_code == 200:
            return BytesIO(resp.content)
    except:
        return None
    return None

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("🎨 Passo 2: Geração de Imagens")
st.caption(f"Leitura: {leitura['titulo']}")

# Navegação Superior
if st.button("🔙 Voltar para Roteiro"):
    st.switch_page("pages/1_Roteiro_Viral.py")

st.divider()

if not prompts:
    st.error("❌ Nenhum prompt de imagem encontrado. Gere o roteiro primeiro.")
    st.stop()

col_esq, col_dir = st.columns([1, 1])

# --- COLUNA 1: PROMPTS ---
with col_esq:
    st.subheader("📝 Prompts (IA)")
    
    p1 = st.text_area("Prompt Cena 1", value=prompts.get('bloco_1', ''), height=100)
    p2 = st.text_area("Prompt Cena 2", value=prompts.get('bloco_2', ''), height=100)
    p3 = st.text_area("Prompt Cena 3", value=prompts.get('bloco_3', ''), height=100)
    p4 = st.text_area("Prompt Cena 4", value=prompts.get('bloco_4', ''), height=100)
    
    if st.button("🔄 Atualizar Prompts no Banco"):
        progresso['prompts_imagem'] = {
            "bloco_1": p1, "bloco_2": p2, "bloco_3": p3, "bloco_4": p4
        }
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
        st.success("Prompts atualizados!")

# --- COLUNA 2: IMAGENS ---
with col_dir:
    st.subheader("🖼️ Resultados")
    
    # Verifica se já existem imagens salvas
    imagens_salvas = progresso.get('imagens_paths', [])
    
    if st.button("✨ Gerar Todas as Imagens (Simulação)", type="primary"):
        with st.spinner("Gerando imagens..."):
            novas_imagens = []
            folder = os.path.join(parent_dir, "data", "imagens")
            os.makedirs(folder, exist_ok=True)
            
            prompts_lista = [p1, p2, p3, p4]
            
            for i, p in enumerate(prompts_lista):
                img_io = gerar_imagem_placeholder(p, i)
                if img_io:
                    filename = f"img_{data_str}_{i+1}.png"
                    path = os.path.join(folder, filename)
                    # Salva no disco
                    with open(path, "wb") as f:
                        f.write(img_io.getbuffer())
                    novas_imagens.append(path)
            
            # SALVA NO BANCO (CRÍTICO PARA O PASSO 6)
            progresso['imagens_paths'] = novas_imagens
            progresso['imagens'] = True  # <--- A CHAVE QUE O PASSO 6 PROCURA
            
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
            st.success("Imagens geradas e salvas!")
            st.rerun()

    # Exibe Galeria
    if imagens_salvas:
        cols = st.columns(2)
        for i, path in enumerate(imagens_salvas):
            if os.path.exists(path):
                with cols[i % 2]:
                    st.image(path, caption=f"Cena {i+1}")
            else:
                st.warning(f"Imagem {i+1} não encontrada no disco.")
                
# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('imagens'):
        if st.button("Próximo: Áudio ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/3_Audio_TTS.py")
