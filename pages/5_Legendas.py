import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Legendas", page_icon="💬", layout="wide")

if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

# --- Funções ---
def get_fonts():
    folder = "fonts"
    if not os.path.exists(folder): return ["Arial"]
    fonts = [f for f in os.listdir(folder) if f.endswith(('.ttf', '.otf'))]
    return fonts if fonts else ["Arial"]

def preview_combined(overlay_cfg, legenda_cfg):
    # Preview combinado: Overlay + Legenda
    W, H = 540, 960
    img = Image.new('RGB', (W, H), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # 1. Desenha Overlay (Se existir)
    if overlay_cfg:
        y_start = overlay_cfg['posicao_y']
        try:
            f_path = os.path.join("fonts", overlay_cfg['fonte']) if overlay_cfg['fonte'] != "Arial" else "arial.ttf"
            font_ovr = ImageFont.truetype(f_path, overlay_cfg['tamanho_fonte'])
        except: font_ovr = ImageFont.load_default()
        
        for i, linha in enumerate(overlay_cfg['textos']):
            bbox = draw.textbbox((0, 0), linha, font=font_ovr)
            x = (W - (bbox[2] - bbox[0])) / 2
            draw.text((x, y_start + i*40), linha, font=font_ovr, fill=overlay_cfg['cor_texto'])

    # 2. Desenha Legenda (Simulação)
    if legenda_cfg['ativar']:
        txt_legenda = "E então Jesus disse..."
        try:
            f_leg = os.path.join("fonts", legenda_cfg['fonte']) if legenda_cfg['fonte'] != "Arial" else "arial.ttf"
            font_leg = ImageFont.truetype(f_leg, legenda_cfg['tamanho'])
        except: font_leg = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), txt_legenda, font=font_leg)
        x_leg = (W - (bbox[2] - bbox[0])) / 2
        y_leg = H - 200 # Posição inferior fixa ou ajustável
        
        # Fundo da legenda (opcional)
        if legenda_cfg['estilo'] == "Fundo Preto":
             draw.rectangle((x_leg-10, y_leg-5, x_leg+(bbox[2]-bbox[0])+10, y_leg+(bbox[3]-bbox[1])+5), fill="black")
        
        draw.text((x_leg, y_leg), txt_legenda, font=font_leg, fill=legenda_cfg['cor'], stroke_width=2, stroke_fill="black")

    return img

st.title("💬 Configuração de Legendas (Opcional)")

col_opt, col_view = st.columns([1, 1])

with col_opt:
    ativar = st.checkbox("Ativar Legendas no Vídeo", value=True)
    
    fontes = get_fonts()
    fonte = st.selectbox("Fonte da Legenda", options=fontes)
    tamanho = st.slider("Tamanho", 20, 80, 40)
    cor = st.color_picker("Cor da Legenda", "#FFFF00") # Amarelo padrão
    estilo = st.selectbox("Estilo", ["Sombra/Outline", "Fundo Preto", "Simples"])

with col_view:
    st.subheader("Preview Final (Overlay + Legenda)")
    
    # Recupera config do Overlay se existir
    overlay_config = st.session_state.get('overlay_config', None)
    
    legenda_config = {
        "ativar": ativar,
        "fonte": fonte,
        "tamanho": tamanho,
        "cor": cor,
        "estilo": estilo
    }
    
    img = preview_combined(overlay_config, legenda_config)
    st.image(img, width=300)

if st.button("💾 Salvar e Prosseguir"):
    st.session_state['legenda_config'] = legenda_config
    
    # Atualiza Progresso
    data_str = st.session_state.get('data_atual_str', '')
    leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
    chave = f"{data_str}-{leitura_tipo}"
    
    if chave in st.session_state.get('progresso_leituras', {}):
        st.session_state['progresso_leituras'][chave]['legendas'] = True
        
    st.success("Legendas configuradas!")
    st.switch_page("pages/6_Video_Final.py")
