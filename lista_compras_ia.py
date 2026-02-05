"""
Gerador Inteligente de Lista de Compras
Cria sugestões de compra baseadas em previsão de demanda e níveis de estoque
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, MARGEM_SEGURANCA, COBERTURA_IDEAL_DIAS,
    converter_para_numero, formatar_numero_br
)

class GeradorListaCompras:
    """Gera listas de compras inteligentes baseadas em análise preditiva"""

    def __init__(self):
        self.df_estoque = None
        self.df_historico = None
        self.lista_compras = []
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_dados(self):
        """Carrega dados de estoque e histórico"""
        print("📡 Carregando dados...")
        ss = self.conectar()

        # Índice atual
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")
        dados_indice = sheet_indice.get_all_values()
        self.df_estoque = pd.DataFrame(dados_indice[1:], columns=dados_indice[0])

        if 'Saldo Atual' in self.df_estoque.columns:
            self.df_estoque['Saldo'] = self.df_estoque['Saldo Atual'].apply(converter_para_numero)

        # Histórico
        sheet_hist = ss.worksheet("ESTOQUE")
        dados_hist = sheet_hist.get_all_values()
        self.df_historico = pd.DataFrame(dados_hist[1:], columns=dados_hist[0])

        for col in ['Entrada', 'Saída', 'Saldo']:
            self.df_historico[col] = self.df_historico[col].apply(converter_para_numero)

        self.df_historico['Data'] = pd.to_datetime(
            self.df_historico['Data'], format='%d/%m/%Y', errors='coerce'
        )

        # Calcular métricas
        self._calcular_metricas()

        print(f"✅ {len(self.df_estoque)} itens carregados")
        return self.df_estoque

    def _calcular_metricas(self):
        """Calcula métricas de consumo para cada item"""
        hoje = datetime.now()

        # Consumo por período
        for dias, nome in [(30, '30d'), (60, '60d'), (90, '90d')]:
            data_inicio = hoje - timedelta(days=dias)
            consumo = self.df_historico[
                self.df_historico['Data'] >= data_inicio
            ].groupby('Item')['Saída'].sum()

            self.df_estoque[f'Consumo_{nome}'] = self.df_estoque['Item'].map(consumo).fillna(0)
            self.df_estoque[f'Media_Diaria_{nome}'] = self.df_estoque[f'Consumo_{nome}'] / dias

        # Média ponderada (mais peso para dados recentes)
        self.df_estoque['Media_Diaria'] = (
            self.df_estoque['Media_Diaria_30d'] * 0.5 +
            self.df_estoque['Media_Diaria_60d'] * 0.3 +
            self.df_estoque['Media_Diaria_90d'] * 0.2
        )

        # Dias de cobertura
        self.df_estoque['Dias_Cobertura'] = self.df_estoque.apply(
            lambda r: r['Saldo'] / r['Media_Diaria'] if r['Media_Diaria'] > 0 else 999,
            axis=1
        )

        # Última entrada
        ultima_entrada = self.df_historico[
            self.df_historico['Entrada'] > 0
        ].groupby('Item')['Data'].max()
        self.df_estoque['Ultima_Entrada'] = self.df_estoque['Item'].map(ultima_entrada)

        # Quantidade média de compra
        media_compra = self.df_historico[
            self.df_historico['Entrada'] > 0
        ].groupby('Item')['Entrada'].mean()
        self.df_estoque['Media_Compra'] = self.df_estoque['Item'].map(media_compra).fillna(0)

    def calcular_quantidade_compra(self, row, dias_cobertura_alvo=None):
        """Calcula quantidade ideal de compra para um item"""
        if dias_cobertura_alvo is None:
            dias_cobertura_alvo = COBERTURA_IDEAL_DIAS

        saldo = row.get('Saldo', 0)
        media_diaria = row.get('Media_Diaria', 0)

        if media_diaria <= 0:
            return 0

        # Quantidade para atingir cobertura alvo + margem de segurança
        consumo_periodo = media_diaria * dias_cobertura_alvo * MARGEM_SEGURANCA
        qtd_necessaria = max(0, consumo_periodo - saldo)

        # Arredondar para múltiplo da média de compra (lotes)
        media_compra = row.get('Media_Compra', 0)
        if media_compra > 0:
            lotes = max(1, round(qtd_necessaria / media_compra))
            qtd_necessaria = lotes * media_compra

        return round(qtd_necessaria, 0)

    def gerar_lista_compras(self, dias_cobertura_alvo=None, limite_dias_cobertura=30):
        """Gera lista de compras baseada em análise preditiva"""
        if self.df_estoque is None:
            self.carregar_dados()

        if dias_cobertura_alvo is None:
            dias_cobertura_alvo = COBERTURA_IDEAL_DIAS

        print(f"\n📋 Gerando lista de compras (cobertura alvo: {dias_cobertura_alvo} dias)...")

        # Filtrar itens que precisam de reposição
        df_compras = self.df_estoque[
            (self.df_estoque['Dias_Cobertura'] < limite_dias_cobertura) &
            (self.df_estoque['Media_Diaria'] > 0)
        ].copy()

        if df_compras.empty:
            print("✅ Nenhum item precisa de reposição!")
            return []

        self.lista_compras = []

        for _, row in df_compras.iterrows():
            qtd_compra = self.calcular_quantidade_compra(row, dias_cobertura_alvo)

            if qtd_compra <= 0:
                continue

            # Classificar urgência
            dias_cob = row['Dias_Cobertura']
            if dias_cob < 0 or row['Saldo'] < 0:
                urgencia = "CRITICO"
                prioridade = 1
            elif dias_cob <= 7:
                urgencia = "URGENTE"
                prioridade = 2
            elif dias_cob <= 15:
                urgencia = "ALTO"
                prioridade = 3
            else:
                urgencia = "MEDIO"
                prioridade = 4

            item_compra = {
                'item': row['Item'],
                'grupo': row.get('Grupo', 'N/A'),
                'saldo_atual': row['Saldo'],
                'media_diaria': row['Media_Diaria'],
                'dias_cobertura': dias_cob,
                'qtd_sugerida': qtd_compra,
                'urgencia': urgencia,
                'prioridade': prioridade,
                'consumo_30d': row.get('Consumo_30d', 0),
                'ultima_entrada': row.get('Ultima_Entrada', None),
                'nova_cobertura': (row['Saldo'] + qtd_compra) / row['Media_Diaria'] if row['Media_Diaria'] > 0 else 999
            }

            self.lista_compras.append(item_compra)

        # Ordenar por prioridade e consumo
        self.lista_compras.sort(key=lambda x: (x['prioridade'], -x['consumo_30d']))

        print(f"✅ {len(self.lista_compras)} itens na lista de compras")
        return self.lista_compras

    def agrupar_por_categoria(self):
        """Agrupa lista de compras por categoria/grupo"""
        if not self.lista_compras:
            self.gerar_lista_compras()

        grupos = {}
        for item in self.lista_compras:
            grupo = item.get('grupo', 'SEM GRUPO')
            if grupo not in grupos:
                grupos[grupo] = []
            grupos[grupo].append(item)

        return grupos

    def gerar_resumo_ia(self):
        """Gera resumo executivo da lista de compras usando IA"""
        if not self.lista_compras:
            self.gerar_lista_compras()

        if not self.client_groq:
            return "IA não disponível"

        # Estatísticas
        total_itens = len(self.lista_compras)
        criticos = len([i for i in self.lista_compras if i['urgencia'] == 'CRITICO'])
        urgentes = len([i for i in self.lista_compras if i['urgencia'] == 'URGENTE'])
        total_unidades = sum(i['qtd_sugerida'] for i in self.lista_compras)

        contexto = f"""
