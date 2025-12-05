import streamlit as st
import json
import re
from datetime import datetime
import os
from groq import Groq

# Configuração da Página
st.set_page_config(
    page_title="Início - Bíblia Narrada",
    page_icon="🙏",
    layout="wide"
)

st.title("🙏 Bíblia Narrada: Planejamento Litúrgico")
st.markdown("---")

# -------------------------------------------------------------------
# 1. Configuração e Inicialização
# -------------------------------------------------------------------

# Inicializa banco de dados na sessão se não existir
if "db" not in st.session_state:
    st.session_state.db = {"canais": {}, "liturgia_atual": None}

# Cliente Groq (tenta pegar a chave dos secrets ou input)
api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

# -------------------------------------------------------------------
# 2. Funções de Processamento de Dados (Parsing & AI)
# -------------------------------------------------------------------

def get_day_name(date_str):
    """Converte '05/12/2025' para 'Sexta-feira'."""
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        days = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        return days[date_obj.weekday()]
    except:
        return "Dia Desconhecido"

def clean_html(raw_html):
    """Remove tags HTML básicas como <br>, <b>."""
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, ' ', raw_html)
    return text.strip()

def extract_book_ref(title, reading_type):
    """
    Extrai a referência do livro (Ex: 'Isaías 29, 17-24') do título completo.
    Usa regras de string para rapidez, mas pode ser refinado via IA.
    """
    # Remove prefixos comuns
    prefixes = [
        "Primeira leitura:", "Segunda leitura:", "Salmo", 
        "Proclamação do Evangelho de Jesus Cristo segundo", 
        "Evangelho de Jesus Cristo segundo", "Leitura do livro"
    ]
    
    clean_title = title
    for p in prefixes:
        if p in clean_title:
            clean_title = clean_title.replace(p, "")
    
    return clean_title.strip(" :-")

