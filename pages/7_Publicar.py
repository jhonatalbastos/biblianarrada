import streamlit as st
from groq import Groq

st.set_page_config(page_title="Publicar", page_icon="🚀", layout="wide")

if 'leitura_atual' not in st.session_state:
    st.warning("Selecione uma leitura no Início.")
    st.stop()

leitura = st.session_state['leitura_atual']
roteiro = st.session_state.get('roteiro_gerado', {})
texto_base = leitura['texto']

# Config API
api_key = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

st.title("🚀 Central de Publicação")
st.markdown("Gere títulos virais e descrições para Shorts e TikTok.")

if not client:
    st.error("Configure a API KEY do Groq para usar a IA.")
    st.stop()

col_input, col_output = st.columns(2)

with col_input:
    st.subheader("Conteúdo Analisado")
    st.info(f"Leitura: {leitura['tipo']} - {leitura.get('ref')}")
    st.text_area("Base do Roteiro (Hook)", roteiro.get('hook', 'Texto indisponível'), height=150, disabled=True)
    
    if st.button("✨ Gerar Metadados com IA", type="primary"):
        with st.spinner("Criando títulos virais..."):
            prompt = f"""
            Aja como um especialista em YouTube Shorts e TikTok.
            Baseado neste texto religioso: "{roteiro.get('hook', '')} ... {roteiro.get('reflexao', '')}"
            
            Gere:
            1. 5 Títulos Altamente Virais (curtos, < 60 chars) para Shorts.
            2. 5 Títulos estilo "Curiosidade" para TikTok.
            3. Uma descrição curta com hashtags relevantes.
            
            Formate bonito.
            """
            
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile"
            )
            st.session_state['metadados_pub'] = completion.choices[0].message.content

with col_output:
    st.subheader("📋 Metadados Gerados")
    
    if 'metadados_pub' in st.session_state:
        st.markdown(st.session_state['metadados_pub'])
        
        # Atualiza Status Final
        data_str = st.session_state.get('data_atual_str', '')
        leitura_tipo = st.session_state.get('leitura_atual', {}).get('tipo', '')
        chave = f"{data_str}-{leitura_tipo}"
        if chave in st.session_state.get('progresso_leituras', {}):
            st.session_state['progresso_leituras'][chave]['publicacao'] = True
            
        st.success("Ciclo Completo! ✅")
        if st.button("🏠 Voltar ao Início (Novo Projeto)"):
            st.switch_page("Inicio.py")
    else:
        st.info("Clique em gerar para ver as sugestões.")
