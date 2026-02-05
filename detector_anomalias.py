"""
Detector de Anomalias de Consumo
Identifica padrões atípicos no consumo de materiais
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

class DetectorAnomalias:
    """Detecta anomalias no padrão de consumo usando estatísticas e IA"""

    def __init__(self):
        self.df_historico = None
        self.anomalias = []
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_historico(self):
        """Carrega histórico de movimentações"""
        print("📡 Carregando histórico...")
        ss = self.conectar()
        sheet = ss.worksheet("ESTOQUE")
        dados = sheet.get_all_values()

        self.df_historico = pd.DataFrame(dados[1:], columns=dados[0])

        # Converter colunas
        for col in ['Entrada', 'Saída', 'Saldo']:
            self.df_historico[col] = self.df_historico[col].apply(converter_para_numero)

        self.df_historico['Data'] = pd.to_datetime(
            self.df_historico['Data'], format='%d/%m/%Y', errors='coerce'
        )

        print(f"✅ {len(self.df_historico)} movimentações carregadas")
        return self.df_historico

    def calcular_zscore(self, valores):
        """Calcula Z-Score para detecção de outliers"""
        if len(valores) < 3:
            return [0] * len(valores)
        media = np.mean(valores)
        desvio = np.std(valores)
        if desvio == 0:
            return [0] * len(valores)
        return [(v - media) / desvio for v in valores]

    def detectar_consumo_atipico(self, item_nome, limiar_zscore=2.5):
        """Detecta consumos atípicos de um item específico"""
        df_item = self.df_historico[
            (self.df_historico['Item'].str.upper() == item_nome.upper()) &
            (self.df_historico['Saída'] > 0)
        ].copy()

        if len(df_item) < 5:
            return []

        saidas = df_item['Saída'].values
        zscores = self.calcular_zscore(saidas)
        df_item['zscore'] = zscores

        anomalias = []
        for _, row in df_item[abs(df_item['zscore']) > limiar_zscore].iterrows():
            tipo = "CONSUMO_ALTO" if row['zscore'] > 0 else "CONSUMO_BAIXO"
            anomalias.append({
                'item': item_nome,
                'tipo': tipo,
                'data': row['Data'],
                'valor': row['Saída'],
                'zscore': row['zscore'],
                'media_normal': np.mean(saidas),
                'desvio': abs(row['Saída'] - np.mean(saidas)),
                'obs': row.get('Obs', ''),
                'nf': row.get('NF', '')
            })

        return anomalias

    def detectar_picos_entrada(self, item_nome, limiar_zscore=2.5):
        """Detecta entradas atípicas (compras muito grandes ou muito pequenas)"""
        df_item = self.df_historico[
            (self.df_historico['Item'].str.upper() == item_nome.upper()) &
            (self.df_historico['Entrada'] > 0)
        ].copy()

        if len(df_item) < 3:
            return []

        entradas = df_item['Entrada'].values
        zscores = self.calcular_zscore(entradas)
        df_item['zscore'] = zscores

        anomalias = []
        for _, row in df_item[abs(df_item['zscore']) > limiar_zscore].iterrows():
            tipo = "ENTRADA_ALTA" if row['zscore'] > 0 else "ENTRADA_BAIXA"
            anomalias.append({
                'item': item_nome,
                'tipo': tipo,
                'data': row['Data'],
                'valor': row['Entrada'],
                'zscore': row['zscore'],
                'media_normal': np.mean(entradas),
                'nf': row.get('NF', '')
            })

        return anomalias

    def detectar_padroes_suspeitos(self, item_nome):
        """Detecta padrões suspeitos como saídas em sequência ou valores repetidos"""
        df_item = self.df_historico[
            self.df_historico['Item'].str.upper() == item_nome.upper()
        ].sort_values('Data').copy()

        if len(df_item) < 5:
            return []

        anomalias = []

        # Detectar valores repetidos exatamente iguais (possível erro de lançamento)
        saidas = df_item[df_item['Saída'] > 0]['Saída']
        valores_repetidos = saidas.value_counts()
        for valor, count in valores_repetidos.items():
            if count >= 5 and valor > 0:  # Mesmo valor 5+ vezes
                anomalias.append({
                    'item': item_nome,
                    'tipo': 'VALOR_REPETIDO',
                    'data': datetime.now(),
                    'valor': valor,
                    'ocorrencias': count,
                    'descricao': f"Saída de {valor:.0f} un ocorreu {count}x - possível padrão ou erro"
                })

        # Detectar múltiplas saídas no mesmo dia
        saidas_por_dia = df_item[df_item['Saída'] > 0].groupby(df_item['Data'].dt.date).size()
        dias_multiplos = saidas_por_dia[saidas_por_dia >= 3]
        for dia, count in dias_multiplos.items():
            anomalias.append({
                'item': item_nome,
                'tipo': 'MULTIPLAS_SAIDAS_DIA',
                'data': pd.Timestamp(dia),
                'valor': count,
                'descricao': f"{count} saídas no mesmo dia - verificar"
            })

        # Detectar saldo negativo
        saldos_negativos = df_item[df_item['Saldo'] < 0]
        if not saldos_negativos.empty:
            for _, row in saldos_negativos.iterrows():
                anomalias.append({
                    'item': item_nome,
                    'tipo': 'SALDO_NEGATIVO',
                    'data': row['Data'],
                    'valor': row['Saldo'],
                    'descricao': f"Saldo ficou negativo: {row['Saldo']:.0f}"
                })

        return anomalias

    def detectar_sazonalidade_quebrada(self, item_nome):
        """Detecta quebra no padrão sazonal de consumo"""
        df_item = self.df_historico[
            (self.df_historico['Item'].str.upper() == item_nome.upper()) &
            (self.df_historico['Saída'] > 0)
        ].copy()

        if len(df_item) < 30:  # Precisa de histórico
            return []

        df_item['mes'] = df_item['Data'].dt.month
        df_item['ano'] = df_item['Data'].dt.year

        # Consumo mensal
        consumo_mensal = df_item.groupby(['ano', 'mes'])['Saída'].sum().reset_index()

        if len(consumo_mensal) < 6:
            return []

        # Calcular média histórica por mês
        media_por_mes = consumo_mensal.groupby('mes')['Saída'].mean()

        anomalias = []
        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        # Verificar últimos 3 meses
        for i in range(3):
            mes = mes_atual - i
            ano = ano_atual
            if mes <= 0:
                mes += 12
                ano -= 1

            consumo_mes = consumo_mensal[
                (consumo_mensal['ano'] == ano) &
                (consumo_mensal['mes'] == mes)
            ]['Saída'].sum()

            media_historica = media_por_mes.get(mes, 0)

            if media_historica > 0:
                variacao = (consumo_mes - media_historica) / media_historica

                if abs(variacao) > 0.5:  # Variação > 50%
                    tipo = "CONSUMO_ACIMA_SAZONAL" if variacao > 0 else "CONSUMO_ABAIXO_SAZONAL"
                    anomalias.append({
                        'item': item_nome,
                        'tipo': tipo,
                        'data': datetime(ano, mes, 1),
                        'valor': consumo_mes,
                        'media_historica': media_historica,
                        'variacao_percentual': variacao * 100,
                        'descricao': f"Consumo {variacao*100:+.0f}% vs média histórica do mês"
                    })

        return anomalias

    def analisar_todos_itens(self, limite=50):
        """Analisa todos os itens e retorna anomalias encontradas"""
        if self.df_historico is None:
            self.carregar_historico()

        print("\n🔍 Analisando anomalias em todos os itens...")

        itens_unicos = self.df_historico['Item'].unique()
        todas_anomalias = []

        for item in itens_unicos[:limite]:
            # Detectar diferentes tipos de anomalias
            anomalias_consumo = self.detectar_consumo_atipico(item)
            anomalias_entrada = self.detectar_picos_entrada(item)
            anomalias_padrao = self.detectar_padroes_suspeitos(item)
            anomalias_sazonal = self.detectar_sazonalidade_quebrada(item)

            todas_anomalias.extend(anomalias_consumo)
            todas_anomalias.extend(anomalias_entrada)
            todas_anomalias.extend(anomalias_padrao)
            todas_anomalias.extend(anomalias_sazonal)

        # Ordenar por data (mais recentes primeiro)
        todas_anomalias.sort(key=lambda x: x.get('data', datetime.min) if pd.notna(x.get('data')) else datetime.min, reverse=True)

        self.anomalias = todas_anomalias
        return todas_anomalias

    def gerar_relatorio_anomalias(self, item_nome=None):
        """Gera relatório de anomalias com análise IA"""
        if item_nome:
            anomalias = (
                self.detectar_consumo_atipico(item_nome) +
                self.detectar_picos_entrada(item_nome) +
                self.detectar_padroes_suspeitos(item_nome) +
                self.detectar_sazonalidade_quebrada(item_nome)
            )
        else:
            if not self.anomalias:
                self.analisar_todos_itens()
            anomalias = self.anomalias

        if not anomalias:
            return "✅ Nenhuma anomalia detectada!"

        if not self.client_groq:
            return self._formatar_anomalias_texto(anomalias)

        # Construir contexto para IA
        contexto = f"ANOMALIAS DETECTADAS ({len(anomalias)} total):\n\n"

        tipos_count = {}
        for a in anomalias:
            tipo = a['tipo']
            tipos_count[tipo] = tipos_count.get(tipo, 0) + 1

        contexto += "RESUMO POR TIPO:\n"
        for tipo, count in tipos_count.items():
            contexto += f"- {tipo}: {count} ocorrências\n"

        contexto += "\nDETALHES (primeiras 15):\n"
        for a in anomalias[:15]:
            data_str = a['data'].strftime('%d/%m/%Y') if pd.notna(a.get('data')) else 'N/A'
            contexto += f"- [{a['tipo']}] {a['item']}: {a.get('valor', 'N/A')} em {data_str}\n"

        prompt = f"""
{contexto}

