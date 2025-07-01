import os
import streamlit as st
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from io import StringIO
import pytz
import zipfile 
import io

st.set_page_config(page_title="Grupo Projeta", layout="wide")
# Sessão de usuário
if "usuario" not in st.session_state:
    st.session_state.usuario = None

st.markdown("""
    <style>
        /* Oculta a barra de ações (canto superior direito) */
        [data-testid="stToolbarActions"],
        /* Oculta o menu principal (os três pontinhos ...) */
        [data-testid="stMainMenu"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

USUARIOS = {
    "Liderancas": {
        "perfil": st.secrets["usuarios"]["Liderancas"]["perfil"],
        "senha": st.secrets["usuarios"]["Liderancas"]["senha"]

    },
    "Tecnicos": {
        "perfil": st.secrets["usuarios"]["Tecnicos"]["perfil"],
        "senha": st.secrets["usuarios"]["Tecnicos"]["senha"]

    }
}
# Função de login
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("###  Acesso Restrito")
            usuario = st.text_input("Usuário", placeholder="Liderancas ou Tecnicos")
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")

            if submit:
                if usuario in USUARIOS and senha == USUARIOS[usuario]["senha"]:
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

if not st.session_state.usuario:
    login()
    st.stop()

perfil = USUARIOS[st.session_state.usuario]["perfil"]


if perfil == "Liderancas":
    abas = st.tabs(["Cadastro de Tarefa", "Cadastro de Descrição", "Controle de Arquivos"])

    with abas[2]:
        def conectar_google_sheets():
            escopos = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            json_credencial = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
            credenciais = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json_credencial), escopos) 
            cliente = gspread.authorize(credenciais)
            planilha = cliente.open("ControleArquivosProjeta") 
            aba = planilha.sheet1
            return aba

        def buscar_tarefas():
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_tarefas = planilha.worksheet("Tarefas")
                registros = aba_tarefas.get_all_records()
                return registros 
            except Exception as e:
                st.error(f"Erro ao buscar tarefas: {e}")
                return []

        if "tarefas" not in st.session_state:
            st.session_state["tarefas"] = buscar_tarefas()

        tarefas = st.session_state["tarefas"] 

        def buscar_descricoes():
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_descricoes = planilha.worksheet("Descricoes")
                registros = aba_descricoes.get_all_records()
                return registros
            except Exception as e:
                st.error(f"Erro ao carregar descrições: {e}")
                return []

        if "descricoes" not in st.session_state:
            st.session_state["descricoes"] = buscar_descricoes()

        descricoes = st.session_state["descricoes"]

        def extrair_prefixo(valor):
            return valor.split(" - ")[0] if " - " in valor else valor

        def gerar_nomes_arquivos(
            qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
            descricao_selecionada, sigla_descricao, revisao, extensoes_arquivos=None
        ):
            nomes_gerados = []
            if extensoes_arquivos is None:
                extensoes_arquivos = [""] * int(qtd_projetos)

            for idx in range(int(qtd_projetos)):
                extensao = extensoes_arquivos[idx] if idx < len(extensoes_arquivos) else ""

                prefixo_arquivo = extrair_prefixo(tipo_arquivo)
                prefixo_fase = extrair_prefixo(tipo_fase)
                prefixo_disciplina = extrair_prefixo(disciplina)

                ordem = str(idx + 1).zfill(2)
                total = str(int(qtd_projetos)).zfill(2)
                codigo_arquivo = f"{ordem}{total}"

                if descricao_selecionada == "Sem descrição":
                    if tipo_fase in ["Em andamento", "Interno"]:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_disciplina}-{codigo_arquivo}-V0{revisao}"    
                    else:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-REV0{revisao}"
                else:
                    if tipo_fase in ["Em andamento", "Interno"]:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-V0{revisao}"
                    else:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-REV0{revisao}"
                
                novo_nome = f"{nome_base}{extensao}"
                nomes_gerados.append(novo_nome)
            return nomes_gerados

        c1, c2 = st.columns([2, 1])
        with c1:
            st.title("Planos Urbanos")
        with c2:
            st.image("projeta.png", width=350)

        co1, co2 = st.columns(2)
        with co1:
            responsavel = st.text_input("Responsável")
        with co2:
            caminho = st.text_input("Caminho", help="Caminho onde o arquivo vai ser salvo na rede.")

        col1, col2 = st.columns(2)
        with col1:
            tipo_arquivo = st.selectbox("Arquivo", [
                "Selecione", "ATA - Ata de Reunião", "DGN - Diagnóstico", "EST - Estudo", "GPKG - GeoPackage", "LAU - Laudo", "LAYOUT - Layout", "MANUAL - Manual", 
                "MIN - Minuta", "MMD - Memorial Descritivo",  "OFI - Oficio", "PLN - Planilha", "PPT - Apresentação", "PRJ - Projeto", "RLT - Relatório", "TRF - Termo de Referência"
            ])
        with col2:
            nomes_tarefas = [t["nome_da_tarefa"] for t in tarefas]
            tarefa_selecionada = st.selectbox("Tarefa", nomes_tarefas)
            numero_tarefa = next((t["numero_da_tarefa"] for t in tarefas if t["nome_da_tarefa"] == tarefa_selecionada), "")

        colu1, colu2, colu3 = st.columns(3)
        with colu1:
            tipo_fase = st.selectbox("Fase", ["Selecione", "Em andamento","FIN - Final", "Interno", "PRE - Preliminar"])
        with colu2:
            disciplina = st.selectbox("Disciplina", [
                "Selecine", "PELE - Elétrica", "PINF - Infraestrutura", "PLU - Integrado / Gerais do Setor", "PJUR - Jurídico", "PMAB - Meio Ambiente", "PSOC - Social", "PTOP - Topografia", "PURB - Urbanismo / Geotecnia"
            ])
        with colu3:
            qtd_projetos = st.number_input("Quantidade de arquivos", min_value=1, step=1)

        colun1, colun2 = st.columns(2)
        with colun1:
            nomes_descricoes = [d["descricao_tarefa"] for d in descricoes]
            descricao_selecionada = st.selectbox("Descrição", nomes_descricoes)
            sigla_descricao = next(
                (d["sigla_descricao"] for d in descricoes if d["descricao_tarefa"] == descricao_selecionada),
                ""
            )

        with colun2:
            revisao = st.number_input("Revisão/Versão", min_value=0, step=1)

        uploaded_files = []
        for i in range(int(qtd_projetos)):
            uploaded_file = st.file_uploader(f"Arquivo {i + 1} (opcional para 'Nome dos arquivos')", key=f"file_uploader_{i}")
            uploaded_files.append(uploaded_file)

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Renomear arquivos"):
                campos_obrigatorios = {
                    "Responsável": responsavel.strip(),
                    "Caminho": caminho.strip(),
                    "Tipo de Arquivo": tipo_arquivo if tipo_arquivo != "Selecione" else "",
                    "Fase": tipo_fase if tipo_fase != "Selecione" else "",
                    "Disciplina": disciplina if disciplina != "Selecine" else "",
                    "Tarefa": tarefa_selecionada if tarefa_selecionada else ""
                }

                faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor]

                if faltando:
                    st.error(f"Preencha os campos obrigatórios: {', '.join(faltando)}")
                else:
                    if not all(uploaded_files):
                        st.error("Você precisa anexar todos os arquivos para renomeá-los e baixá-los.")
                    else:
                        arquivos_renomeados = []
                        extensoes = [os.path.splitext(f.name)[1] for f in uploaded_files if f is not None]
                        
                        nomes_gerados_para_download = gerar_nomes_arquivos(
                            qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
                            descricao_selecionada, sigla_descricao, revisao, extensoes
                        )

                        for idx, file in enumerate(uploaded_files):
                            if file:
                                novo_nome = nomes_gerados_para_download[idx]
                                conteudo = file.read()
                                arquivos_renomeados.append((novo_nome, conteudo))

                        if len(arquivos_renomeados) == int(qtd_projetos):
                            st.session_state['arquivos_prontos'] = arquivos_renomeados
                            st.success("Arquivos processados. Aguarde para download!")

                            try:
                                aba = conectar_google_sheets()
                                fuso_brasil = pytz.timezone("America/Sao_Paulo")
                                data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                                for nome_arquivo, _ in arquivos_renomeados:
                                    aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                                st.success("Nomes dos arquivos registrados no Google Sheets.")
                            except Exception as e:
                                st.error(f"Erro ao registrar no Google Sheets: {e}")
                        else:
                            st.error("Ocorreu um erro inesperado na geração dos nomes para download.")

                if 'arquivos_prontos' in st.session_state:
                    st.markdown("### Baixar Arquivos")
                    
                    # --- COMEÇA A MUDANÇA AQUI ---
                    if st.session_state['arquivos_prontos']: # Verifica se há arquivos para processar
                        zip_buffer = io.BytesIO() # Cria um buffer em memória para o arquivo ZIP
                        
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for nome_arquivo, conteudo in st.session_state['arquivos_prontos']:
                                # Adiciona cada arquivo ao ZIP com seu novo nome e conteúdo
                                zip_file.writestr(nome_arquivo, conteudo)
                        
                        # Prepara o buffer para leitura e download
                        zip_buffer.seek(0) 
                        
                        st.download_button(
                            label="Baixar Todos os Arquivos (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name="arquivos_renomeados.zip", # Nome do arquivo ZIP
                            mime="application/zip",
                            key="download_all_zip"
                        )
                        st.info(f"Após o download, mova o arquivo para: `{caminho}`")
                    else:
                        st.warning("Nenhum arquivo processado para download.")


        with col_btn2:
            if st.button("Nome dos arquivos"):
                campos_obrigatorios = {
                    "Responsável": responsavel.strip(),
                    "Caminho": caminho.strip(),
                    "Tipo de Arquivo": tipo_arquivo if tipo_arquivo != "Selecione" else "",
                    "Fase": tipo_fase if tipo_fase != "Selecione" else "",
                    "Disciplina": disciplina if disciplina != "Selecine" else "",
                    "Tarefa": tarefa_selecionada if tarefa_selecionada else ""
                }

                faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor]

                if faltando:
                    st.error(f"Preencha os campos obrigatórios para gerar os nomes: {', '.join(faltando)}")
                else:
                    extensoes = [os.path.splitext(f.name)[1] if f is not None else "" for f in uploaded_files]
                    
                    nomes_gerados = gerar_nomes_arquivos(
                        qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
                        descricao_selecionada, sigla_descricao, revisao, extensoes
                    )

                    if nomes_gerados:
                        st.markdown("### Nomes Gerados")

                        for idx, nome in enumerate(nomes_gerados):
                            st.write(f"**Arquivo {idx + 1}:**") 
                            st.code(nome, language='text')

                        try:
                            aba = conectar_google_sheets()
                            fuso_brasil = pytz.timezone("America/Sao_Paulo")
                            data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                            for nome_arquivo in nomes_gerados:
                                aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                            st.success("Nomes dos arquivos registrados no Google Sheets.")
                        except Exception as e:
                            st.error(f"Erro ao registrar os nomes no Google Sheets: {e}")
                    else:
                        st.warning("Nenhum nome de arquivo gerado. Verifique a quantidade de arquivos.")

    with abas[0]:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.title("Planos Urbanos")
        with c2:
            st.image("projeta.png", width=350)
            
        c1, c2 = st.columns([2, 1])
        with c1:
            tarefaMae = st.text_input("Nome da tarefa")
        with c2:
            numero = st.number_input("Número da tarefa", step=1)

        def salvar_tarefa(nome, numero):
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_tarefas = planilha.worksheet("Tarefas")
                aba_tarefas.append_row([nome, numero])
                return True
            except Exception as e:
                st.error(f"Erro ao salvar tarefa: {e}")
                return False

        if st.button("Adicionar Tarefa"):
            if tarefaMae.strip():
                sucesso = salvar_tarefa(tarefaMae.strip(), int(numero))
                if sucesso:
                    st.success(f"Tarefa '{tarefaMae}' adicionada com sucesso!")
                    st.session_state.pop("tarefas", None)  # limpa cache para recarregar
            else:
                st.warning("Preencha o nome da tarefa antes de salvar.")

    with abas[1]:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.title("Planos Urbanos")
        with c2:
            st.image("projeta.png", width=350)

        col1, col2 = st.columns(2)
        with col1:
            descricao_tarefa = st.text_input("Descrição")
        with col2:
            sigla_descricao = st.text_input("Sigla", max_chars=10)
            upper_sigla = sigla_descricao.upper()

        def salvar_descricao(desc, sigla):
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_descricoes = planilha.worksheet("Descricoes")
                aba_descricoes.append_row([desc, sigla])
                return True
            except Exception as e:
                st.error(f"Erro ao salvar descrição: {e}")
                return False

        if st.button("Adicionar Descrição"):
            if descricao_tarefa.strip() and sigla_descricao.strip():
                sucesso = salvar_descricao(descricao_tarefa.strip(), upper_sigla.strip().upper())
                if sucesso:
                    st.success("Descrição adicionada com sucesso!")
                    st.session_state.pop("descricoes", None)
            else:
                st.warning("Preencha os dois campos para salvar.")

else:
        def conectar_google_sheets():
            escopos = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            json_credencial = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
            credenciais = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json_credencial), escopos) 
            cliente = gspread.authorize(credenciais)
            planilha = cliente.open("ControleArquivosProjeta") 
            aba = planilha.sheet1
            return aba

        def buscar_tarefas():
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_tarefas = planilha.worksheet("Tarefas")
                registros = aba_tarefas.get_all_records()
                return registros 
            except Exception as e:
                st.error(f"Erro ao buscar tarefas: {e}")
                return []

        if "tarefas" not in st.session_state:
            st.session_state["tarefas"] = buscar_tarefas()

        tarefas = st.session_state["tarefas"] 

        def buscar_descricoes():
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_descricoes = planilha.worksheet("Descricoes")
                registros = aba_descricoes.get_all_records()
                return registros
            except Exception as e:
                st.error(f"Erro ao carregar descrições: {e}")
                return []

        if "descricoes" not in st.session_state:
            st.session_state["descricoes"] = buscar_descricoes()

        descricoes = st.session_state["descricoes"]

        def extrair_prefixo(valor):
            return valor.split(" - ")[0] if " - " in valor else valor

        def gerar_nomes_arquivos(
            qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
            descricao_selecionada, sigla_descricao, revisao, extensoes_arquivos=None
        ):
            nomes_gerados = []
            if extensoes_arquivos is None:
                extensoes_arquivos = [""] * int(qtd_projetos)

            for idx in range(int(qtd_projetos)):
                extensao = extensoes_arquivos[idx] if idx < len(extensoes_arquivos) else ""

                prefixo_arquivo = extrair_prefixo(tipo_arquivo)
                prefixo_fase = extrair_prefixo(tipo_fase)
                prefixo_disciplina = extrair_prefixo(disciplina)

                ordem = str(idx + 1).zfill(2)
                total = str(int(qtd_projetos)).zfill(2)
                codigo_arquivo = f"{ordem}{total}"

                if descricao_selecionada == "Sem descrição":
                    if tipo_fase in ["Em andamento", "Interno"]:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_disciplina}-{codigo_arquivo}-V0{revisao}"    
                    else:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-REV0{revisao}"
                else:
                    if tipo_fase in ["Em andamento", "Interno"]:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-V0{revisao}"
                    else:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-REV0{revisao}"
                
                novo_nome = f"{nome_base}{extensao}"
                nomes_gerados.append(novo_nome)
            return nomes_gerados

        c1, c2 = st.columns([2, 1])
        with c1:
            st.title("Planos Urbanos")
        with c2:
            st.image("projeta.png", width=350)

        co1, co2 = st.columns(2)
        with co1:
            responsavel = st.text_input("Responsável")
        with co2:
            caminho = st.text_input("Caminho", help="Caminho onde o arquivo vai ser salvo na rede.")

        col1, col2 = st.columns(2)
        with col1:
            tipo_arquivo = st.selectbox("Arquivo", [
                "Selecione", "ATA - Ata de Reunião", "DGN - Diagnóstico", "EST - Estudo", "GPKG - GeoPackage", "LAU - Laudo", "LAYOUT - Layout", "MANUAL - Manual", 
                "MIN - Minuta", "MMD - Memorial Descritivo",  "OFI - Oficio", "PLN - Planilha", "PPT - Apresentação", "PRJ - Projeto", "RLT - Relatório", "TRF - Termo de Referência"
            ])
        with col2:
            nomes_tarefas = [t["nome_da_tarefa"] for t in tarefas]
            tarefa_selecionada = st.selectbox("Tarefa", nomes_tarefas)
            numero_tarefa = next((t["numero_da_tarefa"] for t in tarefas if t["nome_da_tarefa"] == tarefa_selecionada), "")

        colu1, colu2, colu3 = st.columns(3)
        with colu1:
            tipo_fase = st.selectbox("Fase", ["Selecione", "Em andamento","FIN - Final", "Interno", "PRE - Preliminar"])
        with colu2:
            disciplina = st.selectbox("Disciplina", [
                "Selecine", "PELE - Elétrica", "PINF - Infraestrutura", "PLU - Integrado / Gerais do Setor", "PJUR - Jurídico", "PMAB - Meio Ambiente", "PSOC - Social", "PTOP - Topografia", "PURB - Urbanismo / Geotecnia"
            ])
        with colu3:
            qtd_projetos = st.number_input("Quantidade de arquivos", min_value=1, step=1)

        colun1, colun2 = st.columns(2)
        with colun1:
            nomes_descricoes = [d["descricao_tarefa"] for d in descricoes]
            descricao_selecionada = st.selectbox("Descrição", nomes_descricoes)
            sigla_descricao = next(
                (d["sigla_descricao"] for d in descricoes if d["descricao_tarefa"] == descricao_selecionada),
                ""
            )

        with colun2:
            revisao = st.number_input("Revisão/Versão", min_value=0, step=1)

        uploaded_files = []
        for i in range(int(qtd_projetos)):
            uploaded_file = st.file_uploader(f"Arquivo {i + 1} (opcional para 'Nome dos arquivos')", key=f"file_uploader_{i}")
            uploaded_files.append(uploaded_file)

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Renomear arquivos"):
                campos_obrigatorios = {
                    "Responsável": responsavel.strip(),
                    "Caminho": caminho.strip(),
                    "Tipo de Arquivo": tipo_arquivo if tipo_arquivo != "Selecione" else "",
                    "Fase": tipo_fase if tipo_fase != "Selecione" else "",
                    "Disciplina": disciplina if disciplina != "Selecine" else "",
                    "Tarefa": tarefa_selecionada if tarefa_selecionada else ""
                }

                faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor]

                if faltando:
                    st.error(f"Preencha os campos obrigatórios: {', '.join(faltando)}")
                else:
                    if not all(uploaded_files):
                        st.error("Você precisa anexar todos os arquivos para renomeá-los e baixá-los.")
                    else:
                        arquivos_renomeados = []
                        extensoes = [os.path.splitext(f.name)[1] for f in uploaded_files if f is not None]
                        
                        nomes_gerados_para_download = gerar_nomes_arquivos(
                            qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
                            descricao_selecionada, sigla_descricao, revisao, extensoes
                        )

                        for idx, file in enumerate(uploaded_files):
                            if file:
                                novo_nome = nomes_gerados_para_download[idx]
                                conteudo = file.read()
                                arquivos_renomeados.append((novo_nome, conteudo))

                        if len(arquivos_renomeados) == int(qtd_projetos):
                            st.session_state['arquivos_prontos'] = arquivos_renomeados
                            st.success("Arquivos processados. Aguarde para download!")

                            try:
                                aba = conectar_google_sheets()
                                fuso_brasil = pytz.timezone("America/Sao_Paulo")
                                data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                                for nome_arquivo, _ in arquivos_renomeados:
                                    aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                                st.success("Nomes dos arquivos registrados no Google Sheets.")
                            except Exception as e:
                                st.error(f"Erro ao registrar no Google Sheets: {e}")
                        else:
                            st.error("Ocorreu um erro inesperado na geração dos nomes para download.")

                if 'arquivos_prontos' in st.session_state:
                    st.markdown("### Baixar Arquivos")
                    
                    # --- COMEÇA A MUDANÇA AQUI ---
                    if st.session_state['arquivos_prontos']: # Verifica se há arquivos para processar
                        zip_buffer = io.BytesIO() # Cria um buffer em memória para o arquivo ZIP
                        
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for nome_arquivo, conteudo in st.session_state['arquivos_prontos']:
                                # Adiciona cada arquivo ao ZIP com seu novo nome e conteúdo
                                zip_file.writestr(nome_arquivo, conteudo)
                        
                        # Prepara o buffer para leitura e download
                        zip_buffer.seek(0) 
                        
                        st.download_button(
                            label="Baixar Todos os Arquivos (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name="arquivos_renomeados.zip", # Nome do arquivo ZIP
                            mime="application/zip",
                            key="download_all_zip"
                        )
                        st.info(f"Após o download, mova o arquivo para: `{caminho}`")
                    else:
                        st.warning("Nenhum arquivo processado para download.")


        with col_btn2:
            if st.button("Nome dos arquivos"):
                campos_obrigatorios = {
                    "Responsável": responsavel.strip(),
                    "Caminho": caminho.strip(),
                    "Tipo de Arquivo": tipo_arquivo if tipo_arquivo != "Selecione" else "",
                    "Fase": tipo_fase if tipo_fase != "Selecione" else "",
                    "Disciplina": disciplina if disciplina != "Selecine" else "",
                    "Tarefa": tarefa_selecionada if tarefa_selecionada else ""
                }

                faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor]

                if faltando:
                    st.error(f"Preencha os campos obrigatórios para gerar os nomes: {', '.join(faltando)}")
                else:
                    extensoes = [os.path.splitext(f.name)[1] if f is not None else "" for f in uploaded_files]
                    
                    nomes_gerados = gerar_nomes_arquivos(
                        qtd_projetos, tipo_arquivo, numero_tarefa, tipo_fase, disciplina,
                        descricao_selecionada, sigla_descricao, revisao, extensoes
                    )

                    if nomes_gerados:
                        st.markdown("### Nomes Gerados")

                        for idx, nome in enumerate(nomes_gerados):
                            st.write(f"**Arquivo {idx + 1}:**") 
                            st.code(nome, language='text')

                        try:
                            aba = conectar_google_sheets()
                            fuso_brasil = pytz.timezone("America/Sao_Paulo")
                            data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                            for nome_arquivo in nomes_gerados:
                                aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                            st.success("Nomes dos arquivos registrados no Google Sheets.")
                        except Exception as e:
                            st.error(f"Erro ao registrar os nomes no Google Sheets: {e}")
                    else:
                        st.warning("Nenhum nome de arquivo gerado. Verifique a quantidade de arquivos.")