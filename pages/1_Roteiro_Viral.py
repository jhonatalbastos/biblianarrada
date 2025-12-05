import streamlit as st
from datetime import datetime
from groq import Groq

st.set_page_config(page_title="1 – Roteiro Devocional", layout="wide")
st.title("🙏 1 – Roteiro: Bíblia Narrada")

# -------------------------------------------------------------------
# Integração com o DB
# -------------------------------------------------------------------
if "db" not in st.session_state:
    st.error("Por favor, inicie pelo arquivo principal (app.py).")
    st.stop()

db = st.session_state.db
canal_id = st.session_state.get("canal_atual_id")
video_id = st.session_state.get("video_atual_id")

if not canal_id or not video_id:
    st.warning("Nenhum vídeo selecionado. Volte ao Dashboard e selecione um projeto.")
    st.stop()

canal = db["canais"][canal_id]
video = canal["videos"][video_id]

st.subheader(f"Projeto: {video['titulo']}")

# -------------------------------------------------------------------
# Configuração da IA (Groq)
# -------------------------------------------------------------------
# Tenta pegar a chave dos secrets ou input manual
api_key = st.secrets.get("GROQ_API_KEY")
if not api_key:
    api_key = st.text_input("Insira sua Groq API Key:", type="password")

# -------------------------------------------------------------------
# Interface de Geração
# -------------------------------------------------------------------
st.markdown("### 🕊️ Gerar Roteiro Estruturado")

passagem_tema = st.text_input("Passagem Bíblica ou Tema do dia:", value=video.get("titulo", ""))
instrucoes_extras = st.text_area("Instruções adicionais (opcional):", placeholder="Ex: Focar na esperança, usar linguagem acolhedora...")

def gerar_roteiro_biblico():
    if not api_key:
        st.error("API Key necessária.")
        return

    client = Groq(api_key=api_key)
    
    prompt_sistema = """
    Você é um assistente devocional sábio, acolhedor e teologicamente profundo.
    Sua tarefa é criar um roteiro para um vídeo curto (TikTok/YouTube Shorts/Reels).
    O roteiro DEVE seguir estritamente esta estrutura de 5 passos:
    1. Hook (Gancho inicial de 3 a 5 segundos que prenda a atenção)
    2. Leitura (O texto bíblico principal na versão NVI ou Almeida)
    3. Reflexão (Explicação breve e profunda do texto)
    4. Aplicação (Como aplicar isso na vida hoje)
    5. Oração (Uma oração curta em primeira pessoa para quem está assistindo repetir)

    Saída desejada: Apenas o texto falado, separado claramente por seções. Use marcadores como [HOOK], [LEITURA], etc.
    Linguagem: Português do Brasil, tom pastoral e encorajador.
    """

    prompt_usuario = f"Tema/Passagem: {passagem_tema}. \nExtras: {instrucoes_extras}"

    with st.spinner("Meditando e escrevendo o roteiro..."):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                # MODELO ATUALIZADO AQUI:
                model="llama-3.1-70b-versatile", 
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            st.error(f"Erro na IA: {e}")
            return None

