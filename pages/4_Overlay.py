import streamlit as st
import os
import sys
import datetime
from PIL import Image, ImageDraw, ImageFont

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

st.set_page_config(page_title="Configurar Overlay", page_icon="🖼️", layout="wide")
st.session_state['current_page_name'] = 'pages/4_Overlay.py'

# ---------------------------------------------------------------------
# 2. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada. Volte ao Início.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.date.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

progresso, _ = db.load_status(chave_progresso)

# --- Utility Function for Navigation Bar ---
def render_navigation_bar(current_page_title):
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    st.caption(f"📖 Em Produção: **{leitura['tipo']}** ({data_str})")

    cols_nav = st.columns([1, 1, 1, 1, 1, 1]) # Removido 1 coluna
    
    # REMOVIDO "LEGENDAS" DA LISTA
    stages = [
        ('Roteiro', 'roteiro', 'pages/1_Roteiro_Viral.py', '📝', '📝', True),
        ('Imagens', 'imagens', 'pages/2_Imagens.py', '🎨', '🔒', progresso.get('roteiro', False)),
        ('Áudio', 'audio', 'pages/3_Audio_TTS.py', '🔊', '🔒', progresso.get('roteiro', False)),
        ('Overlay', 'overlay', 'pages/4_Overlay.py', '🖼️', '🔒', progresso.get('audio', False)),
        ('Vídeo', 'video', 'pages/6_Video_Final.py', '🎬', '🔒', progresso.get('overlay', False)),
        ('Publicar', 'publicacao', 'pages/7_Publicar.py', '🚀', '🔒', progresso.get('video', False))
    ]

    current_page = st.session_state['current_page_name']
    
    for i, (label, key, page, icon_on, icon_off, base_enabled) in enumerate(stages):
        status = progresso.get(key, False)
        is_current = current_page == page
        
        icon = icon_on if status or is_current else icon_off
        display_icon = f"✅ {icon}" if status and not is_current else icon
        
        enabled = base_enabled
        btn_disabled = not enabled and not status and not is_current
        
        with cols_nav[i]:
            btn_style = "primary" if is_current else "secondary"
            if st.button(display_icon, key=f"nav_btn_{key}", type=btn_style, disabled=btn_disabled, help=label):
                st.switch_page(page)

    st.markdown("---")

render_navigation_bar("🖼️ Configuração de Overlay")

# --- Funções ---
def get_fonts():
    folder = os.path.join(parent_dir, "fonts")
    if not os.path.exists(folder):
        return ["Arial"] 
    fonts = [f for f in os.listdir(folder) if f.endswith(('.ttf', '.otf'))]
    return fonts if fonts else ["Arial"]

def gerar_preview(config):
    W, H = 540, 960
    img = Image.new('RGB', (W, H), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    
    linhas = [l for l in config['textos'] if l]
    
    font_name = config['fonte']
    font_path = os.path.join(parent_dir, "fonts", font_name) if font_name != "Arial" else None
    
    try:
        if font_path and os.path.exists(font_path):
            font_obj = ImageFont.truetype(font_path, config['tamanho_fonte'])
        else:
            font_obj = ImageFont.load_default()
    except Exception as e:
        font_obj = ImageFont.load_default()

    y_start = config['posicao_y']
    espacamento = config['tamanho_fonte'] + 15
    
    for i, linha in enumerate(linhas):
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), linha, font=font_obj)
            text_w = bbox[2] - bbox[0]
        else:
            text_w = draw.textlength(linha, font=font_obj)
            
        x = (W - text_w) / 2
        y = y_start + (i * espacamento)
        
        draw.text((x, y), linha, font=font_obj, fill=config['cor_texto'])

    if config['visualizer']:
        draw.line((50, H - 200, W - 50, H - 200), fill="white", width=2)
        for k in range(60, W - 60, 20):
            import random
            h_bar = random.randint(10, 50)
            draw.line((k, H - 200 - h_bar, k, H - 200 + h_bar), fill="white", width=3)

    return img

# --- Interface ---
col_config, col_preview = st.columns([1, 1])

defaults = st.session_state.get('overlay_defaults', {
    "posicao_y": 150,
    "tamanho": 40,
    "fonte": "Arial",
    "visualizer": True,
    "cor": "#FFFFFF"
})

with col_config:
    st.subheader("📝 Textos Superiores")
    
    txt_1 = st.text_input("Linha 1 (Tipo)", value=leitura['tipo'])
    
    try:
        dt_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
    except ValueError:
        try:
            dt_obj = datetime.datetime.strptime(data_str, "%d/%m/%Y")
        except ValueError:
            dt_obj = datetime.datetime.today()

    try:
        dias_semana = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }
        nome_dia = dias_semana[dt_obj.weekday()]
        data_formatada = f"{nome_dia}, {dt_obj.strftime('%d.%m.%Y')}"
    except:
        data_formatada = data_str

    txt_2 = st.text_input("Linha 2 (Data)", value=data_formatada)
    txt_3 = st.text_input("Linha 3 (Livro/Ref)", value=leitura.get('ref', ''))
    txt_4 = st.text_input("Linha 4 (Tempo/Cor)", value=leitura.get('cor', ''))
    
    st.divider()
    st.subheader("🎨 Estilo")
    
    fontes_disponiveis = get_fonts()
    idx_font = 0
    if defaults['fonte'] in fontes_disponiveis:
        idx_font = fontes_disponiveis.index(defaults['fonte'])
        
    fonte_sel = st.selectbox("Fonte (pasta 'fonts')", options=fontes_disponiveis, index=idx_font)
    
    tamanho = st.slider("Tamanho da Fonte", 10, 100, defaults['tamanho'])
    pos_y = st.slider("Posição Vertical (Y)", 50, 800, defaults['posicao_y'])
    cor = st.color_picker("Cor do Texto", defaults['cor'])
    
    st.divider()
    visualizer = st.checkbox("Adicionar Visualizer (Onda de Áudio)", value=defaults['visualizer'])
    salvar_padrao = st.checkbox("Salvar estes ajustes como padrão", value=True)

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
    st.image(img_prev, width=320, caption="Prévia do Overlay")

st.divider()
if st.button("💾 Salvar e Renderizar Vídeo ➡️", type="primary"):
    st.session_state['overlay_config'] = config_atual
    
    if salvar_padrao:
        st.session_state['overlay_defaults'] = {
            "posicao_y": pos_y, "tamanho": tamanho, "visualizer": visualizer, "fonte": fonte_sel, "cor": cor
        }
    
    progresso['overlay'] = True
    progresso['overlay_dados'] = config_atual
    db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 4)
        
    st.success("Configuração salva!")
    # PULA A PÁGINA DE LEGENDAS
    st.switch_page("pages/6_Video_Final.py")