def refine_with_groq(text_content, context_type):
    """
    Usa IA para limpar ou resumir textos se necessário.
    Útil para normalizar o texto para o roteiro.
    """
    if not api_key:
        return text_content # Fallback se sem chave
    
    client = Groq(api_key=api_key)
    
    prompt = f"""
    Atue como um editor de textos litúrgicos católicos.
    Sua tarefa é limpar e formatar o seguinte texto do tipo '{context_type}'.
    
    Texto Original: "{text_content}"
    
    Regras:
    1. Remova numerações de versículos misturadas no texto (ex: "17Dentro" -> "Dentro").
    2. Mantenha a reverência e a pontuação correta para leitura em voz alta.
    3. Retorne APENAS o texto limpo, sem introduções.
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"Erro ao refinar com IA: {e}")
        return text_content

# -------------------------------------------------------------------
# 3. Ingestão de Dados (Mock do JSON fornecido)
# -------------------------------------------------------------------

# Aqui simulamos a resposta da API que você forneceu. 
# Em produção, isso seria um request.get(url).json()
raw_data_example = {
    "objective": "A API_LITURGIA_DIARIA visa disponibilizar...",
    "source": "https://sagradaliturgia.com.br/",
    "today": {
        "color": "roxo",
        "date": "05/12/2025",
        "entry_title": "1a. Semana do Advento<br/>Ciclo do Natal"
    },
    "readings": {
        "first_reading": {
            "title": "Primeira leitura: Isaías 29, 17-24",
            "text": "Assim fala o Senhor Deus: 17Dentro de pouco tempo..."
        },
        "gospel": {
            "title": "Proclamação do Evangelho de Jesus Cristo segundo São Mateus:",
            "head_title": "Evangelho de Jesus Cristo segundo São Mateus 9, 27-31", # Usaremos este se disponível
            "text": "Naquele tempo: 27Partindo Jesus, dois cegos o seguiram..."
        },
        "psalm": {
            "title": "Salmo 26 (27)",
            "response": "R: O Senhor é minha luz e salvação.",
            "content_psalm": [
                "- O Senhor é minha luz e salvação...",
                "- Ao Senhor eu peço apenas uma coisa...",
                "- Sei que a bondade do Senhor..."
            ]
        }
    }
}

# -------------------------------------------------------------------
# 4. Interface Principal
# -------------------------------------------------------------------

col_info, col_action = st.columns([2, 1])

with col_info:
    st.info("ℹ️ Este painel carrega a Liturgia Diária e prepara os dados para a criação de roteiros e vídeos.")

with col_action:
    # Simula botão de busca
    if st.button("🔄 Buscar Liturgia de Hoje", type="primary"):
        st.session_state.raw_liturgia = raw_data_example
        st.rerun()

# Verifica se temos dados carregados
if "raw_liturgia" in st.session_state:
    data = st.session_state.raw_liturgia
    today_info = data["today"]
    readings = data["readings"]
    
    # Processamento dos metadados globais
    data_formatada = today_info["date"]
    dia_semana = get_day_name(data_formatada)
    tempo_liturgico = clean_html(today_info["entry_title"])
    cor_liturgica = today_info["color"]

    # Container de Cabeçalho Visual
    with st.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 Data", data_formatada, dia_semana)
        c2.metric("✝️ Tempo Litúrgico", tempo_liturgico.split(" - ")[0])
        c3.metric("🎨 Cor", cor_liturgica.upper())
        c4.metric("📚 Fonte", "Sagrada Liturgia")

    st.markdown("### 📖 Leituras Processadas")
    
    # Preparar estrutura de dados limpa
    structured_readings = []

    # Definição de mapeamento para iterar
    map_keys = {
        "first_reading": "1ª Leitura",
        "second_reading": "2ª Leitura", # Caso exista
        "psalm": "Salmo",
        "gospel": "Evangelho"
    }

    tabs = st.tabs(list(map_keys.values()))

    for i, (key, label) in enumerate(map_keys.items()):
        if key in readings:
            r_data = readings[key]
            
            # 1. Determinar Título/Livro
            if key == "gospel" and "head_title" in r_data:
                raw_title = r_data["head_title"]
            else:
                raw_title = r_data["title"]
            
            livro_ref = extract_book_ref(raw_title, label)
            
            # 2. Determinar Texto
            if key == "psalm":
                # Junta o refrão com as estrofes
                refrao = r_data.get("response", "")
                estrofes = "\n\n".join(r_data.get("content_psalm", []))
                texto_completo = f"{refrao}\n\n{estrofes}"
            else:
                texto_completo = r_data.get("text", "")

            # 3. Estrutura final para o objeto
            item_struct = {
                "tipo_leitura": label,
                "data_completa": f"{dia_semana}, {data_formatada}",
                "livro": livro_ref,
                "tempo_liturgico": tempo_liturgico,
                "texto_original": texto_completo,
                "texto_limpo": None # Será preenchido se usar IA
            }
            
            # UI na Aba
            with tabs[i]:
                st.subheader(f"{label}: {livro_ref}")
                st.caption(f"{dia_semana}, {data_formatada} | {tempo_liturgico}")
                
                txt_col, meta_col = st.columns([3, 1])
                
                with txt_col:
                    st.text_area("Texto Original", texto_completo, height=200, key=f"txt_{key}")
                    
                    # Botão para refinar com IA (Opcional)
                    if st.button(f"✨ Limpar texto com IA ({label})", key=f"btn_ai_{key}"):
                        with st.spinner("A IA está limpando a formatação e números de versículos..."):
                            texto_limpo = refine_with_groq(texto_completo, label)
                            st.session_state[f"clean_{key}"] = texto_limpo
                            item_struct["texto_limpo"] = texto_limpo
                            st.success("Texto refinado!")
                    
                    # Mostra texto limpo se existir
                    if f"clean_{key}" in st.session_state:
                        st.text_area("Texto Pronto para Locução", st.session_state[f"clean_{key}"], height=200)
                        item_struct["texto_limpo"] = st.session_state[f"clean_{key}"]

                with meta_col:
                    st.markdown("**Metadados Extraídos:**")
                    st.json({
                        "Tipo": item_struct["tipo_leitura"],
                        "Data": item_struct["data_completa"],
                        "Livro": item_struct["livro"],
                        "Tempo": item_struct["tempo_liturgico"]
                    })
                    
            structured_readings.append(item_struct)

    # -------------------------------------------------------------------
    # 5. Ação Final: Salvar e Ir para Roteiro
    # -------------------------------------------------------------------
    st.markdown("---")
    col_save, _ = st.columns([1, 4])
    with col_save:
        if st.button("🚀 Usar estes dados no Roteiro", type="primary"):
            # Salva na "Sessão Global" do app
            st.session_state.dados_liturgia_selecionada = structured_readings
            
            # Opcional: Criar automaticamente uma entrada no "Banco de Canais"
            # simulando a criação de uma ideia de vídeo baseada na liturgia
            st.success("Dados enviados para o módulo de Roteiro! Vá para a página '1 - Roteiro Viral'.")
            
else:
    st.warning("Clique em 'Buscar Liturgia' para carregar os dados do dia.")

# Debug (apenas para ver o estado)
# st.write(st.session_state)
