import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Legendas", page_icon="💬", layout="wide")
st.session_state['current_page_name'] = 'pages/5_Legendas.py'

# --- Utility Function for Navigation Bar (Identical in all pages 1-7) ---
def render_navigation_bar(current_page_title):
    progresso_leituras = st.session_state.get('progresso_leituras', {})
    leitura_atual = st.session_state.get('leitura_atual')
    data_atual_str = st.session_state.get('data_atual_str')
    
    # Check for selected video
    if not leitura_atual or not data_atual_str:
        st.error("Nenhuma leitura selecionada. Por favor, volte ao Dashboard (Início).")
        if st.button("🏠 Voltar ao Início"):
            st.switch_page("Inicio.py")
        st.stop()
        return

    # Key for the currently active production
    chave_atual = f"{data_atual_str}-{leitura_atual['tipo']}"
    progresso = progresso_leituras.get(chave_atual, {})
    
    # --- Rótulo e Título ---
    st.markdown("---")
    st.markdown(f"## {current_page_title}")
    st.caption(f"📖 Em Produção: **{leitura_atual['tipo']}** ({data_atual_str}) - *Ref: {leitura_atual.get('ref', '')}*")

    # --- Layout da Barra de Navegação de Etapas ---
    cols_nav = st.columns([1, 1, 1, 1, 1, 1, 1])
    
    # Check if the mandatory assets for the subsequent steps are ready
    midia_pronta = progresso.get('imagens', False) and progresso.get('audio', False)

    stages = [
        ('Roteiro', 'roteiro', 'pages/1_Roteiro_Viral.py', '📝', '📝', True),
        ('Imagens', 'imagens', 'pages/2_Imagens.py', '🎨', '🔒', progresso.get('roteiro', False)),
        ('Áudio', 'audio', 'pages/3_Audio_TTS.py', '🔊', '🔒', progresso.get('roteiro', False)),
        ('Overlay', 'overlay', 'pages/4_Overlay.py', '🖼️', '🔒', midia_pronta),
        ('Legendas', 'legendas', 'pages/5_Legendas.py', '💬', '🔒', midia_pronta),
        ('Vídeo', 'video', 'pages/6_Video_Final.py', '🎬', '🔒', midia_pronta),
        ('Publicar', 'publicacao', 'pages/7_Publicar.py', '🚀', '🔒', progresso.get('video', False))
    ]

    # Render Buttons
    current_page = st.session_state['current_page_name']
    
    for i, (label, key, page, icon_on, icon_off, base_enabled) in enumerate(stages):
        status = progresso.get(key, False)
        is_current = current_page == page
        
        icon = icon_on if status or is_current else icon_off
        display_icon = f"✅ {icon}" if status and not is_current else icon
        
        # Enable logic
        enabled = base_enabled
        btn_disabled = not enabled and not status and not is_current
        
        with cols_nav[i]:
            btn_style = "primary" if is_current else "secondary"
            if st.button(display_icon, key=f"nav_btn_{key}", type=btn_style, disabled=btn_disabled, help=f"{label} ({'Pronto' if status else 'Pendente'})"):
                st.switch_page(page)

    st.markdown("---")
# --- End Utility Function ---


if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

