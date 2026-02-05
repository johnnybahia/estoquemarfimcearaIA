"""
Dashboard Unificado Inteligente - Marfim IA
Interface moderna com todas as funcionalidades do sistema
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from groq import Groq

# Importar módulos do sistema
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, VERSAO, NOME_SISTEMA, converter_para_numero
)

# Configuração da página
st.set_page_config(
    page_title="Marfim IA - Estoque Inteligente",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #c5a059;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #0a192f 0%, #1a365d 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #c5a059;
    }
    .alert-critical { background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 1rem; border-radius: 5px; }
    .alert-warning { background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem; border-radius: 5px; }
    .alert-success { background-color: #d1fae5; border-left: 4px solid #10b981; padding: 1rem; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_conexao():
    """Conexão com Google Sheets (cacheada)"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client


@st.cache_data(ttl=300)
def carregar_dados():
    """Carrega dados do estoque (cache de 5 min)"""
    client = get_conexao()
    ss = client.open(NOME_PLANILHA)

    # Índice
    sheet_idx = ss.worksheet("ÍNDICE_ITENS")
    dados_idx = sheet_idx.get_all_values()
    df_idx = pd.DataFrame(dados_idx[1:], columns=dados_idx[0])

    if 'Saldo Atual' in df_idx.columns:
        df_idx['Saldo'] = df_idx['Saldo Atual'].apply(converter_para_numero)

    # Histórico
    sheet_hist = ss.worksheet("ESTOQUE")
    dados_hist = sheet_hist.get_all_values()
    df_hist = pd.DataFrame(dados_hist[1:], columns=dados_hist[0])

    for col in ['Entrada', 'Saída', 'Saldo']:
        if col in df_hist.columns:
            df_hist[col] = df_hist[col].apply(converter_para_numero)

    df_hist['Data'] = pd.to_datetime(df_hist['Data'], format='%d/%m/%Y', errors='coerce')

    return df_idx, df_hist


def calcular_metricas(df_idx, df_hist):
    """Calcula métricas principais"""
    hoje = datetime.now()
    data_30d = hoje - timedelta(days=30)

    # Consumo 30 dias
    consumo_30d = df_hist[df_hist['Data'] >= data_30d].groupby('Item')['Saída'].sum()
    df_idx['Consumo_30d'] = df_idx['Item'].map(consumo_30d).fillna(0)
    df_idx['Media_Diaria'] = df_idx['Consumo_30d'] / 30
    df_idx['Dias_Cobertura'] = df_idx.apply(
        lambda r: r['Saldo'] / r['Media_Diaria'] if r['Media_Diaria'] > 0 else 999,
        axis=1
    )

    return df_idx


def consultar_ia(prompt, contexto=""):
    """Consulta a IA com um prompt"""
    if not CHAVE_GROQ:
        return "⚠️ Configure CHAVE_GROQ no config.py para usar a IA"

    try:
        client = Groq(api_key=CHAVE_GROQ)
        completion = client.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": f"Você é o assistente de estoque da Marfim Têxtil. {contexto}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro: {e}"