# Botão de Geração
if st.button("✨ Gerar Roteiro com IA"):
    resultado_bruto = gerar_roteiro_biblico()
    if resultado_bruto:
        # Tenta fazer um parse simples baseado nas tags, senão coloca tudo num bloco
        # Aqui fazemos um split manual simples para preencher os campos
        sections = {
            "01_Hook": "",
            "02_Leitura": "",
            "03_Reflexão": "",
            "04_Aplicação": "",
            "05_Oração": ""
        }
        
        # Lógica simplificada de extração (pode ser melhorada com Regex)
        # Assume que o modelo obedeceu [TAG]
        current_key = "01_Hook" # Default
        lines = resultado_bruto.split('\n')
        
        buffer = []
        
        for line in lines:
            upper_line = line.upper()
            if "[HOOK]" in upper_line:
                current_key = "01_Hook"
                buffer = []
            elif "[LEITURA]" in upper_line:
                sections["01_Hook"] = "\n".join(buffer).strip()
                current_key = "02_Leitura"
                buffer = []
            elif "[REFLEXÃO]" in upper_line or "[REFLEXAO]" in upper_line:
                sections["02_Leitura"] = "\n".join(buffer).strip()
                current_key = "03_Reflexão"
                buffer = []
            elif "[APLICAÇÃO]" in upper_line or "[APLICACAO]" in upper_line:
                sections["03_Reflexão"] = "\n".join(buffer).strip()
                current_key = "04_Aplicação"
                buffer = []
            elif "[ORAÇÃO]" in upper_line or "[ORACAO]" in upper_line:
                sections["04_Aplicação"] = "\n".join(buffer).strip()
                current_key = "05_Oração"
                buffer = []
            else:
                buffer.append(line)
        
        # Salva o último buffer
        sections[current_key] = "\n".join(buffer).strip()

        # Salva no estado
        roteiro_struct = {}
        prompts_img = {}
        for k, v in sections.items():
            # Estrutura: chave -> lista de parágrafos (aqui usamos 1 parágrafo por seção para simplificar)
            roteiro_struct[k] = [v] if v else ["(Edite este texto)"]
            prompts_img[k] = ["Cinematic biblical scene, peaceful, golden light, 4k"] # Prompt padrão placeholder

        # Atualiza o objeto vídeo
        if "roteiro" not in video["artefatos"]:
            video["artefatos"]["roteiro"] = {}
        
        video["artefatos"]["roteiro"]["roteiro"] = roteiro_struct
        video["artefatos"]["roteiro"]["image_prompts"] = prompts_img
        video["artefatos"]["roteiro"]["titulo_video"] = passagem_tema
        st.success("Roteiro gerado! Edite abaixo.")

# -------------------------------------------------------------------
# Editor Manual do Roteiro
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("📝 Edição Final")

# Recupera o roteiro salvo ou inicializa vazio
artefato_roteiro = video["artefatos"].get("roteiro", {})
blocos_salvos = artefato_roteiro.get("roteiro", {})
prompts_salvos = artefato_roteiro.get("image_prompts", {})

# Define as seções padrão caso esteja vazio
secoes_padrao = ["01_Hook", "02_Leitura", "03_Reflexão", "04_Aplicação", "05_Oração"]
novos_blocos = {}
novos_prompts = {}

with st.form("form_edicao_roteiro"):
    for titulo_secao in secoes_padrao:
        st.markdown(f"#### {titulo_secao.split('_')[1]}")
        
        # Recupera texto atual
        texto_atual_lista = blocos_salvos.get(titulo_secao, [""])
        texto_atual = texto_atual_lista[0] if texto_atual_lista else ""
        
        # Recupera prompt atual
        prompt_atual_lista = prompts_salvos.get(titulo_secao, [""])
        prompt_atual = prompt_atual_lista[0] if prompt_atual_lista else ""

        col_txt, col_img = st.columns([2, 1])
        with col_txt:
            novo_texto = st.text_area(f"Texto ({titulo_secao})", value=texto_atual, height=150, key=f"txt_{titulo_secao}")
        with col_img:
            novo_prompt = st.text_area(f"Prompt Imagem (Inglês)", value=prompt_atual, height=150, key=f"prm_{titulo_secao}", help="Para gerar a thumbnail desta parte.")

        novos_blocos[titulo_secao] = [novo_texto]
        novos_prompts[titulo_secao] = [novo_prompt]
        st.markdown("---")

    btn_salvar = st.form_submit_button("💾 Salvar Roteiro e Prompts")
    if btn_salvar:
        video["artefatos"]["roteiro"]["roteiro"] = novos_blocos
        video["artefatos"]["roteiro"]["image_prompts"] = novos_prompts
        video["artefatos"]["roteiro"]["titulo_video"] = passagem_tema
        video["artefatos"]["roteiro"]["gerado_em"] = datetime.now().isoformat()
        video["status"]["1_roteiro"] = True
        video["ultima_atualizacao"] = datetime.now().isoformat()
        st.success("Roteiro atualizado com sucesso!")