render_navigation_bar("💬 Configuração de Legendas (Opcional)")

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
    
    # 1. Desenha Overlay (Reutiliza a lógica do 4_Overlay.py)
    if overlay_cfg:
        linhas = [l for l in overlay_cfg['textos'] if l]
        y_start = overlay_cfg['posicao_y']
        
        font_path = os.path.join("fonts", overlay_cfg['fonte']) if overlay_cfg['fonte'] != "Arial" and os.path.exists(os.path.join("fonts", overlay_cfg['fonte'])) else None
        try:
            if font_path:
                font_ovr = ImageFont.truetype(font_path, overlay_cfg['tamanho_fonte'])
            else:
                font_ovr = ImageFont.load_default()
        except: font_ovr = ImageFont.load_default()

        espacamento = overlay_cfg['tamanho_fonte'] + 10

        for i, linha in enumerate(linhas):
            bbox = draw.textbbox((0, 0), linha, font=font_ovr)
            text_w = bbox[2] - bbox[0]
            x = (W - text_w) / 2
            y = y_start + (i * espacamento)
            draw.text((x, y), linha, font=font_ovr, fill=overlay_cfg['cor_texto'])
            
        if overlay_cfg.get('visualizer'):
            draw.line((50, H - 150, W - 50, H - 150), fill="white", width=3)


    # 2. Desenha Legenda (Simulação)
    if legenda_cfg['ativar']:
        txt_legenda = "E então Jesus disse: 'A colheita é grande, mas os trabalhadores são poucos. Peçam, pois, ao Senhor da colheita que mande trabalhadores para a sua colheita'."
        
        font_path_leg = os.path.join("fonts", legenda_cfg['fonte']) if legenda_cfg['fonte'] != "Arial" and os.path.exists(os.path.join("fonts", legenda_cfg['fonte'])) else None
        try:
            if font_path_leg:
                font_leg = ImageFont.truetype(font_path_leg, legenda_cfg['tamanho'])
            else:
                font_leg = ImageFont.load_default()
        except: font_leg = ImageFont.load_default()
        
        # Simulação de quebra de linha (rudimentar)
        linhas_leg = [txt_legenda[:70], txt_legenda[70:140] + "...", ""]
        
        y_leg_start = H - 250 
        
        for idx, linha_leg in enumerate(linhas_leg):
            if not linha_leg: continue
            
            bbox = draw.textbbox((0, 0), linha_leg, font=font_leg)
            text_w = bbox[2] - bbox[0]
            x_leg = (W - text_w) / 2
            y_leg = y_leg_start + (idx * (legenda_cfg['tamanho'] + 10))
            
            # Fundo da legenda
            if legenda_cfg['estilo'] == "Fundo Preto":
                 draw.rectangle((x_leg-10, y_leg-5, x_leg+(bbox[2]-bbox[0])+10, y_leg+(bbox[3]-bbox[1])+5), fill="black")
            
            # Desenha texto (outline/stroke apenas se for o estilo)
            stroke_width = 2 if legenda_cfg['estilo'] == "Sombra/Outline" else 0
            draw.text((x_leg, y_leg), linha_leg, font=font_leg, fill=legenda_cfg['cor'], stroke_width=stroke_width, stroke_fill="black")

    return img

# --- Interface ---
col_opt, col_view = st.columns([1, 1])

# Carrega defaults salvos
defaults = st.session_state.get('legenda_defaults', {
    "ativar": True, "fonte": "Arial", "tamanho": 40, "cor": "#FFFF00", "estilo": "Sombra/Outline"
})

with col_opt:
    ativar = st.checkbox("Ativar Legendas no Vídeo", value=defaults['ativar'])
    
    fontes = get_fonts()
    default_font_idx = fontes.index(defaults['fonte']) if defaults['fonte'] in fontes else 0
    fonte = st.selectbox("Fonte da Legenda", options=fontes, index=default_font_idx)
    
    tamanho = st.slider("Tamanho", 20, 80, defaults['tamanho'])
    cor = st.color_picker("Cor da Legenda", defaults['cor']) 
    estilo = st.selectbox("Estilo", ["Sombra/Outline", "Fundo Preto", "Simples"], index=["Sombra/Outline", "Fundo Preto", "Simples"].index(defaults['estilo']))
    
    salvar_padrao = st.checkbox("Salvar estes ajustes de legenda como padrão", value=False)


# Recupera config do Overlay se existir
overlay_config = st.session_state.get('overlay_config', None)
if not overlay_config:
    st.warning("⚠️ Overlay não configurado. O preview não mostrará os textos superiores.")
    
legenda_config = {
    "ativar": ativar,
    "fonte": fonte,
    "tamanho": tamanho,
    "cor": cor,
    "estilo": estilo
}

with col_view:
    st.subheader("Preview Final (Overlay + Legenda)")
    img = preview_combined(overlay_config, legenda_config)
    st.image(img, width=300)

if st.button("💾 Salvar e Prosseguir para Vídeo Final", type="primary"):
    st.session_state['legenda_config'] = legenda_config
    
    if salvar_padrao:
        st.session_state['legenda_defaults'] = legenda_config
    
    # Atualiza Progresso
    data_str = st.session_state.get('data_atual_str', '')
    leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
    chave = f"{data_str}-{leitura_tipo}"
    
    if chave in st.session_state.get('progresso_leituras', {}):
        st.session_state['progresso_leituras'][chave]['legendas'] = True
        
    st.success("Legendas configuradas! Indo para Vídeo Final...")
    st.switch_page("pages/6_Video_Final.py")