def pagina_dashboard():
    """Página principal do dashboard"""
    st.markdown('<div class="main-header">🏭 Marfim IA - Estoque Inteligente</div>', unsafe_allow_html=True)

    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # KPIs principais
    col1, col2, col3, col4, col5 = st.columns(5)

    total_itens = len(df_idx)
    itens_criticos = len(df_idx[df_idx['Dias_Cobertura'] < 15])
    itens_zerados = len(df_idx[df_idx['Saldo'] == 0])
    itens_negativos = len(df_idx[df_idx['Saldo'] < 0])
    consumo_total = df_idx['Consumo_30d'].sum()

    col1.metric("📦 Total Itens", f"{total_itens:,}")
    col2.metric("🔴 Críticos", itens_criticos, delta=f"{itens_criticos/total_itens*100:.1f}%")
    col3.metric("⚪ Zerados", itens_zerados)
    col4.metric("❌ Negativos", itens_negativos)
    col5.metric("📈 Consumo 30d", f"{consumo_total:,.0f}")

    st.divider()

    # Gráficos
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("📊 Top 10 Maior Consumo")
        top_consumo = df_idx.nlargest(10, 'Consumo_30d')
        fig = px.bar(
            top_consumo,
            x='Consumo_30d',
            y='Item',
            orientation='h',
            color='Consumo_30d',
            color_continuous_scale='Oranges'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_graf2:
        st.subheader("⚠️ Itens Mais Críticos")
        criticos = df_idx[df_idx['Dias_Cobertura'] < 30].nsmallest(10, 'Dias_Cobertura')
        fig = px.bar(
            criticos,
            x='Dias_Cobertura',
            y='Item',
            orientation='h',
            color='Dias_Cobertura',
            color_continuous_scale='Reds_r'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Distribuição de cobertura
    st.subheader("📈 Distribuição de Cobertura de Estoque")
    df_idx['Faixa_Cobertura'] = pd.cut(
        df_idx['Dias_Cobertura'].clip(upper=100),
        bins=[0, 7, 15, 30, 60, 100],
        labels=['< 7 dias', '7-15 dias', '15-30 dias', '30-60 dias', '> 60 dias']
    )
    faixas = df_idx['Faixa_Cobertura'].value_counts().sort_index()

    fig = px.pie(
        values=faixas.values,
        names=faixas.index,
        color_discrete_sequence=['#ef4444', '#f59e0b', '#eab308', '#22c55e', '#3b82f6']
    )
    st.plotly_chart(fig, use_container_width=True)


def pagina_consulta():
    """Página de consulta de itens"""
    st.header("🔍 Consulta de Estoque")

    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # Busca
    busca = st.text_input("Buscar item:", placeholder="Digite o nome do item...")

    if busca:
        resultado = df_idx[df_idx['Item'].str.upper().str.contains(busca.upper(), na=False)]

        if not resultado.empty:
            st.success(f"✅ {len(resultado)} item(s) encontrado(s)")

            for _, row in resultado.iterrows():
                with st.expander(f"📦 {row['Item']}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Saldo Atual", f"{row['Saldo']:,.0f}")
                    col2.metric("Consumo 30d", f"{row['Consumo_30d']:,.0f}")
                    col3.metric("Cobertura", f"{row['Dias_Cobertura']:.0f} dias")

                    # Histórico do item
                    hist_item = df_hist[df_hist['Item'] == row['Item']].tail(10)
                    if not hist_item.empty:
                        st.write("**Últimas movimentações:**")
                        st.dataframe(
                            hist_item[['Data', 'Entrada', 'Saída', 'Saldo', 'Obs']],
                            hide_index=True
                        )

                    # Análise IA
                    if st.button(f"🤖 Analisar {row['Item']}", key=f"ia_{row['Item']}"):
                        with st.spinner("Analisando..."):
                            prompt = f"""
Analise este item de estoque:
- Item: {row['Item']}
- Saldo: {row['Saldo']}
- Consumo 30d: {row['Consumo_30d']}
- Cobertura: {row['Dias_Cobertura']:.0f} dias

Forneça: situação atual, recomendação de compra e riscos.
"""
                            resposta = consultar_ia(prompt)
                            st.info(resposta)
        else:
            st.warning("Nenhum item encontrado")


def pagina_alertas():
    """Página de alertas"""
    st.header("🚨 Alertas do Sistema")

    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        tipo_alerta = st.selectbox(
            "Tipo de Alerta",
            ["Todos", "Críticos (<7 dias)", "Urgentes (<15 dias)", "Atenção (<30 dias)", "Zerados", "Negativos"]
        )

    # Aplicar filtros
    if tipo_alerta == "Críticos (<7 dias)":
        df_filtrado = df_idx[df_idx['Dias_Cobertura'] < 7]
    elif tipo_alerta == "Urgentes (<15 dias)":
        df_filtrado = df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)]
    elif tipo_alerta == "Atenção (<30 dias)":
        df_filtrado = df_idx[(df_idx['Dias_Cobertura'] >= 15) & (df_idx['Dias_Cobertura'] < 30)]
    elif tipo_alerta == "Zerados":
        df_filtrado = df_idx[df_idx['Saldo'] == 0]
    elif tipo_alerta == "Negativos":
        df_filtrado = df_idx[df_idx['Saldo'] < 0]
    else:
        df_filtrado = df_idx[df_idx['Dias_Cobertura'] < 30]

    # Resumo
    st.markdown(f"""
    <div class="alert-critical">
        <strong>🔴 Críticos:</strong> {len(df_idx[df_idx['Dias_Cobertura'] < 7])} itens
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="alert-warning">
        <strong>🟡 Urgentes:</strong> {len(df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)])} itens
    </div>
    """, unsafe_allow_html=True)

    # Tabela
    st.subheader(f"📋 {len(df_filtrado)} itens")

    if not df_filtrado.empty:
        st.dataframe(
            df_filtrado[['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']].sort_values('Dias_Cobertura'),
            hide_index=True,
            use_container_width=True
        )

        # Análise IA
        if st.button("🤖 Gerar Análise IA dos Alertas"):
            with st.spinner("Analisando alertas..."):
                itens_str = "\n".join([
                    f"- {r['Item']}: {r['Dias_Cobertura']:.0f} dias cobertura"
                    for _, r in df_filtrado.head(15).iterrows()
                ])
                prompt = f"""
Analise estes alertas de estoque:

{itens_str}

Forneça:
1. Avaliação geral da situação
2. Top 5 prioridades
3. Ações recomendadas para os próximos 7 dias
"""
                resposta = consultar_ia(prompt)
                st.info(resposta)


