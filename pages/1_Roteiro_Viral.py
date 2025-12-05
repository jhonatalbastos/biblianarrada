import streamlit as st
from groq import Groq
import json
import os

# Configuração da Página
st.set_page_config(
    page_title="Roteiro Viral - Bíblia Narrada",
    page_icon="✍️",
    layout="wide"
)

# Título e Descrição
st.title("✍️ Gerador de Roteiro Viral")
st.markdown("""
Transforme a Liturgia Diária em um roteiro curto, impactante e pronto para **Reels, TikTok e Shorts**.
A IA analisará o Evangelho e criará uma narrativa que conecta a mensagem milenar com dores e desejos modernos.
""")

st.divider()

# --- Configuração da API Key ---
api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("❌ Chave da API Groq não encontrada. Configure-a nos 'secrets' do Streamlit.")
    st.stop()

client = Groq(api_key=api_key)

# --- Função de Geração de Roteiro ---
def gerar_roteiro_liturgico(dados_liturgia):
    """
    Gera um roteiro viral baseado nos dados da liturgia usando Llama 3.
    """
    
    # Prompt do Sistema (A "Persona" da IA)
    prompt_system = """
    Você é um especialista em Copywriting para Redes Sociais Católicas e Roteirista de Vídeos Curtos (Reels/TikTok).
    Sua missão é traduzir a profundidade teológica do Evangelho em uma linguagem simples, magnética e viral, sem perder a sacralidade.
    
    ESTRUTURA OBRIGATÓRIA DO ROTEIRO (JSON):
    1. "hook_visual": Descrição da cena inicial (3s) para prender atenção visualmente.
    2. "headline": A frase falada nos primeiros 3 segundos (O Gancho). Deve tocar numa dor ou curiosidade.
    3. "corpo": O desenvolvimento da mensagem (máximo 40 segundos). Use storytelling.
    4. "cta": Chamada para ação clara (Ex: "Comente 'Amém' se você crê").
    5. "legenda": Sugestão de legenda para o post com hashtags.
    6. "prompt_imagem": Um prompt detalhado para gerar uma imagem de capa ou fundo usando IA (estilo cinematográfico, realista).
    
    TOM DE VOZ:
    - Próximo, acolhedor, mas com autoridade espiritual.
    - Evite "evangeliquês" difícil. Use analogias do dia a dia.
    - Foco na transformação: Do sofrimento para a esperança.
    """

    # Prompt do Usuário (O Conteúdo)
    prompt_user = f"""
    Crie um roteiro viral para o Evangelho de hoje.
    
    DADOS DA LITURGIA:
    Data: {dados_liturgia.get('data', 'Hoje')}
    Cor Litúrgica: {dados_liturgia.get('cor', 'N/A')}
    Santo do Dia: {dados_liturgia.get('santo', 'N/A')}
    
    PRIMEIRA LEITURA (Resumo): {dados_liturgia.get('primeira_leitura', '')[:500]}...
    
    EVANGELHO COMPLETO:
    {dados_liturgia.get('evangelho', '')}
    
    REFLEXÃO/HOMILIA BASE:
    {dados_liturgia.get('reflexao', '')[:1000]}...
    
    Retorne APENAS um objeto JSON válido.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user}
            ],
            # --- ATUALIZAÇÃO DO MODELO AQUI ---
            model="llama-3.3-70b-versatile", 
            # ----------------------------------
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro ao conectar com a IA: {e}")
        return None

# --- Interface Principal ---

# Verifica se há dados na sessão (vindos da Home)
if "dados_liturgia" not in st.session_state:
    st.warning("⚠️ Nenhuma liturgia carregada. Por favor, vá para a **Página Inicial (Início)** e carregue a liturgia do dia primeiro.")
    if st.button("Ir para Início"):
        st.switch_page("Inicio.py") # Ajuste se o nome do arquivo principal for diferente
else:
    dados = st.session_state["dados_liturgia"]
    
    # Exibe resumo do que foi carregado
    st.success(f"📖 Liturgia carregada: {dados.get('data')} - {dados.get('santo')}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("💡 **Dica:** O roteiro é gerado focado em retenção. Leia em voz alta para testar o ritmo.")
        if st.button("✨ Gerar Roteiro Viral", type="primary", use_container_width=True):
            with st.spinner("A IA está escrevendo seu roteiro..."):
                roteiro_gerado = gerar_roteiro_liturgico(dados)
                
                if roteiro_gerado:
                    st.session_state["roteiro_atual"] = roteiro_gerado
                    st.rerun() # Recarrega para mostrar o resultado

    with col2:
        if "roteiro_atual" in st.session_state:
            r = st.session_state["roteiro_atual"]
            
            st.subheader("🎬 Seu Roteiro")
            
            # Exibição visual do Roteiro
            container = st.container(border=True)
            container.markdown(f"**🎥 Gancho Visual:** `{r.get('hook_visual')}`")
            container.markdown(f"**🗣️ Headline (Fale isso):** \n> ## {r.get('headline')}")
            container.markdown(f"**📜 Corpo do Texto:** \n\n{r.get('corpo')}")
            container.markdown(f"**🔥 Chamada para Ação (CTA):** `{r.get('cta')}`")
            
            st.divider()
            
            with st.expander("📝 Legenda e Hashtags"):
                st.code(r.get('legenda'), language="text")
                
            with st.expander("🎨 Prompt para Imagem (Midjourney/DALL-E)"):
                st.code(r.get('prompt_imagem'), language="text")
                
            # Botão de Download (Opcional, salva como TXT)
            texto_download = f"""ROTEIRO VIRAL - {dados.get('data')}
            
HEADLINE: {r.get('headline')}

CORPO:
{r.get('corpo')}

CTA: {r.get('cta')}

LEGENDA:
{r.get('legenda')}
            """
            st.download_button(
                label="📥 Baixar Roteiro (.txt)",
                data=texto_download,
                file_name=f"roteiro_viral_{dados.get('data').replace('/', '-')}.txt",
                mime="text/plain"
            )
