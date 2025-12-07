import streamlit as st
import sys
import os
import json
from datetime import datetime

# Tenta importar a biblioteca Groq
try:
    from groq import Groq
except ImportError:
    st.error("⚠️ Biblioteca 'groq' não encontrada. Instale usando: pip install groq")
    st.stop()

# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E IMPORTAÇÕES
# ---------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

try:
    import modules.database as db
except ImportError:
    st.error("🚨 Erro: Não foi possível importar o módulo de banco de dados.")
    st.stop()

# ---------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(page_title="1. Roteiro Viral", layout="wide")

# ---------------------------------------------------------------------
# 3. RECUPERAÇÃO DE ESTADO
# ---------------------------------------------------------------------
if 'leitura_atual' not in st.session_state:
    st.warning("⚠️ Nenhuma leitura selecionada.")
    if st.button("Voltar para o Início"):
        st.switch_page("Inicio.py")
    st.stop()

leitura = st.session_state['leitura_atual']
data_str = st.session_state.get('data_atual_str', datetime.today().strftime('%Y-%m-%d'))
chave_progresso = f"{data_str}-{leitura['tipo']}"

# Carrega status atual do banco
progresso, em_producao = db.load_status(chave_progresso)

# Inicializa o cliente Groq
api_key = st.secrets.get("GROQ_API_KEY")
client = None
if api_key:
    client = Groq(api_key=api_key)

# ---------------------------------------------------------------------
# 4. FUNÇÕES DE GERAÇÃO (IA)
# ---------------------------------------------------------------------

def gerar_conteudo_ia(texto_original, referencia):
    """Gera os 4 blocos de texto e os 4 prompts de imagem usando Groq."""
    
    if not client:
        st.error("Chave de API Groq não configurada nos secrets.")
        return None, None, None, None, None

    with st.spinner('🤖 A IA está lendo o Evangelho, refletindo e orando... Por favor, aguarde.'):
        
        # --- BLOCO 1: LEITURA FORMATADA ---
        prompt_leitura = f"""
        Atue como um leitor litúrgico católico.
        Reescreva o texto abaixo para o formato solene de proclamação.
        Referência: {referencia}
        Texto Original: "{texto_original}"

        Regras de Formatação:
        1. Inicie com: "Proclamação do Evangelho segundo [Nome], capítulo [X], versículos [Y]. Glória a vós, Senhor!" (Ajuste conforme a referência).
        2. Insira o corpo do texto corrigido e pontuado para leitura em voz alta.
        3. Termine com: "Palavra da Salvação. Glória a vós, Senhor."
        4. Não adicione comentários, apenas o texto litúrgico formatado.
        """
        
        completion_1 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_leitura}],
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        txt_leitura = completion_1.choices[0].message.content

        # --- BLOCO 2: REFLEXÃO ---
        prompt_reflexao = f"""
        Atue como um especialista em teologia católica e liturgia.
        Leia o seguinte texto do Evangelho: "{texto_original}"

        Sua tarefa é escrever uma reflexão teológica curta e profunda sobre este texto.

        Regras estritas:
        1. Inicie o texto EXATAMENTE com a palavra "Reflexão." (com o ponto final e quebra de linha).
        2. O conteúdo deve ter entre 80 a 100 palavras.
        3. Use uma linguagem culta, mas acessível, focada na teologia da missão, compaixão e Reino de Deus.
        4. O texto deve ser um parágrafo único.
        5. Não use emojis ou formatação de markdown (negrito/itálico) no corpo do texto.
        """
        
        completion_2 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_reflexao}],
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        txt_reflexao = completion_2.choices[0].message.content

        # --- BLOCO 3: APLICAÇÃO NA VIDA ---
        prompt_aplicacao = f"""
        Atue como um diretor espiritual católico focado em vivência prática da fé.
        Leia o seguinte texto do Evangelho: "{texto_original}"

        Sua tarefa é escrever um parágrafo de aplicação prática para o dia a dia.

        Regras estritas:
        1. Inicie o texto EXATAMENTE com a frase "Aplicação na sua vida." (com ponto final e quebra de linha).
        2. O tamanho deve ser semelhante ao exemplo (aprox. 80 a 100 palavras).
        3. Tom de voz: Desafiador, pessoal (use "você" ou "nós") e motivador.
        4. Estrutura obrigatória:
           - Conecte a missão do texto bíblico à identidade do leitor como discípulo.
           - Inclua uma pergunta direta de reflexão/exame de consciência (ex: "Pergunte-se: ...").
           - Termine com uma chamada para ação concreta (uso de tempo, talentos ou recursos) e serviço ao próximo.
        """
        
        completion_3 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_aplicacao}],
            model="llama-3.3-70b-versatile",
            temperature=0.6
        )
        txt_aplicacao = completion_3.choices[0].message.content

        # --- BLOCO 4: ORAÇÃO ---
        prompt_oracao = f"""
        Atue como um líder espiritual católico inspirador.
        Com base no texto do Evangelho: "{texto_original}"

        Sua tarefa é escrever a conclusão da reflexão, composta por uma Oração e um Envio Final.

        Regras estritas de Estrutura:
        1. PRIMEIRA PARTE (Oração):
           - Inicie EXATAMENTE com o texto: "Vamos orar:" (quebra de linha).
           - Escreva uma oração de um parágrafo (aprox. 60-80 palavras).
           - Dirija-se a Jesus ou ao Pai. Agradeça pela mensagem do Evangelho e peça a graça de colocá-la em prática.
           - Termine com "Amém."

        2. SEGUNDA PARTE (Envio):
           - Pule uma linha após o "Amém".
           - Inicie EXATAMENTE com a frase: "Se esta Palavra tocou o seu coração," (quebra de linha).
           - Escreva um parágrafo de encerramento (aprox. 60-80 palavras).
           - Incentive o leitor a não guardar a Boa Nova, a realizar uma atitude concreta de caridade hoje (cite uma ação relacionada ao texto) e a compartilhar a mensagem com um amigo.
        """
        
        completion_4 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_oracao}],
            model="llama-3.3-70b-versatile",
            temperature=0.6
        )
        txt_oracao = completion_4.choices[0].message.content

        # --- GERAÇÃO DE PROMPTS DE IMAGEM (ATUALIZADO) ---
        # Reforçando o aspecto "contemporâneo/roupas modernas" nos blocos 2, 3 e 4
        prompts_img = {
            "bloco_1": f"A high-quality, cinematic, photorealistic biblical scene depicting the events described in this text: '{texto_original}'. Style: Epic movie shot, First Century Palestine setting, dramatic lighting, 8k resolution, highly detailed texture. Constraint: No text, no typography, no watermarks.",
            
            "bloco_2": f"A photorealistic image of Jesus Christ (traditional appearance with robes) sitting in a modern, busy everyday setting (like a coffee shop, a subway station, or a busy park). Action: He is having a friendly conversation with an **ordinary contemporary person wearing casual modern clothes (like jeans, t-shirt, or hoodie)**. Context: They are discussing the biblical theme: '{texto_original}'. Style: Candid photography, depth of field, natural lighting, realistic interactions, vertical 9:16 framing.",
            
            "bloco_3": f"A photorealistic image of Jesus Christ (traditional appearance) walking or standing with an **ordinary modern person dressed in contemporary daily attire** in a public urban space (like a street, bus stop, or office). Action: Jesus is gesturing kindly, offering advice or comfort, like a mentor. Context: Applying the lesson of this text to real life: '{texto_original}'. Style: Warm atmosphere, urban photography style, 4k resolution, vertical 9:16 framing.",
            
            "bloco_4": f"A serene, photorealistic image of Jesus Christ and an **ordinary person wearing modern casual clothing** in a quiet, calm location (like a peaceful living room or a quiet garden corner). Action: They are praying together, perhaps with eyes closed or hands clasped. Atmosphere: Spiritual, peaceful, soft divine lighting, intimate and comforting. Context: Based on the spirituality of: '{texto_original}'."
        }

    return txt_leitura, txt_reflexao, txt_aplicacao, txt_oracao, prompts_img

