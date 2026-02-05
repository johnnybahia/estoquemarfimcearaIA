"""
Calculador de Estoque Mínimo Otimizado
Calcula ponto de pedido e estoque de segurança usando análise estatística
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, converter_para_numero
)

class CalculadorEstoqueMinimo:
    """Calcula estoque mínimo, ponto de pedido e estoque de segurança"""

    def __init__(self):
        self.df_historico = None
        self.df_parametros = None
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_dados(self):
        """Carrega histórico de movimentações"""
        print("📡 Carregando dados...")
        ss = self.conectar()

        # Histórico
        sheet = ss.worksheet("ESTOQUE")
        dados = sheet.get_all_values()
        self.df_historico = pd.DataFrame(dados[1:], columns=dados[0])

        for col in ['Entrada', 'Saída', 'Saldo']:
            self.df_historico[col] = self.df_historico[col].apply(converter_para_numero)

        self.df_historico['Data'] = pd.to_datetime(
            self.df_historico['Data'], format='%d/%m/%Y', errors='coerce'
        )

        # Índice para saldo atual
        sheet_idx = ss.worksheet("ÍNDICE_ITENS")
        dados_idx = sheet_idx.get_all_values()
        df_idx = pd.DataFrame(dados_idx[1:], columns=dados_idx[0])
        df_idx['Saldo'] = df_idx['Saldo Atual'].apply(converter_para_numero)

        self.df_saldo = df_idx[['Item', 'Saldo']].copy()

        print(f"✅ Dados carregados")

    def calcular_lead_time(self, item_nome):
        """Calcula lead time médio baseado no histórico de entradas"""
        df_item = self.df_historico[
            (self.df_historico['Item'].str.upper() == item_nome.upper()) &
            (self.df_historico['Entrada'] > 0)
        ].sort_values('Data')

        if len(df_item) < 2:
            return 7  # Default: 7 dias

        # Intervalo entre entregas
        intervalos = df_item['Data'].diff().dropna().dt.days
        intervalos = intervalos[intervalos > 0]

        if len(intervalos) == 0:
            return 7

        return max(3, min(30, intervalos.mean()))  # Entre 3 e 30 dias

    def calcular_parametros_item(self, item_nome, nivel_servico=0.95):
        """
        Calcula parâmetros de estoque para um item:
        - Consumo médio diário
        - Desvio padrão do consumo
        - Lead time médio
        - Estoque de segurança
        - Ponto de pedido
        - Estoque mínimo
        - Estoque máximo
        """
        df_item = self.df_historico[
            self.df_historico['Item'].str.upper() == item_nome.upper()
        ].copy()

        if df_item.empty:
            return None

        # Consumo diário (últimos 90 dias)
        hoje = datetime.now()
        df_90d = df_item[df_item['Data'] >= (hoje - timedelta(days=90))]

        if df_90d.empty:
            df_90d = df_item

        # Agrupar consumo por dia
        consumo_diario = df_90d.groupby(df_90d['Data'].dt.date)['Saída'].sum()

        if len(consumo_diario) == 0:
            return None

        # Estatísticas de consumo
        media_diaria = consumo_diario.mean()
        desvio_diario = consumo_diario.std() if len(consumo_diario) > 1 else media_diaria * 0.2
        if pd.isna(desvio_diario) or desvio_diario == 0:
            desvio_diario = media_diaria * 0.2

        # Lead time
        lead_time = self.calcular_lead_time(item_nome)

        # Fator Z para nível de serviço (distribuição normal)
        z_scores = {
            0.90: 1.28,
            0.95: 1.65,
            0.97: 1.88,
            0.99: 2.33
        }
        z = z_scores.get(nivel_servico, 1.65)

        # Estoque de segurança = Z * σ * √(LT)
        estoque_seguranca = z * desvio_diario * np.sqrt(lead_time)

        # Ponto de pedido = (Demanda média × Lead Time) + Estoque de Segurança
        ponto_pedido = (media_diaria * lead_time) + estoque_seguranca

        # Estoque mínimo = Ponto de pedido (para simplificar)
        estoque_minimo = ponto_pedido

        # Estoque máximo = Ponto de pedido + Lote econômico (estimado como 30 dias de consumo)
        lote_economico = media_diaria * 30
        estoque_maximo = ponto_pedido + lote_economico

        # Saldo atual
        saldo_atual = self.df_saldo[
            self.df_saldo['Item'].str.upper() == item_nome.upper()
        ]['Saldo'].values

        saldo_atual = saldo_atual[0] if len(saldo_atual) > 0 else 0

        # Status
        if saldo_atual <= 0:
            status = "RUPTURA"
        elif saldo_atual < estoque_seguranca:
            status = "CRITICO"
        elif saldo_atual < ponto_pedido:
            status = "COMPRAR"
        elif saldo_atual < estoque_maximo:
            status = "NORMAL"
        else:
            status = "EXCESSO"

        return {
            'item': item_nome,
            'saldo_atual': round(saldo_atual, 0),
            'media_diaria': round(media_diaria, 2),
            'desvio_diario': round(desvio_diario, 2),
            'lead_time_dias': round(lead_time, 0),
            'nivel_servico': f"{nivel_servico*100:.0f}%",
            'estoque_seguranca': round(estoque_seguranca, 0),
            'ponto_pedido': round(ponto_pedido, 0),
            'estoque_minimo': round(estoque_minimo, 0),
            'estoque_maximo': round(estoque_maximo, 0),
            'lote_sugerido': round(lote_economico, 0),
            'dias_cobertura': round(saldo_atual / media_diaria, 0) if media_diaria > 0 else 999,
            'status': status
        }

    def calcular_todos_itens(self, nivel_servico=0.95):
        """Calcula parâmetros para todos os itens"""
        if self.df_historico is None:
            self.carregar_dados()

        print(f"\n⚙️ Calculando parâmetros (nível de serviço: {nivel_servico*100:.0f}%)...")

        itens_unicos = self.df_historico['Item'].unique()
        parametros = []

        for item in itens_unicos:
            params = self.calcular_parametros_item(item, nivel_servico)
            if params and params['media_diaria'] > 0:
                parametros.append(params)

        # Ordenar por status
        ordem_status = {'RUPTURA': 0, 'CRITICO': 1, 'COMPRAR': 2, 'NORMAL': 3, 'EXCESSO': 4}
        parametros.sort(key=lambda x: (ordem_status.get(x['status'], 5), -x['media_diaria']))

        self.df_parametros = pd.DataFrame(parametros)
        print(f"✅ {len(parametros)} itens calculados")

        return parametros

    def gerar_relatorio_ia(self, item_nome=None):
        """Gera relatório com recomendações da IA"""
        if not self.client_groq:
            return "IA não disponível"

        if item_nome:
            params = self.calcular_parametros_item(item_nome)
            if not params:
                return f"Item {item_nome} não encontrado"

            contexto = f"""
