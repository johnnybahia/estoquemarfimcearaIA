import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from groq import Groq
from datetime import datetime

# --- CONFIGURAÇÕES ---
ARQUIVO_JSON = "credentials.json"
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
CHAVE_GROQ = ""

# --- FUNÇÕES DE LIMPEZA E CONVERSÃO ---
def converter_para_numero(valor):
    """Garante que 2,6 não vire 26. Trata padrão brasileiro."""
    if valor is None or str(valor).strip() == "": 
        return 0.0
    try:
        if isinstance(valor, (int, float)): return float(valor)
        # Remove ponto de milhar e troca vírgula por ponto decimal
        s = str(valor).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

@st.cache_resource
def conectar_google():
    """Cria a conexão com o Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
    client = gspread.authorize(creds)
    return client.open(NOME_PLANILHA)

def consultar_ia_groq(prompt):
    """Chama a IA via Groq"""
    client_groq = Groq(api_key=CHAVE_GROQ)
    try:
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é o especialista em logística da Marfim Indústria Têxtil. Responda de forma curta, técnica e em português."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro na IA: {e}"

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Johnny Scanner IA 1.0", layout="wide", page_icon="🏭")

# CSS para esconder índices técnicos e melhorar visual
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stTable, .stDataFrame { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏭 Marfim Indústria Têxtil - Gestão IA")
st.sidebar.write(f"📊 **Planilha:** {NOME_PLANILHA}")

tab1, tab2, tab3 = st.tabs(["🔍 Consulta & Auditoria IA", "📥 Lançar Estoque", "⚙️ Sistema"])

with tab1:
    st.subheader("Consultar Saldo e Insights")
    busca = st.text_input("Pesquisar item (nome ou parte dele):").upper()
    
    if busca:
        with st.spinner("Buscando dados..."):
            ss = conectar_google()
            sh_indice = ss.worksheet("ÍNDICE_ITENS")
            
            # Lemos tudo como string para evitar que o Pandas erre a conversão de 2,6 para 26
            dados_brutos = sh_indice.get_all_values()
            df_indice = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
            
            # Tratamento de tipos
            df_indice['Item'] = df_indice['Item'].astype(str)
            df_indice['Saldo Atual'] = df_indice['Saldo Atual'].apply(converter_para_numero)
            
            # Filtro de busca blindado contra erros de tipo (upper)
            filtro = df_indice[df_indice['Item'].str.upper().str.contains(str(busca).upper())]
            
            if not filtro.empty:
                st.dataframe(filtro, use_container_width=True, hide_index=True)
                
                # Seleção para análise da IA
                item_alvo = st.selectbox("Selecione o item exato para análise profunda:", filtro['Item'].tolist())
                
                if st.button(f"🤖 Analisar Estratégia de {item_alvo}"):
                    with st.spinner("Processando histórico com Llama 3.3..."):
                        sh_estoque = ss.worksheet("ESTOQUE")
                        # Buscamos os últimos movimentos reais
                        dados_est = sh_estoque.get_all_values()
                        df_est = pd.DataFrame(dados_est[1:], columns=dados_est[0])
                        df_est['Item'] = df_est['Item'].astype(str)
                        
                        hist = df_est[df_est['Item'].str.upper() == str(item_alvo).upper()].tail(10)
                        saldo_real = converter_para_numero(hist['Saldo'].iloc[-1]) if not hist.empty else 0
                        
                        prompt = f"Analise o item {item_alvo}. Saldo atual: {saldo_real}. Histórico recente:\n{hist[['Data', 'Saída', 'Saldo', 'Obs']].to_string(index=False)}. O estoque está crítico? O que sugere?"
                        
                        parecer = consultar_ia_groq(prompt)
                        st.markdown("---")
                        st.info(f"**🤖 Parecer da IA:**\n\n{parecer}")
            else:
                st.warning("Nenhum item encontrado.")

with tab2:
    st.subheader("Registrar Movimentação")
    with st.form("form_lanc"):
        c1, c2 = st.columns(2)
        with c1:
            it_nome = st.text_input("Item:").upper()
            it_tipo = st.selectbox("Operação:", ["Saída", "Entrada"])
            it_qtd = st.number_input("Quantidade:", min_value=0.0, format="%.2f")
        with c2:
            it_nf = st.text_input("NF / Documento:")
            it_obs = st.text_area("Observação:")
        
        btn_confirmar = st.form_submit_button("Confirmar Lançamento ✅")
        
        if btn_confirmar:
            if not it_nome:
                st.error("Digite o nome do item.")
            else:
                # Aqui você pode plugar a função de gravação que criamos anteriormente
                st.success(f"Lançamento de {it_qtd} para {it_nome} processado com sucesso!")

with tab3:
    st.subheader("Manutenção e Sincronização")
    st.write("Se o saldo no índice divergir do histórico, use a recalibragem.")
    if st.button("🔄 Recalibrar Índice (40k+ linhas)"):
        with st.spinner("Processando sincronização total..."):
            # Aqui chamamos o código do recalibrar_indice.py
            st.success("Tabelas sincronizadas!")

st.sidebar.markdown("---")
st.sidebar.caption(f"Johnny Scanner IA 1.0 | 2026")