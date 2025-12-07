import streamlit as st
import sys
import os
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import modules.database as db
except ImportError:
    # Fallback caso a pasta modules não seja encontrada de imediato
    st.error("Erro ao importar módulo de banco de dados. Verifique a estrutura de pastas.")
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
                # Textos
                "bloco_leitura": "",
                "bloco_reflexao": "",
                "bloco_aplicacao": "",
                "bloco_oracao": ""
            }
            
            # 2. Salva no Session State para passar para a próxima página
            st.session_state['leitura_atual'] = {
                "tipo": tipo_leitura,
                "titulo": referencia,
                "data": data_hoje
            }
            st.session_state['data_atual_str'] = data_hoje
            
            # 3. Cria entrada inicial no JSON (Database)
            chave = f"{data_hoje}-{tipo_leitura}"
            # Se já existir, db.load_status recupera, senão cria zero.
            # Aqui forçamos a atualização/criação
            db.update_status(chave, data_hoje, tipo_leitura, novo_status, 0)
            
            st.success(f"Projeto '{referencia}' iniciado!")
            
            # 4. Redireciona para o Roteiro
            st.switch_page("pages/1_Roteiro_Viral.py")

with col_new_2:
    st.markdown("#### 📊 Status do Sistema")
    st.markdown("""
    *   **API IA Texto:** ✅ Ativo (Groq/Llama)
    *   **API Imagem:** ✅ Ativo (Pollinations)
    *   **API Áudio:** ✅ Ativo (Edge-TTS)
    *   **Data:** """ + datetime.today().strftime('%d/%m/%Y'))
    
    st.markdown("---")
    st.markdown("**Dica:** Siga a numeração das páginas na barra lateral para completar o fluxo.")

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
    # Exibe em cards (colunas)
    for item in producoes:
        with st.container():
            col_a, col_b, col_c = st.columns([1, 3, 2])
            
            with col_a:
                st.markdown(f"## 📅")
                st.caption(item['data'])
            
            with col_b:
                st.markdown(f"**{item['tipo']}**")
                # Tenta pegar um título se houver no progresso, senão usa genérico
                st.write("Projeto em andamento")
            
            with col_c:
                # -------------------------------------------------------
                # A CORREÇÃO ESTÁ AQUI ABAIXO
                # -------------------------------------------------------
                # Antes: etapas = sum(item['progresso'].values()) -> Isso quebrava com textos
                # Agora: Somamos apenas se o valor for explicitamente True
                etapas = sum(1 for v in item['progresso'].values() if v is True)
                
                # O total de etapas padrão é 4 (Roteiro, Imagem, Audio, Video)
                total_etapas = 4 
                progresso_pct = min(etapas / total_etapas, 1.0)
                
                st.progress(progresso_pct, text=f"Progresso: {int(progresso_pct*100)}%")
                
                if st.button("Continuar ➡️", key=f"btn_{item['id']}"):
                    # Carrega no session state e vai para roteiro (ou a pág certa)
                    st.session_state['leitura_atual'] = {
                        "tipo": item['tipo'],
                        "titulo": item['tipo'], # Título genérico ao carregar
                        "data": item['data']
                    }
                    st.session_state['data_atual_str'] = item['data']
                    st.switch_page("pages/1_Roteiro_Viral.py")
            
            st.markdown("---")
