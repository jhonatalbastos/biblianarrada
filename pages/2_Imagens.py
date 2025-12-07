import streamlit as st
import sys
import os
import requests
import random
from datetime import datetime
from PIL import Image
from urllib.parse import quote

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="2. Imagens Visuais", layout="wide")

# ---------------------------------------------------------------------
# 3. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega status atual do banco
progresso, em_producao = db.load_status(chave_progresso)

# Recupera os prompts gerados no passo anterior
prompts_salvos = progresso.get('prompts_imagem', {})

# ---------------------------------------------------------------------
# 4. FUNÇÕES UTILITÁRIAS (POLLINATIONS.AI)
# ---------------------------------------------------------------------

def salvar_imagem_local(url_imagem, nome_arquivo):
    """
    Baixa a imagem da URL e salva em uma pasta local 'generated_images'.
    Retorna o caminho relativo para salvar no banco.
    """
    try:
        # Cria estrutura de pastas: generated_images/ANO-MES-DIA/TIPO_LEITURA/
        pasta_destino = os.path.join(parent_dir, "generated_images", data_str, leitura['tipo'])
        os.makedirs(pasta_destino, exist_ok=True)
        
        caminho_completo = os.path.join(pasta_destino, nome_arquivo)
        
        # Faz o download da imagem
        response = requests.get(url_imagem)
        if response.status_code == 200:
            with open(caminho_completo, 'wb') as f:
                f.write(response.content)
            return caminho_completo
        else:
            st.error(f"Erro ao baixar imagem: Status {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erro ao salvar imagem: {e}")
        return None

def gerar_imagem_pollinations(prompt):
    """
    Gera imagem usando Pollinations.ai (Gratuito e Rápido).
    Formato forçado: 9:16 (720x1280).
    """
    try:
        # Limpa e encoda o prompt para URL
        prompt_clean = prompt.replace("\n", " ").strip()
        prompt_encoded = quote(prompt_clean)
        
        # Gera uma seed aleatória para garantir variedade
        seed = random.randint(0, 999999)
        
        # Constrói a URL do Pollinations
        # model=flux (Geralmente o melhor/mais rápido atual deles)
        # width=720, height=1280 (Proporção 9:16)
        url = f"https://pollinations.ai/p/{prompt_encoded}?width=720&height=1280&seed={seed}&model=flux&nologo=true"
        
        return url
    except Exception as e:
        st.error(f"Erro na construção da URL Pollinations: {e}")
        return None

# ---------------------------------------------------------------------
# 5. INTERFACE
# ---------------------------------------------------------------------

st.title("🎨 Passo 2: Criação de Imagens (Pollinations)")

# Header
cols_header = st.columns([3, 1])
with cols_header[0]:
    st.markdown(f"**Leitura:** {leitura['titulo']}")
    st.caption("Gerador: Pollinations AI | Formato: 9:16 (Vertical)")
with cols_header[1]:
    if st.button("🔙 Voltar ao Roteiro"):
        st.switch_page("pages/1_Roteiro_Viral.py")

st.divider()

# Verifica se existem prompts
if not prompts_salvos:
    st.warning("⚠️ Não foram encontrados prompts de imagem. Volte ao Passo 1 e gere o roteiro com IA.")
    st.stop()

# Inicializa dicionário de caminhos de imagem no progresso se não existir
if 'caminhos_imagens' not in progresso:
    progresso['caminhos_imagens'] = {}

# --- CRIAÇÃO DAS ABAS PARA OS 4 BLOCOS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Leitura", "2. Reflexão", "3. Aplicação", "4. Oração"])

def renderizar_aba_imagem(tab_obj, chave_bloco, titulo_bloco):
    with tab_obj:
        st.subheader(f"🖼️ Imagem: {titulo_bloco}")
        
        col_txt, col_img = st.columns([1, 1])
        
        # --- COLUNA DA ESQUERDA: PROMPT E GERAÇÃO ---
        with col_txt:
            prompt_padrao = prompts_salvos.get(chave_bloco, "")
            prompt_editavel = st.text_area(
                "Prompt (Inglês - Editável):", 
                value=prompt_padrao, 
                height=200,
                key=f"txt_{chave_bloco}",
                help="O Pollinations entende melhor prompts em inglês."
            )
            
            if st.button(f"✨ Gerar Imagem (Turbo) - {titulo_bloco}", key=f"btn_{chave_bloco}", type="primary"):
                with st.spinner("Gerando imagem via Pollinations..."):
                    # 1. Obtém a URL gerada
                    url_gerada = gerar_imagem_pollinations(prompt_editavel)
                    
                    if url_gerada:
                        # 2. Baixa e salva localmente
                        nome_arquivo = f"{chave_bloco}.png"
                        caminho_salvo = salvar_imagem_local(url_gerada, nome_arquivo)
                        
                        if caminho_salvo:
                            progresso['caminhos_imagens'][chave_bloco] = caminho_salvo
                            # Atualiza prompt caso tenha sido editado
                            progresso['prompts_imagem'][chave_bloco] = prompt_editavel
                            
                            # Salva no banco
                            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
                            st.success("Imagem salva com sucesso!")
                            st.rerun()

        # --- COLUNA DA DIREITA: VISUALIZAÇÃO ---
        with col_img:
            caminho_existente = progresso['caminhos_imagens'].get(chave_bloco)
            
            if caminho_existente and os.path.exists(caminho_existente):
                # Exibe a imagem salva
                image = Image.open(caminho_existente)
                st.image(image, caption=f"Imagem Salva (9:16) - {titulo_bloco}", use_container_width=True)
            else:
                st.info("Nenhuma imagem gerada ainda.")
                # Placeholder visual
                st.markdown(
                    """
                    <div style="border: 2px dashed #ccc; padding: 100px; text-align: center; color: #ccc;">
                        Visualização 9:16
                    </div>
                    """, unsafe_allow_html=True
                )

# Renderiza as 4 abas
renderizar_aba_imagem(tab1, "bloco_1", "Bloco 1 (Leitura)")
renderizar_aba_imagem(tab2, "bloco_2", "Bloco 2 (Reflexão)")
renderizar_aba_imagem(tab3, "bloco_3", "Bloco 3 (Aplicação)")
renderizar_aba_imagem(tab4, "bloco_4", "Bloco 4 (Oração)")

# ---------------------------------------------------------------------
# 6. VERIFICAÇÃO FINAL E NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()

# Verifica se todas as 4 imagens existem
imgs = progresso.get('caminhos_imagens', {})
tem_todas = all(k in imgs for k in ["bloco_1", "bloco_2", "bloco_3", "bloco_4"])

col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    if tem_todas:
        if st.button("Próximo: Gerar Áudios ➡️", type="primary", use_container_width=True):
            # Marca etapa como concluída no banco
            progresso['imagens_prontas'] = True
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 2)
            st.switch_page("pages/3_Audios.py")
    else:
        st.button("Próximo ➡️", disabled=True, use_container_width=True, help="Gere as 4 imagens para continuar.")
