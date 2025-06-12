import os
import streamlit as st
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from io import StringIO

def conectar_google_sheets():
    escopos = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    json_credencial = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json_credencial), escopos)  
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open("ControleArquivosProjeta")  
    aba = planilha.sheet1
    return aba

st.set_page_config(page_title="Grupo Projeta", layout="wide")
st.markdown("""
    <style>
        /* Esconde a barra de ferramentas do Streamlit */
        .stAppHeader.st-emotion-cache-h4xjwg.e4hpqof0,
        ._terminalButton_rix23_138 
         {
        
            visibility: hidden;
        }

    </style>
""", unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])
with c1:
    st.title("Controle de Arquivos")
with c2:
    st.image("projeta.png", width=350)

co1, co2 = st.columns(2)
with co1:
    responsavel = st.text_input("Responsável")
with co2:
    caminho = st.text_input("Caminho")

col1, col2, col3 = st.columns(3)
with col1:
    tipo_arquivo = st.selectbox("Arquivo", [
        "Selecione", "PRJ - Projeto", "MMD - Memorial Descritivo", "MMC - Memória de Cálculo",
        "OFR - Ofício de Resposta", "OFC - Ofício Geral", "PLN - Planilha Orçamentária",
        "DGN - Diagnóstico", "PGN - Prognóstico", "ATA - Ata de Reunião", "RLT - Relatório"
    ])
with col2:
    tipo_fase = st.selectbox("Fase", [
        "Selecione", "ATP - Nível de Anteprojeto", "BSC - Nível Básico", "EXE - Nível Executivo"
    ])
with col3:
    disciplina = st.selectbox("Disciplina", [
        "Selecine", "ARQ - Projeto Arquitetônico", "CBM - Projeto de Cabeamento Estruturado",
        "CFV - Projeto de Alarme e Circuito Fechado de Televisão", "CLM - Projeto de Climatização",
        "CMV - Projeto de Comunicação Visual", "DRE - Projeto de Drenagem Pluvial",
        "EFV - Projeto de Energia Fotovoltaica", "ELE - Projeto de Elétrico", "EST - Projeto Estrutural",
        "GAS - Projeto de Gás", "GEO - Projeto de Geométrico", "GSM - Projeto de Gases Medicinais",
        "HDS - Projeto Hidrossanitário", "ORC - Orçamento", "PAV - Projeto de Pavimentação",
        "PCI - Projeto de Prevenção e Combate a Incêndio", "PSG - Projeto de Paisagismo",
        "R3D - Projeto de Representação Tridimensional", "RST - Projeto de Restauro",
        "SAA - Projeto de Sistema de Abastecimento de Água", "SES - Projeto de Sistema de Esgoto Sanitário",
        "SND - Sondagem", "SNL - Projeto de Sinalização Vertical e Horizontal",
        "SON - Projeto de Sonorização", "SPD - Projeto de Sistema de Proteção a Descargas Atmosféricas",
        "TOP - Projeto Topográfico", "TRP - Projeto de Terraplenagem", "URB - Projeto de Urbanização"
    ])

colu1, colu2, colu3 = st.columns(3)
with colu1:
    contratante = st.text_input("Contratante", placeholder="CMD",help="Abreviação do Contrato (nome da prefeitura ou município) isso normalmente é definido pela gerencia.")
with colu2:
    projeto = st.text_input("Projeto", placeholder="CMR",help="Abreviação geralmente definida pela gerência")
with colu3:
    qtd_projetos = st.number_input("Quantidade de arquivos", min_value=1, step=1)

colun1, colun2 = st.columns(2)
with colun1:
    descricao = st.text_input("Descrição", placeholder="Planta Baixa",help="Opcional")
with colun2:
    revisao = st.number_input("Revisão", min_value=0, step=1)
    
# Upload dos arquivos
uploaded_files = []
for i in range(int(qtd_projetos)):
    uploaded_file = st.file_uploader(f"Arquivo {i + 1}", key=f"file_{i}")
    uploaded_files.append(uploaded_file)

# Função para extrair prefixos
def extrair_prefixo(valor):
    return valor.split(" - ")[0] if " - " in valor else valor

if st.button("Renomear arquivos"):
    campos_obrigatorios = {
        "Responsável": responsavel.strip(),
        "Caminho": caminho.strip(),
        "Tipo de Arquivo": tipo_arquivo if tipo_arquivo != "Selecione" else "",
        "Fase": tipo_fase if tipo_fase != "Selecione" else "",
        "Disciplina": disciplina if disciplina != "Selecine" else "",
        "Contratante": contratante.strip(),
        "Projeto": projeto.strip(),
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

                if descricao.strip():
                    nome_base = f"{prefixo_arquivo}-{prefixo_fase}-{prefixo_disciplina}-{contratante}-{projeto}-{codigo_arquivo}-{descricao}-REV0{revisao}"
                else:
                    nome_base = f"{prefixo_arquivo}-{prefixo_fase}-{prefixo_disciplina}-{contratante}-{projeto}-{codigo_arquivo}-REV0{revisao}"

                extensao = os.path.splitext(file.name)[1]
                novo_nome = f"{nome_base}{extensao}"

                conteudo = file.read()
                arquivos_renomeados.append((novo_nome, conteudo))

        if len(arquivos_renomeados) == int(qtd_projetos):
            st.session_state['arquivos_prontos'] = arquivos_renomeados
            st.success("Arquivos processados. Prontos para download!")

            try:
                aba = conectar_google_sheets()
                for nome_arquivo, _ in arquivos_renomeados:
                    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    aba.append_row([responsavel, caminho, nome_arquivo, data_hora])
            except Exception as e:
                st.error(f"Erro ao registrar no Google Sheets: {e}")
        else:
            st.error("Você precisa anexar todos os arquivos antes de processar.")


# Botões de download individuais
if 'arquivos_prontos' in st.session_state:
    st.markdown("### Baixar Arquivos")
    for nome_arquivo, conteudo in st.session_state['arquivos_prontos']:
        st.download_button(
            label=f"Baixar {nome_arquivo}",
            data=conteudo,
            file_name=nome_arquivo,
            mime="application/octet-stream"
        )
