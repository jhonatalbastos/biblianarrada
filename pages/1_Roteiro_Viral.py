import os
import json
import uuid
from datetime import datetime

import streamlit as st
from groq import Groq

st.set_page_config(page_title="1 – Roteiro Litúrgico", layout="wide")
st.title("📝 1 – Criador de Roteiro (Liturgia Diária)")

# -------------------------------------------------------------------
# Integração com Banco e Inicio.py
# -------------------------------------------------------------------
if "db" not in st.session_state:
    st.session_state.db = {"canais": {}}
db = st.session_state.db

# Verifica se temos dados vindos do Inicio.py
dados_liturgia = st.session_state.get("dados_liturgia_selecionada")

if not dados_liturgia:
    st.warning("⚠️ Nenhuma liturgia selecionada no Início. O roteiro será genérico.")
    st.markdown("[Voltar para Início](Inicio)")
else:
    st.success(f"✅ Liturgia carregada: {dados_liturgia['data']}")

# -------------------------------------------------------------------
# Configuração do Canal/Vídeo (Mantido da lógica original)
# -------------------------------------------------------------------
if "canal_atual_id" not in st.session_state:
    st.session_state.canal_atual_id = None
if "video_atual_id" not in st.session_state:
    st.session_state.video_atual_id = None

canal_id = st.session_state.canal_atual_id
# Se não tiver canal selecionado, cria um temporário ou avisa
if not canal_id or canal_id not in db["canais"]:
    st.info("Trabalhando em modo rascunho (sem canal vinculado).")

# -------------------------------------------------------------------
# Lógica de Geração com IA
# -------------------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

def gerar_roteiro_liturgico(dados):
    """Gera um roteiro baseado nas leituras carregadas."""
    
    # Extrai textos
    leituras_texto = "\n\n".join([f"{l['tipo']} ({l['livro']}): {l['texto']}" for l in dados['leituras']])
    
    prompt_system = """
    Você é um roteirista especializado em vídeos católicos para YouTube (estilo 'Bíblia Narrada').
    Crie um roteiro emocionante e espiritual.
    
    Estrutura do JSON de resposta:
    {
      "titulo": "Um título viral e curto",
      "intro": "Texto da introdução (gancho)",
      "leitura_comentada": "O texto do Evangelho intercalado com breves explicações ou o texto na íntegra de forma narrativa.",
      "reflexao": "Uma aplicação prática para a vida hoje.",
      "oracao_final": "Uma oração curta de encerramento."
    }
    """
    
    prompt_user = f"""
    Baseado na liturgia de hoje ({dados['data']}), crie um roteiro.
    
    AS LEITURAS SÃO:
    {leituras_texto}
    
    O foco principal deve ser o Evangelho.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user}
            ],
            model="llama3-70b-8192",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return None

# -------------------------------------------------------------------
# Interface de Edição
# -------------------------------------------------------------------

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Conteúdo Base")
    if dados_liturgia:
        for l in dados_liturgia['leituras']:
            with st.expander(f"📜 Ver {l['tipo']}"):
                st.write(l['texto'])
                
    if st.button("✨ Gerar Roteiro com IA", type="primary", disabled=(not client or not dados_liturgia)):
        with st.spinner("A IA está meditando nas leituras..."):
            roteiro_gerado = gerar_roteiro_liturgico(dados_liturgia)
            if roteiro_gerado:
                st.session_state.roteiro_atual = roteiro_gerado
                st.success("Roteiro gerado!")

with col_right:
    st.subheader("✍️ Editor de Roteiro")
    
    roteiro = st.session_state.get("roteiro_atual", {})
    
    # Campos editáveis
    titulo = st.text_input("Título do Vídeo", value=roteiro.get("titulo", ""))
    intro = st.text_area("1. Introdução", value=roteiro.get("intro", ""), height=100)
    corpo = st.text_area("2. Evangelho / Leitura", value=roteiro.get("leitura_comentada", ""), height=300)
    reflexao = st.text_area("3. Reflexão / Homilia Curta", value=roteiro.get("reflexao", ""), height=150)
    oracao = st.text_area("4. Oração Final", value=roteiro.get("oracao_final", ""), height=100)
    
    if st.button("💾 Salvar Roteiro para Vídeo"):
        # Salva estrutura pronta para o gerador de áudio/vídeo
        st.session_state.roteiro_finalizado = {
            "titulo": titulo,
            "blocos": [intro, corpo, reflexao, oracao]
        }
        
        # Opcional: Atualizar o objeto 'video' no db['canais'] se estiver usando o sistema completo
        if canal_id and st.session_state.video_atual_id:
             # Lógica de atualização do DB original
             pass
             
        st.success("Roteiro salvo! Pronto para gerar Áudio e Imagens.")
