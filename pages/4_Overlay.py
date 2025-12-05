import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Configurar Overlay", page_icon="🖼️", layout="wide")
st.session_state['current_page_name'] = 'pages/4_Overlay.py'

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


# --- Verificação de Estado ---
if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', 'Hoje')

render_navigation_bar("🖼️ Configuração de Overlay")

# --- Funções ---
def get_fonts():
    folder = "fonts"
    if not os.path.exists(folder):
        os.makedirs(folder)
        # Use um nome de arquivo comum que o PIL pode encontrar se a pasta estiver vazia
        # Em produção, você deve garantir que `arial.ttf` ou similar exista se não houver outras.
        return ["Arial"] 
    fonts = [f for f in os.listdir(folder) if f.endswith(('.ttf', '.otf'))]
    return fonts if fonts else ["Arial"]

def gerar_preview(config):
    # Cria canvas 9:16 (540x960)
    W, H = 540, 960
    img = Image.new('RGB', (W, H), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    
    # Simula linhas de texto
    linhas = [l for l in config['textos'] if l] # Remove linhas vazias
    font_path = os.path.join("fonts", config['fonte']) if config['fonte'] != "Arial" and os.path.exists(os.path.join("fonts", config['fonte'])) else None
    
    # Tenta carregar fonte
    try:
        if font_path:
            font_obj = ImageFont.truetype(font_path, config['tamanho_fonte'])
        else:
            font_obj = ImageFont.load_default()
    except Exception as e:
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
        # Desenha a linha horizontal (base do visualizador)
        draw.line((50, H - 150, W - 50, H - 150), fill="white", width=3)

    return img

# --- Interface ---
col_config, col_preview = st.columns([1, 1])

# Carrega defaults salvos ou define novos
defaults = st.session_state.get('overlay_defaults', {
    "posicao_y": 150,
    "tamanho": 30,
    "fonte": "Arial",
    "visualizer": True,
    "cor": "#FFFFFF"
})

with col_config:
    st.subheader("📝 Textos Superiores")
    
    # Definição automática dos textos
    txt_1 = st.text_input("Linha 1 (Tipo)", value=leitura['tipo'])
    
    # Dia da semana, Dia e Mês/Ano
    dia_semana = datetime.datetime.strptime(data_str, "%d/%m/%Y").strftime("%A, %d.%m.%Y").replace('feira', '').replace('sábado', 'Sábado').replace('domingo', 'Domingo').capitalize()
    txt_2 = st.text_input("Linha 2 (Data)", value=dia_semana)
    
    txt_3 = st.text_input("Linha 3 (Livro/Ref)", value=leitura.get('ref', ''))
    txt_4 = st.text_input("Linha 4 (Tempo/Cor)", value=leitura.get('cor_liturgica', ''))
    
    st.divider()
    
    st.subheader("🎨 Estilo")
    
    fontes_disponiveis = get_fonts()
    # Garante que a fonte default esteja na lista, senão usa a primeira
    default_font_idx = fontes_disponiveis.index(defaults['fonte']) if defaults['fonte'] in fontes_disponiveis else 0
    fonte_sel = st.selectbox("Fonte (pasta 'fonts')", options=fontes_disponiveis, index=default_font_idx)
    
    tamanho = st.slider("Tamanho da Fonte", 10, 100, defaults['tamanho'])
    pos_y = st.slider("Posição Vertical (Y)", 50, 800, defaults['posicao_y'])
    cor = st.color_picker("Cor do Texto", defaults['cor'])
    
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
if st.button("💾 Salvar Configuração de Overlay e Prosseguir", type="primary"):
    st.session_state['overlay_config'] = config_atual
    
    if salvar_padrao:
        st.session_state['overlay_defaults'] = {
            "posicao_y": pos_y, "tamanho": tamanho, "visualizer": visualizer, "fonte": fonte_sel, "cor": cor
        }
    
    # Atualiza Progresso
    chave = f"{data_str}-{leitura['tipo']}"
    if chave in st.session_state.get('progresso_leituras', {}):
        st.session_state['progresso_leituras'][chave]['overlay'] = True
        
    st.success("Configuração salva! Indo para Legendas...")
    st.switch_page("pages/5_Legendas.py")
