import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Configurar Overlay", page_icon="🖼️", layout="wide")

# --- Verificação de Estado ---
if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', 'Hoje')

# --- Funções ---
def get_fonts():
    folder = "fonts"
    if not os.path.exists(folder):
        os.makedirs(folder)
        return ["Arial"] # Fallback se vazio
    fonts = [f for f in os.listdir(folder) if f.endswith(('.ttf', '.otf'))]
    return fonts if fonts else ["Arial"] # Retorna lista ou fallback

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def gerar_preview(config):
    # Cria canvas 9:16 (1080x1920 reduzido para preview 270x480 para rapidez)
    W, H = 540, 960 # Full HD / 2
    img = Image.new('RGB', (W, H), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    
    # Simula linhas de texto
    linhas = config['textos']
    font_path = os.path.join("fonts", config['fonte']) if config['fonte'] != "Arial" else "arial.ttf"
    
    try:
        # Tenta carregar fonte, senão usa default
        font_obj = ImageFont.truetype(font_path, config['tamanho_fonte'])
    except:
        font_obj = ImageFont.load_default()

    y_start = config['posicao_y']
    espacamento = config['tamanho_fonte'] + 10
    
    # Desenha textos
    for i, linha in enumerate(linhas):
        bbox = draw.textbbox((0, 0), linha, font=font_obj)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) / 2 # Centralizado
        y = y_start + (i * espacamento)
        
        draw.text((x, y), linha, font=font_obj, fill=config['cor_texto'])

    # Simula Visualizer (Linha Branca)
    if config['visualizer']:
        draw.line((50, H - 150, W - 50, H - 150), fill="white", width=3)
        # Ondas falsas
        draw.line((W/2 - 50, H - 150 - 20, W/2, H - 150 + 20), fill="white", width=2)
        draw.line((W/2, H - 150 + 20, W/2 + 50, H - 150 - 20), fill="white", width=2)

    return img

# --- Interface ---
st.title("🖼️ Configuração de Overlay")
st.caption(f"Leitura: {leitura['tipo']} | Cor Litúrgica: {leitura.get('cor_liturgica', 'N/A')}")

col_config, col_preview = st.columns([1, 1])

# Carrega defaults salvos ou define novos
defaults = st.session_state.get('overlay_defaults', {
    "posicao_y": 150,
    "tamanho": 30,
    "fonte": 0,
    "visualizer": True
})

with col_config:
    st.subheader("📝 Textos Superiores")
    
    # Definição automática dos textos
    txt_1 = st.text_input("Linha 1 (Tipo)", value=leitura['tipo'])
    txt_2 = st.text_input("Linha 2 (Data)", value=f"{data_str}")
    txt_3 = st.text_input("Linha 3 (Livro/Ref)", value=leitura.get('ref', ''))
    txt_4 = st.text_input("Linha 4 (Tempo/Cor)", value=f"{leitura.get('cor_liturgica', '')}")
    
    st.divider()
    
    st.subheader("🎨 Estilo")
    
    fontes_disponiveis = get_fonts()
    fonte_sel = st.selectbox("Fonte (pasta 'fonts')", options=fontes_disponiveis)
    
    tamanho = st.slider("Tamanho da Fonte", 10, 100, defaults['tamanho'])
    pos_y = st.slider("Posição Vertical (Y)", 50, 800, defaults['posicao_y'])
    cor = st.color_picker("Cor do Texto", "#FFFFFF")
    
    st.divider()
    visualizer = st.checkbox("Adicionar Linha de Áudio (Visualizer)", value=defaults['visualizer'])
    
    salvar_padrao = st.checkbox("Salvar estes ajustes como padrão para o futuro")

with col_preview:
    st.subheader("📱 Preview (9:16)")
    
    config_atual = {
        "textos": [txt_1, txt_2, txt_3, txt_4],
        "fonte": fonte_sel,
        "tamanho_fonte": tamanho,
        "posicao_y": pos_y,
        "cor_texto": cor,
        "visualizer": visualizer
    }
    
    img_prev = gerar_preview(config_atual)
    st.image(img_prev, width=300, caption="Simulação do Vídeo")

# --- Ação Final ---
st.divider()
if st.button("💾 Salvar Configuração de Overlay", type="primary"):
    # Salva na sessão para ser usado pelo Video_Final
    st.session_state['overlay_config'] = config_atual
    
    if salvar_padrao:
        st.session_state['overlay_defaults'] = {
            "posicao_y": pos_y, "tamanho": tamanho, "visualizer": visualizer
        }
    
    # Atualiza Progresso
    chave = f"{data_str}-{leitura['tipo']}"
    if chave in st.session_state.get('progresso_leituras', {}):
        st.session_state['progresso_leituras'][chave]['overlay'] = True
        
    st.success("Configuração salva! Pode ir para Legendas ou Gerar Vídeo.")