ANÁLISE DE ESTOQUE MÍNIMO - {item_nome}

Parâmetros calculados:
- Saldo atual: {params['saldo_atual']} un
- Consumo médio diário: {params['media_diaria']} un
- Desvio padrão diário: {params['desvio_diario']} un
- Lead time fornecedor: {params['lead_time_dias']} dias
- Nível de serviço: {params['nivel_servico']}

Níveis de estoque recomendados:
- Estoque de Segurança: {params['estoque_seguranca']} un
- Ponto de Pedido: {params['ponto_pedido']} un
- Estoque Mínimo: {params['estoque_minimo']} un
- Estoque Máximo: {params['estoque_maximo']} un
- Lote de compra sugerido: {params['lote_sugerido']} un

Status atual: {params['status']}
Cobertura atual: {params['dias_cobertura']} dias
"""
        else:
            if self.df_parametros is None:
                self.calcular_todos_itens()

            # Resumo geral
            status_count = self.df_parametros['status'].value_counts().to_dict()
            contexto = f"""
ANÁLISE GERAL DE ESTOQUE MÍNIMO

Resumo por status:
- RUPTURA: {status_count.get('RUPTURA', 0)} itens
- CRÍTICO: {status_count.get('CRITICO', 0)} itens
- COMPRAR: {status_count.get('COMPRAR', 0)} itens
- NORMAL: {status_count.get('NORMAL', 0)} itens
- EXCESSO: {status_count.get('EXCESSO', 0)} itens

Itens em ruptura/crítico:
"""
            criticos = self.df_parametros[
                self.df_parametros['status'].isin(['RUPTURA', 'CRITICO'])
            ].head(10)

            for _, row in criticos.iterrows():
                contexto += f"- {row['item']}: saldo {row['saldo_atual']}, mínimo {row['estoque_minimo']}\n"

        prompt = f"""
{contexto}

