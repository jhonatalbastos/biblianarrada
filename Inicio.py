import streamlit as st
import sys
import os
import json
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES (ROBUSTO)
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Tenta importar o banco de dados de diferentes locais para evitar erros
try:
    # Tenta primeiro da pasta modules (padrão do projeto atual)
    import modules.database as db
except ImportError:
    try:
        # Se falhar, tenta da raiz (padrão antigo)
        import database as db
    except ImportError:
        st.error("🚨 Erro Crítico: O arquivo 'database.py' não foi encontrado nem na pasta raiz nem em 'modules/'. Verifique a estrutura.")
        st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Bíblia Narrada - Studio",
    page_icon="🎬",
    layout="wide"
)

# ---------------------------------------------------------------------
# 3. INTERFACE PRINCIPAL
# ---------------------------------------------------------------------

st.title("🎬 Bíblia Narrada Studio")
st.markdown("### Painel de Controle e Início Rápido")

st.divider()

# --- ÁREA DE CRIAÇÃO DE NOVA LEITURA ---
col_new_1, col_new_2 = st.columns([2, 1])

with col_new_1:
    st.info("Comece aqui criando uma nova automação para hoje.")
    
    # Formulário simples para iniciar
    with st.form("nova_producao"):
        st.subheader("🚀 Nova Produção")
        
        # Seleção do Tipo de Leitura
        tipo_leitura = st.selectbox(
            "Tipo de Conteúdo:",
            ["Salmos", "Provérbios", "Parábolas", "Histórias", "Devocional"],
            index=0
        )
        
        # Input do Texto Bíblico ou Referência
        referencia = st.text_input("Referência ou Título (Ex: Salmo 23, O Filho Pródigo):")
        
        # Botão de Submit
        submitted = st.form_submit_button("Iniciar Produção ✨")
        
        if submitted and referencia:
            # 1. Define dados iniciais
            data_hoje = datetime.today().strftime('%Y-%m-%d')
            novo_status = {
                "roteiro_pronto": False,
                "imagens_prontas": False,
                "audios_prontos": False,
                "video_pronto": False,
                "prompts_imagem": {},
                "caminhos_imagens": {},
                "caminhos_audios": {},
                "bloco_leitura": "",
                "bloco_reflexao": "",
                "bloco_aplicacao": "",
                "bloco_oracao": ""
            }
            
            # 2. Salva no Session State
            st.session_state['leitura_atual'] = {
                "tipo": tipo_leitura,
                "titulo": referencia,
                "data": data_hoje
            }
            st.session_state['data_atual_str'] = data_hoje
            
            # 3. Cria entrada inicial no JSON (Database)
            chave = f"{data_hoje}-{tipo_leitura}"
            db.update_status(chave, data_hoje, tipo_leitura, novo_status, 0)
            
            st.success(f"Projeto '{referencia}' iniciado!")
            
            # 4. Redireciona para o Roteiro
            st.switch_page("pages/1_Roteiro_Viral.py")

with col_new_2:
    st.markdown("#### 📊 Status do Sistema")
    # Data atual
    st.markdown(f"**Data:** {datetime.today().strftime('%d/%m/%Y')}")
    st.success("Sistema Online")
    
    st.markdown("---")
    st.markdown("**Dica:** Siga a numeração das páginas na barra lateral.")

st.divider()

# ---------------------------------------------------------------------
# 4. DASHBOARD DE PRODUÇÕES RECENTES
# ---------------------------------------------------------------------
st.subheader("📂 Produções Recentes")

# Carrega todas as produções salvas no JSON
producoes = db.load_recent_productions()

if not producoes:
    st.write("Nenhuma produção encontrada no histórico.")
else:
    # Exibe em cards
    for item in producoes:
        with st.container():
            col_a, col_b, col_c = st.columns([1, 3, 2])
            
            with col_a:
                st.markdown(f"## 📅")
                st.caption(item['data'])
            
            with col_b:
                st.markdown(f"**{item['tipo']}**")
                st.caption("Projeto salvo")
            
            with col_c:
                # --- CORREÇÃO DO ERRO DE TYPEERROR ---
                # Conta apenas valores True, ignorando strings (caminhos de arquivos)
                etapas_concluidas = sum(1 for v in item['progresso'].values() if v is True)
                
                # Total estimado de etapas principais (Roteiro, Imagem, Audio, Video)
                total_etapas = 4
                progresso_pct = min(etapas_concluidas / total_etapas, 1.0)
                
                st.progress(progresso_pct, text=f"Progresso: {int(progresso_pct*100)}%")
                
                if st.button("Continuar ➡️", key=f"btn_{item['id']}"):
                    st.session_state['leitura_atual'] = {
                        "tipo": item['tipo'],
                        "titulo": item['tipo'],
                        "data": item['data']
                    }
                    st.session_state['data_atual_str'] = item['data']
                    st.switch_page("pages/1_Roteiro_Viral.py")
            
            st.markdown("---")
