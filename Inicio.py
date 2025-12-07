import streamlit as st
import sys
import os
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CORREÇÃO DE IMPORTAÇÃO (BANCO DE DADOS)
# ---------------------------------------------------------------------
# Garante que encontra o modules.database ou database local
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import modules.database as db
except ImportError:
    try:
        import database as db
    except ImportError:
        st.error("Erro: Banco de dados não encontrado.")
        st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="Início - Bíblia Narrada", layout="wide")

st.title("📅 Seleção da Liturgia")

# ---------------------------------------------------------------------
# 3. BUSCA POR DATA (FUNCIONALIDADE RESTAURADA)
# ---------------------------------------------------------------------
st.markdown("### Escolha a data da leitura")

col_data, col_tipo, col_btn = st.columns([1, 1, 1])

with col_data:
    # O SELETOR DE DATA QUE VOCÊ QUERIA
    data_selecionada = st.date_input("Data:", datetime.today())
    data_str = data_selecionada.strftime('%Y-%m-%d')

with col_tipo:
    tipo_leitura = st.selectbox(
        "Tipo de Leitura:",
        ["Evangelho", "Primeira Leitura", "Segunda Leitura", "Salmo"],
        index=0
    )

with col_btn:
    st.write("") # Espaçamento
    st.write("") 
    if st.button("🚀 Buscar e Iniciar", type="primary", use_container_width=True):
        # Define os dados na sessão para a Página 1 usar
        st.session_state['leitura_atual'] = {
            "tipo": tipo_leitura,
            "titulo": f"Liturgia de {data_selecionada.strftime('%d/%m')}", # Título provisório, a pág 1 puxa o real
            "ref": "Carregando...",
            "texto": "", # A página 1 vai carregar/raspar o texto baseada na data
            "data": data_str
        }
        st.session_state['data_atual_str'] = data_str

        # Cria/Atualiza entrada no Banco de Dados para não dar erro depois
        chave = f"{data_str}-{tipo_leitura}"
        
        # Estrutura inicial vazia (necessária para as páginas de imagem/audio não quebrarem)
        novo_status = {
            "roteiro_pronto": False,
            "imagens_prontas": False,
            "audios_prontos": False,
            "prompts_imagem": {},
            "caminhos_imagens": {},
            "caminhos_audios": {},
            "bloco_leitura": "",
            "bloco_reflexao": "",
            "bloco_aplicacao": "",
            "bloco_oracao": ""
        }
        
        # Inicia no banco (preserva se já existir)
        db.update_status(chave, data_str, tipo_leitura, novo_status, 0)

        # Vai para a página do Roteiro
        st.switch_page("pages/1_Roteiro_Viral.py")

st.divider()

# ---------------------------------------------------------------------
# 4. HISTÓRICO RECENTE (COM A CORREÇÃO DO CRASH)
# ---------------------------------------------------------------------
st.subheader("📂 Continuar Produções Recentes")

producoes = db.load_recent_productions()

if producoes:
    for item in producoes:
        with st.container():
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                st.write(f"📅 **{item['data']}**")
            with c2:
                st.write(f"📖 {item['tipo']}")
            with c3:
                # --- AQUI ESTAVA O ERRO QUE QUEBRAVA O APP ---
                # Correção: Soma apenas valores True, ignora textos de imagem/audio
                etapas = sum(1 for v in item['progresso'].values() if v is True)
                
                if st.button(f"Continuar (Etapa {etapas})", key=item['id']):
                    st.session_state['leitura_atual'] = {
                        "tipo": item['tipo'],
                        "titulo": f"Retomando {item['tipo']}",
                        "data": item['data'],
                        "ref": "", # Será recarregado
                        "texto": ""
                    }
                    st.session_state['data_atual_str'] = item['data']
                    st.switch_page("pages/1_Roteiro_Viral.py")
            st.markdown("---")
else:
    st.info("Nenhuma produção recente encontrada.")