Analise estes dados e forneça:
1. Avaliação da situação atual
2. Recomendações específicas de ação
3. Riscos identificados
4. Sugestões de otimização

Use português brasileiro e seja prático.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é um especialista em gestão de estoques e supply chain."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Erro: {e}"

    def exibir_dashboard(self):
        """Exibe dashboard de estoque mínimo"""
        if self.df_parametros is None:
            self.calcular_todos_itens()

        print("\n" + "=" * 80)
        print(" 📊 CALCULADOR DE ESTOQUE MÍNIMO - MARFIM IA")
        print("=" * 80)

        # Resumo por status
        status_count = self.df_parametros['status'].value_counts()

        print(f"""
RESUMO POR STATUS:
{'─' * 50}
🔴 RUPTURA:  {status_count.get('RUPTURA', 0):>4} itens (sem estoque)
🟠 CRÍTICO:  {status_count.get('CRITICO', 0):>4} itens (abaixo do mínimo)
🟡 COMPRAR:  {status_count.get('COMPRAR', 0):>4} itens (atingiu ponto de pedido)
🟢 NORMAL:   {status_count.get('NORMAL', 0):>4} itens (estoque adequado)
🔵 EXCESSO:  {status_count.get('EXCESSO', 0):>4} itens (acima do máximo)
""")

        # Tabela de itens críticos
        print("\n📋 ITENS QUE PRECISAM DE AÇÃO:")
        print("-" * 80)
        print(f"{'Item':<35} {'Saldo':>8} {'Mínimo':>8} {'Ponto Ped':>10} {'Status':>10}")
        print("-" * 80)

        acoes = self.df_parametros[
            self.df_parametros['status'].isin(['RUPTURA', 'CRITICO', 'COMPRAR'])
        ]

        emojis = {'RUPTURA': '🔴', 'CRITICO': '🟠', 'COMPRAR': '🟡'}

        for _, row in acoes.head(20).iterrows():
            emoji = emojis.get(row['status'], '⚪')
            print(f"{row['item'][:34]:<35} {row['saldo_atual']:>8.0f} {row['estoque_minimo']:>8.0f} {row['ponto_pedido']:>10.0f} {emoji} {row['status']:>8}")

        if len(acoes) > 20:
            print(f"\n... e mais {len(acoes) - 20} itens")

    def exportar_parametros(self, arquivo=None):
        """Exporta parâmetros para Excel"""
        if self.df_parametros is None:
            self.calcular_todos_itens()

        if not arquivo:
            arquivo = f"parametros_estoque_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
            self.df_parametros.to_excel(writer, sheet_name='Todos os Itens', index=False)

            # Abas por status
            for status in ['RUPTURA', 'CRITICO', 'COMPRAR']:
                df_status = self.df_parametros[self.df_parametros['status'] == status]
                if not df_status.empty:
                    df_status.to_excel(writer, sheet_name=status, index=False)

        print(f"✅ Exportado: {arquivo}")
        return arquivo


def executar_calculador():
    """Execução via CLI"""
    calc = CalculadorEstoqueMinimo()
    calc.carregar_dados()

    print("\n📊 Opções:")
    print("1. Calcular parâmetros de todos os itens")
    print("2. Calcular parâmetros de um item específico")
    print("0. Sair")

    opcao = input("\nEscolha: ").strip()

    if opcao == "1":
        nivel = input("Nível de serviço (90/95/97/99) [95]: ").strip() or "95"
        nivel = int(nivel) / 100

        calc.calcular_todos_itens(nivel)
        calc.exibir_dashboard()

        if input("\nGerar análise IA? (s/n): ").lower() == 's':
            print("\n🤖 Analisando...")
            print("\n" + calc.gerar_relatorio_ia())

        if input("\nExportar para Excel? (s/n): ").lower() == 's':
            calc.exportar_parametros()

    elif opcao == "2":
        item = input("Nome do item: ").strip().upper()
        params = calc.calcular_parametros_item(item)

        if params:
            print(f"\n📊 PARÂMETROS: {item}")
            print("-" * 50)
            for k, v in params.items():
                print(f"  {k}: {v}")

            if input("\nGerar análise IA? (s/n): ").lower() == 's':
                print("\n🤖 Analisando...")
                print("\n" + calc.gerar_relatorio_ia(item))
        else:
            print("❌ Item não encontrado")


if __name__ == "__main__":
    executar_calculador()
