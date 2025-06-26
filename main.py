import os
import streamlit as st
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from io import StringIO
import pytz

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
    "Coordenador": {
        "perfil": st.secrets["usuarios"]["Lideranças"]["perfil"],
        "senha": st.secrets["usuarios"]["Lideranças"]["senha"]

    },
    "Projetista": {
        "perfil": st.secrets["usuarios"]["Técnicos"]["perfil"],
        "senha": st.secrets["usuarios"]["Técnicos"]["senha"]

    }
}
# Função de login
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("###  Acesso Restrito")
            usuario = st.text_input("Usuário", placeholder="Liderança ou Técnicos")
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")

            if submit:
                if usuario in USUARIOS and senha == USUARIOS[usuario]["senha"]:
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# Impede o uso se não estiver logado
if not st.session_state.usuario:
    login()
    st.stop()

perfil = USUARIOS[st.session_state.usuario]["perfil"]


if perfil == "Coordenador":
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

        # ✅ Buscar tarefas só uma vez ao abrir
        def buscar_tarefas():
            try:
                planilha = conectar_google_sheets().spreadsheet
                aba_tarefas = planilha.worksheet("Tarefas")
                registros = aba_tarefas.get_all_records()
                return registros  
            except Exception as e:
                st.error(f"Erro ao buscar tarefas: {e}")
                return []

        # ✅ Armazena uma única vez na sessão
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
                "Selecione", "ATA - Ata de Reunião", "PPT - Apresentação", "DCLV - Declividade", "DGN - Diagnóstico", "EST - Estudo", "GPKG - GeoPackage", "LAU - Laudo", "LAYOUT - Layout", "MANUAL - Manual", 
                "MMD - Memorial Descritivo", "MIN - Minuta", "MDL - Modelo", "OFI - Oficio", "PLN - Planilha", "PRJ - Projeto", "RLT - Relatório"
            ])
        with col2:
            nomes_tarefas = [t["nome_da_tarefa"] for t in tarefas]
            tarefa_selecionada = st.selectbox("Tarefa", nomes_tarefas)
            numero_tarefa = next((t["numero_da_tarefa"] for t in tarefas if t["nome_da_tarefa"] == tarefa_selecionada), "")

        colu1, colu2, colu3 = st.columns(3)
        with colu1:
            tipo_fase = st.selectbox("Fase", ["Selecione", "FIN - Nível Final", "PRE - Nível Preliminar"

            ])
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
            revisao = st.number_input("Revisão", min_value=0, step=1)

        uploaded_files = []
        for i in range(int(qtd_projetos)):
            uploaded_file = st.file_uploader(f"Arquivo {i + 1}", key=f"file_{i}")
            uploaded_files.append(uploaded_file)

        def extrair_prefixo(valor):
            return valor.split(" - ")[0] if " - " in valor else valor

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
                arquivos_renomeados = []

                for idx, file in enumerate(uploaded_files):
                    if file:
                        prefixo_arquivo = extrair_prefixo(tipo_arquivo)
                        prefixo_fase = extrair_prefixo(tipo_fase)
                        prefixo_disciplina = extrair_prefixo(disciplina)

                        ordem = str(idx + 1).zfill(2)
                        total = str(int(qtd_projetos)).zfill(2)
                        codigo_arquivo = f"{ordem}{total}"

                        if descricao_selecionada == "Sem descrição":
                            nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-REV0{revisao}"
                        else:
                            nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-REV0{revisao}"

                        extensao = os.path.splitext(file.name)[1]
                        novo_nome = f"{nome_base}{extensao}"

                        conteudo = file.read()
                        arquivos_renomeados.append((novo_nome, conteudo))

                if len(arquivos_renomeados) == int(qtd_projetos):
                    st.session_state['arquivos_prontos'] = arquivos_renomeados
                    st.success("Arquivos processados. Aguarde para download!")

                    try:
                        aba = conectar_google_sheets()
                        for nome_arquivo, _ in arquivos_renomeados:
                            fuso_brasil = pytz.timezone("America/Sao_Paulo")
                            data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                            aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                    except Exception as e:
                        st.error(f"Erro ao registrar no Google Sheets: {e}")
                else:
                    st.error("Você precisa anexar todos os arquivos antes de processar.")

        if 'arquivos_prontos' in st.session_state:
            st.markdown("### Baixar Arquivos")
            for nome_arquivo, conteudo in st.session_state['arquivos_prontos']:
                st.download_button(
                    label=f"Baixar {nome_arquivo}",
                    data=conteudo,
                    file_name=nome_arquivo,
                    mime="application/octet-stream"
                )
            st.info(f"Após o download, mova o arquivo para: `{caminho}`")

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

    # ✅ Buscar tarefas só uma vez ao abrir
    def buscar_tarefas():
        try:
            planilha = conectar_google_sheets().spreadsheet
            aba_tarefas = planilha.worksheet("Tarefas")
            registros = aba_tarefas.get_all_records()
            return registros  
        except Exception as e:
            st.error(f"Erro ao buscar tarefas: {e}")
            return []

    # ✅ Armazena uma única vez na sessão
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
            "Selecione", "ATA - Ata de Reunião", "PPT - Apresentação", "DCLV - Declividade", "DGN - Diagnóstico", "EST - Estudo", "GPKG - GeoPackage", "LAU - Laudo", "LAYOUT - Layout", "MANUAL - Manual",
            "MMD - Memorial Descritivo", "MIN - Minuta", "MDL - Modelo", "OFI - Oficio", "PLN - Planilha", "PRJ - Projeto", "RLT - Relatório"
        ])
    with col2:
        nomes_tarefas = [t["nome_da_tarefa"] for t in tarefas]
        tarefa_selecionada = st.selectbox("Tarefa", nomes_tarefas)
        numero_tarefa = next((t["numero_da_tarefa"] for t in tarefas if t["nome_da_tarefa"] == tarefa_selecionada), "")

    colu1, colu2, colu3 = st.columns(3)
    with colu1:
        tipo_fase = st.selectbox("Fase", [ "Selecione", "FIN - Nível Final", "PRE - Nível Preliminar"
        ])
    with colu2:
        disciplina = st.selectbox("Disciplina", [
            "Selecine", "PELE - Eletrica", "PINF - Infraestrutura", "PLU - Integrado / Gerais do Setor", "PJUR - Jurídico", "PMAB - Meio Ambiente", "PSOC - Social", "PTOP - Topografia", "PURB - Urbanismo / Geotecnia"
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
        revisao = st.number_input("Revisão", min_value=0, step=1)

    uploaded_files = []
    for i in range(int(qtd_projetos)):
        uploaded_file = st.file_uploader(f"Arquivo {i + 1}", key=f"file_{i}")
        uploaded_files.append(uploaded_file)

    def extrair_prefixo(valor):
        return valor.split(" - ")[0] if " - " in valor else valor

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
            arquivos_renomeados = []

            for idx, file in enumerate(uploaded_files):
                if file:
                    prefixo_arquivo = extrair_prefixo(tipo_arquivo)
                    prefixo_fase = extrair_prefixo(tipo_fase)
                    prefixo_disciplina = extrair_prefixo(disciplina)

                    ordem = str(idx + 1).zfill(2)
                    total = str(int(qtd_projetos)).zfill(2)
                    codigo_arquivo = f"{ordem}{total}"

                    if descricao_selecionada == "Sem descrição":
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-REV0{revisao}"
                    else:
                        nome_base = f"{prefixo_arquivo}-{numero_tarefa}-{prefixo_fase}-{prefixo_disciplina}-{codigo_arquivo}-{sigla_descricao}-REV0{revisao}"

                    extensao = os.path.splitext(file.name)[1]
                    novo_nome = f"{nome_base}{extensao}"

                    conteudo = file.read()
                    arquivos_renomeados.append((novo_nome, conteudo))

            if len(arquivos_renomeados) == int(qtd_projetos):
                st.session_state['arquivos_prontos'] = arquivos_renomeados
                st.success("Arquivos processados. Aguarde para download!")

                try:
                    aba = conectar_google_sheets()
                    for nome_arquivo, _ in arquivos_renomeados:
                        fuso_brasil = pytz.timezone("America/Sao_Paulo")
                        data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
                        aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
                except Exception as e:
                    st.error(f"Erro ao registrar no Google Sheets: {e}")
            else:
                st.error("Você precisa anexar todos os arquivos antes de processar.")

    if 'arquivos_prontos' in st.session_state:
        st.markdown("### Baixar Arquivos")
        for nome_arquivo, conteudo in st.session_state['arquivos_prontos']:
            st.download_button(
                label=f"Baixar {nome_arquivo}",
                data=conteudo,
                file_name=nome_arquivo,
                mime="application/octet-stream"
            )
        st.info(f"Após o download, mova o arquivo para: `{caminho}`")
