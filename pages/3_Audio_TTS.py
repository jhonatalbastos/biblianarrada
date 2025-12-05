import streamlit as st
import time
import os

st.set_page_config(page_title="Gerar Áudio TTS", page_icon="🔊", layout="wide")

if 'roteiro_gerado' not in st.session_state:
    st.error("Roteiro não encontrado.")
    st.stop()

roteiro = st.session_state['roteiro_gerado']
blocos = ["hook", "leitura", "reflexao", "aplicacao", "oracao"]

st.title("🔊 Estúdio de Narração (Piper TTS)")

c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("### Configuração de Voz")
    voz = st.selectbox("Modelo de Voz Piper", ["pt_BR-faber-medium", "pt_BR-edresson-low"])
    velocidade = st.slider("Velocidade da Fala", 0.8, 1.5, 1.0)
    
    st.info("Nota: O Piper TTS deve estar instalado no servidor para funcionar. Aqui simularemos o processo.")

with c2:
    st.markdown("### Processamento em Massa")
    if st.button("🎙️ Gerar Todos os Áudios", type="primary", use_container_width=True):
        
        prog_bar = st.progress(0, text="Inicializando Piper...")
        status = st.empty()
        audios_gerados = {}
        
        total = len(blocos)
        
        for i, bloco in enumerate(blocos):
            texto = roteiro[bloco]
            nome_arquivo = f"audio_{bloco}.wav"
            
            # Cálculo de ETA simples
            status.markdown(f"**Processando:** {bloco.upper()}... (ETA: {2*(total-i)}s)")
            
            # --- Simulação do Subprocess do Piper ---
            # Comando real seria algo como:
            # cmd = f"echo '{texto}' | piper --model {voz} --output_file {nome_arquivo}"
            # subprocess.run(cmd, shell=True)
            
            time.sleep(2) # Simula tempo de renderização de áudio
            
            audios_gerados[bloco] = nome_arquivo # Aqui você salvaria o caminho real
            
            prog = (i + 1) / total
            prog_bar.progress(prog, text=f"Concluído: {int(prog*100)}%")
        
        st.session_state['audios_gerados'] = audios_gerados
        
        # Atualiza Status Global
        leitura = st.session_state.get('leitura_atual', {})
        data_str = st.session_state.get('data_atual_str', '')
        chave = f"{data_str}-{leitura.get('tipo', '')}"
        if chave in st.session_state.get('progresso_leituras', {}):
            st.session_state['progresso_leituras'][chave]['audio'] = True
            
        st.success("Áudios gerados com sucesso!")
        st.rerun()

st.divider()

if 'audios_gerados' in st.session_state:
    st.subheader("🎧 Resultado Final")
    
    for bloco in blocos:
        with st.container():
            col_txt, col_player = st.columns([3, 2])
            with col_txt:
                st.markdown(f"**{bloco.upper()}**")
                st.caption(roteiro[bloco][:100] + "...")
            with col_player:
                # Como é simulação, não temos o arquivo real .wav para tocar aqui
                # Em produção: st.audio(st.session_state['audios_gerados'][bloco])
                st.warning("Arquivo de áudio simulado (Preview indisponível sem Piper instalado).")
    
    st.success("Processo Completo! Você pode voltar ao início para escolher outra leitura.")
    if st.button("🏠 Voltar ao Dashboard"):
        st.switch_page("Inicio.py")
