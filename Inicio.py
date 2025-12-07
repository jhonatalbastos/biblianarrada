import streamlit as st
import datetime
import requests
from modules import database as db  # CORREÇÃO: Importando corretamente da pasta 'modules'
# import audio_generator as ag # Descomente se tiver o gerador de áudio

# Configuração da Página
st.set_page_config(
    page_title="Bíblia Narrada",
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
        # st.toast(f"Carregado do cache: {date_str_db}", icon="💾")
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
        
        # Acesso seguro ao objeto 'leituras'
        obj_leituras = data.get('leituras', {})

        # --- Lógica de Processamento da V2 (Arrays) ---
        
        def processar_secao(chave_json, titulo_padrao):
            """Processa uma chave (que deve ser uma lista) do JSON."""
            itens = obj_leituras.get(chave_json, [])
            
            # Se vier vazio ou None, ignora
            if not itens: 
                return

            # Garante que é lista (caso a API mude comportamento)
            if isinstance(itens, dict): itens = [itens]
            
            for i, item in enumerate(itens):
                # Define o Tipo/Título da seção
                # Prioridade: 'tipo' (ex: "Terceira Leitura") > titulo_padrao
                tipo_leitura = item.get('tipo', titulo_padrao)
                
                # Se houver mais de uma opção para a mesma leitura (ex: Breve/Longa)
                if len(itens) > 1 and chave_json not in ['extras']:
                    # Tenta pegar distinção no título ou referência
                    ref = item.get('referencia', '')
                    if "Breve" in ref or "Breve" in item.get('titulo', ''):
                        sufixo = " (Forma Breve)"
                    elif "Longa" in ref or "Longa" in item.get('titulo', ''):
                        sufixo = " (Forma Longa)"
                    else:
                        sufixo = f" (Opção {i+1})"
                    tipo_leitura += sufixo

                # Extração dos dados
                ref_bruta = item.get('referencia', '')
                texto = item.get('texto', '')
                titulo_texto = item.get('titulo', '')

                # Tratamento especial para Salmo (Refrão)
                if chave_json == 'salmo':
                    tipo_leitura = "Salmo Responsorial" # Força o nome padrão
                    refrao = item.get('refrao', '')
                    if refrao:
                        texto = f"Refrão: {refrao}\n\n{texto}"

                # Adiciona à lista final se tiver texto
                if texto:
                    leituras_formatadas.append({
                        'tipo': tipo_leitura,
                        'titulo': titulo_texto if titulo_texto else tipo_leitura,
                        'ref': formatar_referencia(ref_bruta, tipo_leitura),
                        'texto': texto
                    })

        # Ordem Litúrgica Padrão
        processar_secao('primeiraLeitura', 'Primeira Leitura')
        processar_secao('salmo', 'Salmo Responsorial')
        processar_secao('segundaLeitura', 'Segunda Leitura')
        processar_secao('evangelho', 'Evangelho')
        
        # Ordem para Vigílias e Extras (A chave 'extras' contém lista com 'tipo')
        # Na V2, 'tipo' define se é "Terceira Leitura", "Epístola", etc.
        # Se não tiver 'tipo', usamos o 'titulo' (ex: "Benção do fogo")
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
        
        # Salva no cache
        db.salvar_liturgia(date_str_db, final_data)
        return final_data

    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

st.title("Bíblia Narrada 🎧")

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
        
        # Badge de Cor Litúrgica
        cores_map = {
            "Verde": "🟢", "Vermelho": "🔴", "Roxo": "🟣", 
            "Branco": "⚪", "Rosa": "🌸", "Preto": "⚫"
        }
        icone_cor = cores_map.get(liturgia['cor'], "⚪")
        st.caption(f"{icone_cor} Cor Litúrgica: **{liturgia['cor']}** | 📅 {data_selecionada.strftime('%d/%m/%Y')}")
        
        st.divider()

        # Exibição das Leituras
        for i, item in enumerate(liturgia['leituras']):
            # Container visual para cada leitura
            with st.container():
                st.subheader(item['tipo'])
                if item['ref']:
                    st.markdown(f"**{item['ref']}**")
                
                # Expander para o texto (padrão expandido ou não, conforme preferência)
                with st.expander("📖 Ler Texto", expanded=True):
                    st.write(item['texto'])
                
                # --- ÁREA DE ÁUDIO ---
                # Aqui entra a lógica de gerar o áudio. 
                # O ID único é importante para o Streamlit não confundir os botões
                
                col_audio, col_vazia = st.columns([1, 2])
                with col_audio:
                    if st.button(f"🎧 Ouvir {item['tipo']}", key=f"btn_{i}"):
                        st.info("Gerando áudio... (Implementar conexão com audio_generator)")
                        # Exemplo de integração:
                        # audio_path = ag.gerar_audio(item['texto'], f"{liturgia['data']}_{i}")
                        # st.audio(audio_path)
                
                st.divider()

    else:
        st.info("Nenhuma leitura encontrada para exibir. Verifique sua conexão ou se a data é válida.")