# ---------------------------------------------------------------------
# 5. INTERFACE DO ROTEIRO
# ---------------------------------------------------------------------

st.title("📝 Passo 1: Roteiro Viral (4 Blocos)")

# Header
cols_header = st.columns([3, 1])
with cols_header[0]:
    st.markdown(f"**Leitura:** {leitura['titulo']}")
    st.caption(f"Ref: {leitura['ref']} | Data: {data_str}")
with cols_header[1]:
    if st.button("🔙 Trocar Leitura"):
        st.switch_page("Inicio.py")

st.divider()

col_esq, col_dir = st.columns([1, 1])

# --- COLUNA 1: TEXTO ORIGINAL (REFERÊNCIA) ---
with col_esq:
    st.subheader("📖 Texto Original (Base)")
    with st.container(border=True):
        st.markdown(f"### {leitura['titulo']}")
        st.markdown(f"**{leitura['ref']}**")
        st.write(leitura['texto'])

# --- COLUNA 2: EDITOR DE ROTEIRO (4 BLOCOS) ---
with col_dir:
    st.subheader("✍️ Editor de Roteiro")

    # Recupera valores salvos ou inicializa vazios
    val_bloco1 = progresso.get('bloco_leitura', '')
    val_bloco2 = progresso.get('bloco_reflexao', '')
    val_bloco3 = progresso.get('bloco_aplicacao', '')
    val_bloco4 = progresso.get('bloco_oracao', '')
    
    # Botão de Geração com IA
    if not val_bloco1:
        st.info("O roteiro está vazio. Use a IA para gerar os 4 blocos e preparar as imagens.")
        if st.button("✨ Gerar Roteiro Completo e Imagens (IA)", type="primary"):
            b1, b2, b3, b4, p_imgs = gerar_conteudo_ia(leitura['texto'], leitura['ref'])
            if b1:
                # Atualiza session state temporário para exibir nos campos
                st.session_state['temp_b1'] = b1
                st.session_state['temp_b2'] = b2
                st.session_state['temp_b3'] = b3
                st.session_state['temp_b4'] = b4
                st.session_state['temp_p_imgs'] = p_imgs
                st.rerun()
    else:
        # Se já existe no progresso, usa de lá
        if 'temp_b1' not in st.session_state:
            st.session_state['temp_b1'] = val_bloco1
            st.session_state['temp_b2'] = val_bloco2
            st.session_state['temp_b3'] = val_bloco3
            st.session_state['temp_b4'] = val_bloco4

    # Campos de Edição
    with st.form("form_roteiro"):
        st.markdown("### Bloco 1: Leitura (Formatada)")
        txt_b1 = st.text_area("Texto Litúrgico", value=st.session_state.get('temp_b1', ''), height=300)
        
        st.markdown("### Bloco 2: Reflexão")
        txt_b2 = st.text_area("Reflexão Teológica", value=st.session_state.get('temp_b2', ''), height=200)

        st.markdown("### Bloco 3: Aplicação na sua vida")
        txt_b3 = st.text_area("Aplicação Prática", value=st.session_state.get('temp_b3', ''), height=200)

        st.markdown("### Bloco 4: Oração")
        txt_b4 = st.text_area("Oração e Envio", value=st.session_state.get('temp_b4', ''), height=250)
        
        # Botão para regenerar APENAS os prompts de imagem (caso o usuário queira atualizar sem mexer no texto)
        st.markdown("---")
        regerar_prompts = st.checkbox("Recriar prompts de imagem com a nova configuração?")

        submitted = st.form_submit_button("💾 Salvar Todos os Blocos")

        if submitted:
            # Atualiza o dicionário de progresso
            progresso['bloco_leitura'] = txt_b1
            progresso['bloco_reflexao'] = txt_b2
            progresso['bloco_aplicacao'] = txt_b3
            progresso['bloco_oracao'] = txt_b4
            
            # Se o usuário marcou para recriar os prompts OU se eles foram gerados agora pela IA
            if regerar_prompts:
                 # Recria os prompts localmente com a nova string
                 # (Para evitar chamar a API do Groq só pra isso, montamos aqui com o texto atual)
                 progresso['prompts_imagem'] = {
                    "bloco_1": f"A high-quality, cinematic, photorealistic biblical scene depicting the events described in this text: '{leitura['texto']}'. Style: Epic movie shot, First Century Palestine setting, dramatic lighting, 8k resolution, highly detailed texture. Constraint: No text, no typography, no watermarks.",
                    "bloco_2": f"A photorealistic image of Jesus Christ (traditional appearance with robes) sitting in a modern, busy everyday setting (like a coffee shop, a subway station, or a busy park). Action: He is having a friendly conversation with an **ordinary contemporary person wearing casual modern clothes (like jeans, t-shirt, or hoodie)**. Context: They are discussing the biblical theme: '{leitura['texto']}'. Style: Candid photography, depth of field, natural lighting, realistic interactions, vertical 9:16 framing.",
                    "bloco_3": f"A photorealistic image of Jesus Christ (traditional appearance) walking or standing with an **ordinary modern person dressed in contemporary daily attire** in a public urban space (like a street, bus stop, or office). Action: Jesus is gesturing kindly, offering advice or comfort, like a mentor. Context: Applying the lesson of this text to real life: '{leitura['texto']}'. Style: Warm atmosphere, urban photography style, 4k resolution, vertical 9:16 framing.",
                    "bloco_4": f"A serene, photorealistic image of Jesus Christ and an **ordinary person wearing modern casual clothing** in a quiet, calm location (like a peaceful living room or a quiet garden corner). Action: They are praying together, perhaps with eyes closed or hands clasped. Atmosphere: Spiritual, peaceful, soft divine lighting, intimate and comforting. Context: Based on the spirituality of: '{leitura['texto']}'."
                }
            elif 'temp_p_imgs' in st.session_state:
                 progresso['prompts_imagem'] = st.session_state['temp_p_imgs']
            
            # Cria um texto completo concatenado para referência futura
            progresso['texto_roteiro_completo'] = f"{txt_b1}\n\n{txt_b2}\n\n{txt_b3}\n\n{txt_b4}"
            
            progresso['roteiro'] = True 
            
            # Salva no banco
            db.update_status(chave_progresso, data_str, leitura['tipo'], progresso, 1)
            
            st.success("Roteiro e Prompts de Imagem salvos com sucesso!")
            st.session_state['progresso_leitura_atual'] = progresso

# ---------------------------------------------------------------------
# 6. NAVEGAÇÃO
# ---------------------------------------------------------------------
st.divider()
col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])

with col_nav_3:
    if progresso.get('roteiro'):
        if st.button("Próximo: Criar Imagens (IA) ➡️", type="primary", use_container_width=True):
            st.switch_page("pages/2_Imagens.py")
    else:
        st.button("Próximo ➡️", disabled=True, use_container_width=True, help="Salve o roteiro primeiro.")
