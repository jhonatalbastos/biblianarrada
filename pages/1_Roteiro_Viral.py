import streamlit as st
import time

st.set_page_config(page_title="Gerar Roteiro", page_icon="📝", layout="wide")

if 'leitura_atual' not in st.session_state:
    st.warning("Nenhuma leitura selecionada. Volte ao Início.")
    if st.button("🏠 Voltar ao Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', '')
chave_progresso = f"{data_str}-{leitura['tipo']}"

st.title(f"📝 Roteiro: {leitura['tipo']}")
st.caption(f"Referência: {leitura['ref']}")

# Layout: Texto Original vs Roteiro Gerado
c1, c2 = st.columns(2)

with c1:
    st.subheader("Texto Bíblico Original")
    with st.container(height=500):
        st.write(leitura['texto'])

with c2:
    st.subheader("Roteiro Viral (5 Blocos)")
    
    # Placeholder para simular IA
    def simular_ia(prompt_type, texto_base):
        time.sleep(1) # Simula tempo de processamento
        return f"[Conteúdo Gerado por IA para {prompt_type}]\nBaseado em: {texto_base[:50]}..."

    # Formulário para geração
    with st.form("form_roteiro"):
        st.info("A IA irá estruturar o texto em 5 blocos: Hook, Leitura, Reflexão, Aplicação, Oração.")
        submitted = st.form_submit_button("✨ Gerar Roteiro Agora")
    
    if submitted:
        progress = st.progress(0, text="Analisando texto...")
        
        # Bloco 1: Hook
        progress.progress(20, text="Criando Hook Viral...")
        b1 = simular_ia("Hook + CTA", leitura['texto'])
        
        # Bloco 2: Leitura (Geralmente é o texto original ou resumido)
        progress.progress(40, text="Formatando Leitura...")
        b2 = leitura['texto'] 
        
        # Bloco 3: Reflexão
        progress.progress(60, text="Escrevendo Reflexão Teológica...")
        b3 = simular_ia("Reflexão Curta", leitura['texto'])
        
        # Bloco 4: Aplicação
        progress.progress(80, text="Criando Aplicação Prática...")
        b4 = simular_ia("Aplicação Prática", leitura['texto'])
        
        # Bloco 5: Oração
        progress.progress(95, text="Finalizando com Oração...")
        b5 = simular_ia("Oração Final", leitura['texto'])
        
        progress.progress(100, text="Concluído!")
        
        # Salvar no Session State
        st.session_state['roteiro_gerado'] = {
            "hook": b1,
            "leitura": b2,
            "reflexao": b3,
            "aplicacao": b4,
            "oracao": b5
        }
        
        # Atualizar status no Pipeline
        if 'progresso_leituras' in st.session_state:
             if chave_progresso not in st.session_state['progresso_leituras']:
                 st.session_state['progresso_leituras'][chave_progresso] = {}
             st.session_state['progresso_leituras'][chave_progresso]['roteiro'] = True

        st.rerun()

    # Exibir Roteiro se já existir
    if 'roteiro_gerado' in st.session_state:
        rg = st.session_state['roteiro_gerado']
        
        st.success("Roteiro Gerado com Sucesso!")
        
        st.markdown("**1. Hook + CTA**")
        st.text_area("Bloco 1", rg['hook'], height=100)
        
        st.markdown("**2. Leitura**")
        st.text_area("Bloco 2", rg['leitura'], height=150)
        
        st.markdown("**3. Reflexão**")
        st.text_area("Bloco 3", rg['reflexao'], height=150)
        
        st.markdown("**4. Aplicação**")
        st.text_area("Bloco 4", rg['aplicacao'], height=100)
        
        st.markdown("**5. Oração**")
        st.text_area("Bloco 5", rg['oracao'], height=100)
        
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("🎨 Ir para Geração de Imagens", type="primary", use_container_width=True):
                st.switch_page("pages/2_Imagens.py")
        with col_nav2:
             if st.button("🏠 Voltar ao Dashboard", use_container_width=True):
                st.switch_page("Inicio.py")
