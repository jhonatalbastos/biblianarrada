import streamlit as st
import os
import sys
import datetime
import requests
import json
import base64
import time
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
prompts = progresso.get('prompts_imagem', {})

# ---------------------------------------------------------------------
# 3. FUNÇÕES DE GERAÇÃO
# ---------------------------------------------------------------------

def gerar_pollinations(prompt, width=1080, height=1920, seed=None):
    """Gera imagem usando Pollinations.ai (Modelo Turbo)."""
    if not seed:
        import random
        seed = random.randint(0, 999999)
    
    prompt_safe = requests.utils.quote(prompt)
    # nologo=true remove a marca d'água do pollinations
    url = f"https://image.pollinations.ai/prompt/{prompt_safe}?model=turbo&width={width}&height={height}&seed={seed}&nologo=true"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"Erro Pollinations: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão Pollinations: {e}")
        return None

def gerar_google_imagen_rest(prompt, api_key, model_version="imagen-3.0-generate-001"):
    """
    Gera imagem usando a API REST do Google (Gemini/Imagen).
    Isso evita problemas de versão da biblioteca Python.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_version}:predict?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Corpo da requisição para o endpoint predict
    data = {
        "instances": [
            {
                "prompt": prompt
            }
        ],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "9:16"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code != 200:
            st.error(f"Erro Google API ({response.status_code}): {response.text}")
            return None
            
        result = response.json()
        
        # O Google retorna a imagem em Base64 dentro de 'predictions'
        if 'predictions' in result and len(result['predictions']) > 0:
            b64_data = result['predictions'][0]['bytesBase64Encoded']
            image_data = base64.b64decode(b64_data)
            return BytesIO(image_data)
        else:
            st.error("A API do Google não retornou nenhuma imagem válida.")
            return None
            
    except Exception as e:
        st.error(f"Erro ao conectar na API do Google: {e}")
        return None

# ---------------------------------------------------------------------
# 4. INTERFACE
# ---------------------------------------------------------------------
st.title("🎨 Passo 2: Geração de Imagens")
st.caption(f"Leitura: {leitura['titulo']}")

if st.button("🔙 Voltar para Roteiro"):
    st.switch_page("pages/1_Roteiro_Viral.py")

st.divider()

if not prompts:
    st.error("❌ Nenhum prompt encontrado. Gere o roteiro primeiro.")
    st.stop()

# --- CONFIGURAÇÃO DO GERADOR ---
st.sidebar.header("⚙️ Configuração IA")
motor_ia = st.sidebar.radio("Escolha o Gerador:", ["Pollinations (Grátis/Rápido)", "Google Imagen (Alta Qualidade)"])

api_key_google = ""
modelo_google = ""

if "Google" in motor_ia:
    st.sidebar.markdown("---")
    st.sidebar.info("Para usar o Google Imagen, você precisa de uma API Key do Google AI Studio.")
    api_key_google = st.sidebar.text_input("Sua Google API Key:", type="password")
    modelo_google = st.sidebar.selectbox(
        "Versão do Modelo:", 
        ["imagen-3.0-generate-001", "imagen-3.0-fast-generate-001"]
    )
    if not api_key_google:
        st.sidebar.warning("⚠️ Insira a API Key para prosseguir.")

col_esq, col_dir = st.columns([1, 1])

# --- COLUNA 1: PROMPTS ---
with col_esq:
    st.subheader("📝 Prompts das Cenas")
    
    p1 = st.text_area("Cena 1 (Abertura)", value=prompts.get('bloco_1', ''), height=120)
    p2 = st.text_area("Cena 2 (Reflexão)", value=prompts.get('bloco_2', ''), height=120)
    p3 = st.text_area("Cena 3 (Aplicação)", value=prompts.get('bloco_3', ''), height=120)
    p4 = st.text_area("Cena 4 (Oração)", value=prompts.get('bloco_4', ''), height=120)
    
    if st.button("💾 Salvar Edições nos Prompts"):
        progresso['prompts_imagem'] = {
            "bloco_1": p1, "bloco_2": p2, "bloco_3": p3, "bloco_4": p4
        }
        db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
        st.success("Prompts atualizados no banco!")

# --- COLUNA 2: GERAÇÃO E RESULTADOS ---
with col_dir:
    st.subheader("🖼️ Gerar Imagens")
    
    # Botão de Ação Principal
    nome_botao = "✨ Gerar Imagens (Pollinations)" if "Pollinations" in motor_ia else "✨ Gerar Imagens (Google)"
    
    if st.button(nome_botao, type="primary"):
        
        # Validação Google
        if "Google" in motor_ia and not api_key_google:
            st.error("Para usar o Google Imagen, preencha a API Key na barra lateral.")
            st.stop()

        folder = os.path.join(parent_dir, "data", "imagens")
        os.makedirs(folder, exist_ok=True)
        novas_imagens = []
        prompts_lista = [p1, p2, p3, p4]
        
        bar = st.progress(0, text="Iniciando...")
        
        for i, prompt_text in enumerate(prompts_lista):
            bar.progress((i * 25), text=f"Gerando cena {i+1} de 4...")
            
            img_io = None
            
            # Lógica de escolha do motor
            if "Pollinations" in motor_ia:
                img_io = gerar_pollinations(prompt_text)
            elif "Google" in motor_ia:
                img_io = gerar_google_imagen_rest(prompt_text, api_key_google, modelo_google)
            
            # Salvar imagem se gerada com sucesso
            if img_io:
                filename = f"img_{data_str}_{i+1}_{int(time.time())}.png"
                path = os.path.join(folder, filename)
                
                with open(path, "wb") as f:
                    f.write(img_io.getbuffer())
                
                novas_imagens.append(path)
            else:
                st.warning(f"Falha ao gerar cena {i+1}. Tentando continuar...")
            
        bar.progress(100, text="Concluído!")
        
        # Salva caminhos no banco
        if len(novas_imagens) > 0:
            progresso['imagens_paths'] = novas_imagens
            progresso['imagens'] = True
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
            st.success(f"Sucesso! {len(novas_imagens)} imagens salvas.")
            st.rerun()
        else:
            st.error("Nenhuma imagem foi gerada. Verifique sua conexão ou API Key.")

    # --- GALERIA DE PREVIEW ---
    imagens_salvas = progresso.get('imagens_paths', [])
    if imagens_salvas:
        st.divider()
        st.write("### Galeria Atual")
        cols_gal = st.columns(2)
        for idx, path in enumerate(imagens_salvas):
            if os.path.exists(path):
                with cols_gal[idx % 2]:
                    st.image(path, caption=f"Cena {idx+1}")
            else:
                st.warning(f"Arquivo não encontrado: {path}")

# Navegação Final
st.divider()
_, _, col_nav = st.columns([1, 2, 1])
with col_nav:
    if progresso.get('imagens'):
        if st.button("Próximo: Áudio TTS ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/3_Audio_TTS.py")
