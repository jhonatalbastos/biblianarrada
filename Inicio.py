import streamlit as st
import datetime
import requests
import sys
import os

# Garante que o Python encontre os módulos na raiz
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from modules import database as db

# Configuração da Página
st.set_page_config(
    page_title="Bíblia Narrada - Dashboard",
    page_icon="📖",
    layout="centered"
)

# --- FUNÇÕES AUXILIARES ---

def formatar_referencia(ref_raw, tipo):
    """Limpa e padroniza a referência bíblica."""
    if not ref_raw:
        return tipo
    return ref_raw.strip()

def fetch_liturgia(date_obj):
    """
    Busca a liturgia na API V2 (Railway) respeitando a estrutura de Arrays e Extras.
    """
    # 1. Verifica Cache Local
    date_str_db = date_obj.strftime('%Y-%m-%d')
    cached = db.carregar_liturgia(date_str_db)
    if cached:
        return cached

    # 2. Requisição para API V2
    BASE_URL = "https://liturgia.up.railway.app/v2/"
    params = {
        "dia": date_obj.day,
        "mes": date_obj.month,
        "ano": date_obj.year
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        
        if response.status_code == 404:
            st.warning("Liturgia não encontrada para esta data.")
            return None
            
        response.raise_for_status()
        data = response.json()

        # Extração de Metadados
        cor_liturgica = data.get('cor', 'Verde')
        nome_dia = data.get('liturgia', data.get('dia', 'Dia Litúrgico'))
        
        # Lista final de leituras
        leituras_formatadas = []
        
        obj_leituras = data.get('leituras', {})

        # --- Lógica de Processamento da V2 ---
        
        def processar_secao(chave_json, titulo_padrao):
            itens = obj_leituras.get(chave_json, [])
            if not itens: return
            if isinstance(itens, dict): itens = [itens]
            
            for i, item in enumerate(itens):
                tipo_leitura = item.get('tipo', titulo_padrao)
                
                # Tratamento para múltiplas opções
                if len(itens) > 1 and chave_json not in ['extras']:
                    ref = item.get('referencia', '')
                    if "Breve" in ref or "Breve" in item.get('titulo', ''):
                        sufixo = " (Forma Breve)"
                    elif "Longa" in ref or "Longa" in item.get('titulo', ''):
                        sufixo = " (Forma Longa)"
                    else:
                        sufixo = f" (Opção {i+1})"
                    tipo_leitura += sufixo

                ref_bruta = item.get('referencia', '')
                texto = item.get('texto', '')
                titulo_texto = item.get('titulo', '')

                if chave_json == 'salmo':
                    tipo_leitura = "Salmo Responsorial"
                    refrao = item.get('refrao', '')
                    if refrao:
                        texto = f"Refrão: {refrao}\n\n{texto}"

                if texto:
                    leituras_formatadas.append({
                        'tipo': tipo_leitura,
                        'titulo': titulo_texto if titulo_texto else tipo_leitura,
                        'ref': formatar_referencia(ref_bruta, tipo_leitura),
                        'texto': texto
                    })

        processar_secao('primeiraLeitura', 'Primeira Leitura')
        processar_secao('salmo', 'Salmo Responsorial')
        processar_secao('segundaLeitura', 'Segunda Leitura')
        processar_secao('evangelho', 'Evangelho')
        
        itens_extras = obj_leituras.get('extras', [])
        for item in itens_extras:
            tipo = item.get('tipo', item.get('titulo', 'Leitura Extra'))
            ref = item.get('referencia', '')
            texto = item.get('texto', '')
            titulo_texto = item.get('titulo', '')
            if texto:
                leituras_formatadas.append({
                    'tipo': tipo,
                    'titulo': titulo_texto,
                    'ref': formatar_referencia(ref, tipo),
                    'texto': texto
                })

        if not leituras_formatadas:
            return None

        final_data = {
            'data': date_str_db,
            'nome_dia': nome_dia,
            'cor': cor_liturgica,
            'leituras': leituras_formatadas
        }
        
        db.salvar_liturgia(date_str_db, final_data)
        return final_data

    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

st.title("Bíblia Narrada 🎧")
st.caption("Selecione a liturgia do dia e inicie a produção do vídeo viral.")

# Sidebar: Seleção de Data
st.sidebar.header("Data da Liturgia")
data_selecionada = st.sidebar.date_input(
    "Escolha o dia",
    datetime.date.today()
)

# Processamento
if data_selecionada:
    liturgia = fetch_liturgia(data_selecionada)

    if liturgia:
        # Cabeçalho do Dia
        st.markdown(f"### {liturgia['nome_dia']}")
        
        cores_map = {
            "Verde": "🟢", "Vermelho": "🔴", "Roxo": "🟣", 
            "Branco": "⚪", "Rosa": "🌸", "Preto": "⚫"
        }
        icone_cor = cores_map.get(liturgia['cor'], "⚪")
        st.caption(f"{icone_cor} Cor Litúrgica: **{liturgia['cor']}** | 📅 {data_selecionada.strftime('%d/%m/%Y')}")
        
        st.divider()

        # Exibição das Leituras
        for i, item in enumerate(liturgia['leituras']):
            with st.container():
                # Título da Leitura
                st.subheader(item['tipo'])
                if item['ref']:
                    st.markdown(f"**{item['ref']}**")
                
                # Texto (Expander)
                with st.expander("📖 Ler Texto Completo", expanded=False):
                    st.write(item['texto'])
                
                # --- BOTÃO DE AÇÃO (Conexão com Pages) ---
                col_btn, col_info = st.columns([1, 2])
                with col_btn:
                    # Este é o botão que faz a "mágica" de conexão
                    if st.button(f"🎬 Criar Vídeo Viral", key=f"btn_start_{i}", type="primary"):
                        # 1. Salva a leitura selecionada na Sessão Global
                        st.session_state['leitura_atual'] = item
                        st.session_state['data_atual_str'] = liturgia['data']
                        
                        # 2. Redireciona para a página de Roteiro
                        st.switch_page("pages/1_Roteiro_Viral.py")
                
                with col_info:
                    st.caption("Clique para gerar roteiro, áudio e vídeo desta leitura.")
                
                st.divider()

    else:
        st.info("Nenhuma leitura encontrada. Verifique a conexão ou a data.")