def pagina_lista_compras():
    """Página de lista de compras"""
    st.header("🛒 Lista de Compras Inteligente")

    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # Parâmetros
    col1, col2 = st.columns(2)
    with col1:
        dias_cobertura = st.slider("Cobertura alvo (dias)", 15, 90, 45)
    with col2:
        margem = st.slider("Margem de segurança (%)", 0, 50, 20)

    # Calcular lista
    margem_mult = 1 + margem / 100

    df_compras = df_idx[
        (df_idx['Dias_Cobertura'] < dias_cobertura) &
        (df_idx['Media_Diaria'] > 0)
    ].copy()

    df_compras['Qtd_Sugerida'] = (
        df_compras['Media_Diaria'] * dias_cobertura * margem_mult - df_compras['Saldo']
    ).clip(lower=0).round(0)

    df_compras = df_compras[df_compras['Qtd_Sugerida'] > 0].sort_values('Dias_Cobertura')

    # Resumo
    total_itens = len(df_compras)
    total_unidades = df_compras['Qtd_Sugerida'].sum()

    col1, col2 = st.columns(2)
    col1.metric("📦 Itens para comprar", total_itens)
    col2.metric("📊 Total de unidades", f"{total_unidades:,.0f}")

    # Tabela
    if not df_compras.empty:
        st.dataframe(
            df_compras[['Item', 'Saldo', 'Media_Diaria', 'Dias_Cobertura', 'Qtd_Sugerida']].head(50),
            hide_index=True,
            use_container_width=True
        )

        # Exportar
        csv = df_compras.to_csv(index=False)
        st.download_button(
            "📥 Baixar Lista (CSV)",
            csv,
            f"lista_compras_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

        # Análise IA
        if st.button("🤖 Gerar Análise IA"):
            with st.spinner("Analisando..."):
                prompt = f"""
Lista de compras gerada:
- Total: {total_itens} itens
- {total_unidades:,.0f} unidades
- Cobertura alvo: {dias_cobertura} dias

Top 10 itens:
{df_compras[['Item', 'Qtd_Sugerida', 'Dias_Cobertura']].head(10).to_string()}

Forneça recomendações de compra e priorização.
"""
                resposta = consultar_ia(prompt)
                st.info(resposta)


def pagina_chatbot():
    """Página do chatbot"""
    st.header("🤖 Assistente de Estoque")

    # Inicializar histórico
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Carregar dados para contexto
    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # Exibir histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Faça uma pergunta sobre o estoque..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                # Construir contexto
                stats = f"""
Dados do estoque:
- Total itens: {len(df_idx)}
- Críticos: {len(df_idx[df_idx['Dias_Cobertura'] < 15])}
- Zerados: {len(df_idx[df_idx['Saldo'] == 0])}
- Consumo 30d: {df_idx['Consumo_30d'].sum():,.0f}

Top 5 consumo: {df_idx.nlargest(5, 'Consumo_30d')['Item'].tolist()}
Top 5 críticos: {df_idx[df_idx['Dias_Cobertura'] < 30].nsmallest(5, 'Dias_Cobertura')['Item'].tolist()}
"""
                resposta = consultar_ia(prompt, contexto=stats)
                st.markdown(resposta)

        st.session_state.messages.append({"role": "assistant", "content": resposta})

    # Limpar chat
    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.rerun()


def pagina_relatorios():
    """Página de relatórios"""
    st.header("📊 Relatórios e Análises")

    df_idx, df_hist = carregar_dados()
    df_idx = calcular_metricas(df_idx, df_hist)

    # Seletor de relatório
    relatorio = st.selectbox(
        "Selecione o relatório",
        ["Visão Geral", "Consumo por Período", "Tendências", "Curva ABC"]
    )

    if relatorio == "Visão Geral":
        st.subheader("📈 Visão Geral do Estoque")

        col1, col2 = st.columns(2)

        with col1:
            # Status dos itens
            status = {
                'Normal': len(df_idx[df_idx['Dias_Cobertura'] >= 30]),
                'Atenção': len(df_idx[(df_idx['Dias_Cobertura'] >= 15) & (df_idx['Dias_Cobertura'] < 30)]),
                'Urgente': len(df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)]),
                'Crítico': len(df_idx[df_idx['Dias_Cobertura'] < 7])
            }
            fig = px.pie(
                values=list(status.values()),
                names=list(status.keys()),
                title="Status dos Itens",
                color_discrete_sequence=['#22c55e', '#eab308', '#f59e0b', '#ef4444']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Grupos
            if 'Grupo' in df_idx.columns:
                grupos = df_idx.groupby('Grupo')['Item'].count().sort_values(ascending=False).head(10)
                fig = px.bar(x=grupos.values, y=grupos.index, orientation='h', title="Top 10 Grupos")
                st.plotly_chart(fig, use_container_width=True)

    elif relatorio == "Consumo por Período":
        st.subheader("📈 Análise de Consumo")

        # Consumo mensal
        df_hist['Mes'] = df_hist['Data'].dt.to_period('M').astype(str)
        consumo_mensal = df_hist.groupby('Mes')['Saída'].sum().tail(12)

        fig = px.line(
            x=consumo_mensal.index,
            y=consumo_mensal.values,
            title="Consumo Mensal (últimos 12 meses)",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

    elif relatorio == "Curva ABC":
        st.subheader("📊 Curva ABC")

        df_abc = df_idx[df_idx['Consumo_30d'] > 0].sort_values('Consumo_30d', ascending=False)
        total = df_abc['Consumo_30d'].sum()
        df_abc['Percentual'] = df_abc['Consumo_30d'] / total * 100
        df_abc['Acumulado'] = df_abc['Percentual'].cumsum()
        df_abc['Classe'] = df_abc['Acumulado'].apply(
            lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
        )

        # Resumo
        for classe in ['A', 'B', 'C']:
            qtd = len(df_abc[df_abc['Classe'] == classe])
            pct = df_abc[df_abc['Classe'] == classe]['Percentual'].sum()
            st.write(f"**Classe {classe}:** {qtd} itens ({pct:.1f}% do consumo)")

        # Gráfico
        fig = px.bar(
            df_abc.head(30),
            x='Item',
            y='Consumo_30d',
            color='Classe',
            title="Top 30 Itens - Curva ABC"
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Função principal"""
    # Sidebar
    st.sidebar.image("https://via.placeholder.com/150x50?text=MARFIM", width=150)
    st.sidebar.title("🏭 Marfim IA")
    st.sidebar.caption(f"v{VERSAO}")

    # Menu
    pagina = st.sidebar.radio(
        "Menu",
        ["📊 Dashboard", "🔍 Consulta", "🚨 Alertas", "🛒 Lista de Compras", "🤖 Assistente IA", "📈 Relatórios"]
    )

    st.sidebar.divider()
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"Atualizado: {datetime.now().strftime('%H:%M')}")

    # Renderizar página
    if pagina == "📊 Dashboard":
        pagina_dashboard()
    elif pagina == "🔍 Consulta":
        pagina_consulta()
    elif pagina == "🚨 Alertas":
        pagina_alertas()
    elif pagina == "🛒 Lista de Compras":
        pagina_lista_compras()
    elif pagina == "🤖 Assistente IA":
        pagina_chatbot()
    elif pagina == "📈 Relatórios":
        pagina_relatorios()


if __name__ == "__main__":
    main()