Analise estas anomalias de estoque e forneça:
1. Quais anomalias são mais críticas e precisam de investigação imediata
2. Possíveis causas para os padrões detectados
3. Recomendações de ação para cada tipo de anomalia
4. Se há indícios de problemas operacionais (erros de lançamento, desvios, etc.)

Use português brasileiro e seja objetivo.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é um auditor de estoque especializado em detectar fraudes e erros operacionais."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Erro IA: {e}\n\n" + self._formatar_anomalias_texto(anomalias)

    def _formatar_anomalias_texto(self, anomalias):
        """Formata anomalias em texto"""
        texto = f"\n{'='*60}\n ANOMALIAS DETECTADAS: {len(anomalias)}\n{'='*60}\n"

        tipos = {}
        for a in anomalias:
            tipo = a['tipo']
            if tipo not in tipos:
                tipos[tipo] = []
            tipos[tipo].append(a)

        for tipo, lista in tipos.items():
            texto += f"\n📌 {tipo} ({len(lista)} ocorrências)\n"
            texto += "-" * 50 + "\n"
            for a in lista[:5]:
                data_str = a.get('data', 'N/A')
                if pd.notna(data_str) and hasattr(data_str, 'strftime'):
                    data_str = data_str.strftime('%d/%m/%Y')
                texto += f"  • {a['item']}: {a.get('valor', 'N/A')} ({data_str})\n"
            if len(lista) > 5:
                texto += f"  ... e mais {len(lista)-5}\n"

        return texto

    def exibir_dashboard(self):
        """Exibe dashboard de anomalias"""
        if not self.anomalias:
            self.analisar_todos_itens()

        print("\n" + "=" * 70)
        print(" 🔍 DETECTOR DE ANOMALIAS - MARFIM IA")
        print("=" * 70)

        if not self.anomalias:
            print("\n✅ Nenhuma anomalia significativa detectada!")
            return

        # Agrupar por tipo
        tipos = {}
        for a in self.anomalias:
            tipo = a['tipo']
            if tipo not in tipos:
                tipos[tipo] = []
            tipos[tipo].append(a)

        print(f"\n📊 RESUMO: {len(self.anomalias)} anomalias em {len(tipos)} categorias\n")

        emojis = {
            'CONSUMO_ALTO': '📈',
            'CONSUMO_BAIXO': '📉',
            'ENTRADA_ALTA': '📦',
            'ENTRADA_BAIXA': '📭',
            'SALDO_NEGATIVO': '🔴',
            'VALOR_REPETIDO': '🔁',
            'MULTIPLAS_SAIDAS_DIA': '⚡',
            'CONSUMO_ACIMA_SAZONAL': '🌡️',
            'CONSUMO_ABAIXO_SAZONAL': '❄️'
        }

        for tipo, lista in sorted(tipos.items(), key=lambda x: len(x[1]), reverse=True):
            emoji = emojis.get(tipo, '⚠️')
            print(f"{emoji} {tipo}: {len(lista)} ocorrências")

        # Mostrar anomalias críticas
        criticas = [a for a in self.anomalias if a['tipo'] in ['SALDO_NEGATIVO', 'CONSUMO_ALTO']]
        if criticas:
            print(f"\n🚨 ANOMALIAS CRÍTICAS ({len(criticas)}):")
            print("-" * 60)
            for a in criticas[:10]:
                data_str = a.get('data', 'N/A')
                if pd.notna(data_str) and hasattr(data_str, 'strftime'):
                    data_str = data_str.strftime('%d/%m/%Y')
                print(f"  {a['tipo']}: {a['item'][:35]} | {a.get('valor', 'N/A')} | {data_str}")


def executar_detector():
    """Execução via CLI"""
    detector = DetectorAnomalias()
    detector.carregar_historico()

    print("\n📊 Opções:")
    print("1. Analisar todos os itens")
    print("2. Analisar item específico")
    print("0. Sair")

    opcao = input("\nEscolha: ").strip()

    if opcao == "1":
        detector.analisar_todos_itens()
        detector.exibir_dashboard()

        if input("\nGerar análise IA? (s/n): ").lower() == 's':
            print("\n🤖 Analisando com IA...")
            print(detector.gerar_relatorio_anomalias())

    elif opcao == "2":
        item = input("Nome do item: ").strip().upper()
        print(f"\n🔍 Analisando {item}...")
        relatorio = detector.gerar_relatorio_anomalias(item)
        print(relatorio)


if __name__ == "__main__":
    executar_detector()