LISTA DE COMPRAS GERADA - {datetime.now().strftime('%d/%m/%Y')}

RESUMO:
- Total de itens: {total_itens}
- Itens CRÍTICOS: {criticos}
- Itens URGENTES: {urgentes}
- Total de unidades: {total_unidades:,.0f}

TOP 15 ITENS PRIORITÁRIOS:
"""
        for i in self.lista_compras[:15]:
            contexto += f"- {i['item']}: comprar {i['qtd_sugerida']:.0f} un ({i['urgencia']}) - cobertura atual: {i['dias_cobertura']:.0f} dias\n"

        prompt = f"""
{contexto}

Como gestor de compras, analise esta lista e forneça:
1. Visão geral da situação - está crítica?
2. Sugestão de priorização para os próximos 7 dias
3. Itens que podem ser agrupados na mesma compra (mesmo fornecedor/categoria)
4. Recomendação de urgência geral (escala 1-10)
5. Dicas para negociação considerando os volumes

Seja objetivo e use português brasileiro.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é um gerente de compras experiente em indústria têxtil."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Erro ao consultar IA: {e}"

    def exibir_lista(self):
        """Exibe lista de compras formatada"""
        if not self.lista_compras:
            self.gerar_lista_compras()

        print("\n" + "=" * 80)
        print(" 🛒 LISTA DE COMPRAS INTELIGENTE - MARFIM IA")
        print(" " + datetime.now().strftime('%d/%m/%Y %H:%M'))
        print("=" * 80)

        if not self.lista_compras:
            print("\n✅ Nenhuma compra necessária no momento!")
            return

        # Resumo
        criticos = [i for i in self.lista_compras if i['urgencia'] == 'CRITICO']
        urgentes = [i for i in self.lista_compras if i['urgencia'] == 'URGENTE']
        altos = [i for i in self.lista_compras if i['urgencia'] == 'ALTO']

        print(f"""
📊 RESUMO
{'─' * 60}
🔴 CRÍTICOS:  {len(criticos):>4} itens (comprar HOJE)
🟠 URGENTES:  {len(urgentes):>4} itens (até 3 dias)
🟡 ALTO:      {len(altos):>4} itens (até 7 dias)
{'─' * 60}
   TOTAL:     {len(self.lista_compras):>4} itens
   UNIDADES:  {sum(i['qtd_sugerida'] for i in self.lista_compras):>10,.0f}
""")

        # Lista detalhada
        emojis = {'CRITICO': '🔴', 'URGENTE': '🟠', 'ALTO': '🟡', 'MEDIO': '🟢'}

        print(f"\n{'Item':<40} {'Saldo':>8} {'Comprar':>10} {'Cobertura':>10} {'Prioridade':>10}")
        print("-" * 80)

        for item in self.lista_compras[:30]:
            emoji = emojis.get(item['urgencia'], '⚪')
            cob = f"{item['dias_cobertura']:.0f}d → {item['nova_cobertura']:.0f}d"
            print(f"{item['item'][:39]:<40} {item['saldo_atual']:>8.0f} {item['qtd_sugerida']:>10.0f} {cob:>10} {emoji} {item['urgencia']:>8}")

        if len(self.lista_compras) > 30:
            print(f"\n... e mais {len(self.lista_compras) - 30} itens")

    def exportar_excel(self, arquivo=None):
        """Exporta lista de compras para Excel"""
        if not self.lista_compras:
            self.gerar_lista_compras()

        if not arquivo:
            arquivo = f"lista_compras_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        df = pd.DataFrame(self.lista_compras)

        # Reordenar e renomear colunas
        colunas = {
            'item': 'Item',
            'grupo': 'Grupo',
            'urgencia': 'Urgência',
            'saldo_atual': 'Saldo Atual',
            'qtd_sugerida': 'Qtd Sugerida',
            'media_diaria': 'Média Diária',
            'dias_cobertura': 'Cobertura Atual (dias)',
            'nova_cobertura': 'Nova Cobertura (dias)',
            'consumo_30d': 'Consumo 30d'
        }

        df = df.rename(columns=colunas)
        df = df[[c for c in colunas.values() if c in df.columns]]

        with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Lista Compras', index=False)

            # Aba por urgência
            for urgencia in ['CRITICO', 'URGENTE', 'ALTO']:
                df_urg = df[df['Urgência'] == urgencia]
                if not df_urg.empty:
                    df_urg.to_excel(writer, sheet_name=urgencia, index=False)

        print(f"✅ Lista exportada: {arquivo}")
        return arquivo


def executar_gerador():
    """Execução via CLI"""
    gerador = GeradorListaCompras()
    gerador.carregar_dados()

    print("\n📊 Opções:")
    print("1. Gerar lista de compras (30 dias cobertura)")
    print("2. Gerar lista de compras (45 dias cobertura)")
    print("3. Gerar lista de compras (60 dias cobertura)")
    print("0. Sair")

    opcao = input("\nEscolha: ").strip()

    dias = {
        "1": 30,
        "2": 45,
        "3": 60
    }.get(opcao)

    if dias:
        gerador.gerar_lista_compras(dias_cobertura_alvo=dias)
        gerador.exibir_lista()

        if input("\nGerar análise IA? (s/n): ").lower() == 's':
            print("\n🤖 Gerando análise...")
            print("\n" + "=" * 60)
            print(gerador.gerar_resumo_ia())

        if input("\nExportar para Excel? (s/n): ").lower() == 's':
            gerador.exportar_excel()


if __name__ == "__main__":
    executar_gerador()
