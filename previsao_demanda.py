"""
Módulo de Previsão de Demanda com IA
Prevê consumo futuro baseado em histórico e sazonalidade
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, TEMPERATURA_ANALISE, DIAS_PREVISAO,
    converter_para_numero, formatar_numero_br
)

class PrevisaoDemanda:
    """Motor de previsão de demanda inteligente"""

    def __init__(self):
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None
        self.df_historico = None
        self.df_previsoes = None

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

        # Converter colunas numéricas
        for col in ['Entrada', 'Saída', 'Saldo']:
            self.df_historico[col] = self.df_historico[col].apply(converter_para_numero)

        # Converter datas
        self.df_historico['_data'] = pd.to_datetime(
            self.df_historico['Data'],
            format='%d/%m/%Y',
            errors='coerce'
        )

        print(f"✅ {len(self.df_historico)} movimentações carregadas")
        return self.df_historico

    def calcular_estatisticas_item(self, item_nome):
        """Calcula estatísticas de consumo de um item"""
        df_item = self.df_historico[
            self.df_historico['Item'].str.upper() == item_nome.upper()
        ].copy()

        if df_item.empty:
            return None

        # Ordenar por data
        df_item = df_item.sort_values('_data')

        # Obter unidade de medida do último registro
        unidade = df_item['Unidade'].iloc[-1] if 'Unidade' in df_item.columns else 'UN'
        if not unidade or str(unidade).strip() == '':
            unidade = 'UN'

        # Calcular métricas
        saidas = df_item[df_item['Saída'] > 0]['Saída']

        stats = {
            'item': item_nome,
            'unidade': unidade,
            'saldo_atual': df_item['Saldo'].iloc[-1],
            'total_saidas': saidas.sum(),
            'qtd_movimentacoes': len(saidas),
            'media_saida': saidas.mean() if len(saidas) > 0 else 0,
            'mediana_saida': saidas.median() if len(saidas) > 0 else 0,
            'desvio_padrao': saidas.std() if len(saidas) > 1 else 0,
            'max_saida': saidas.max() if len(saidas) > 0 else 0,
            'min_saida': saidas.min() if len(saidas) > 0 else 0,
            'primeira_mov': df_item['_data'].min(),
            'ultima_mov': df_item['_data'].max(),
        }

        # Calcular frequência de consumo (dias entre saídas)
        datas_saida = df_item[df_item['Saída'] > 0]['_data']
        if len(datas_saida) > 1:
            intervalos = datas_saida.diff().dropna().dt.days
            stats['frequencia_dias'] = intervalos.mean()
        else:
            stats['frequencia_dias'] = 30  # Default: mensal

        # Consumo por período
        hoje = datetime.now()
        for dias in [30, 60, 90]:
            data_inicio = hoje - timedelta(days=dias)
            consumo = df_item[
                (df_item['_data'] >= data_inicio) &
                (df_item['Saída'] > 0)
            ]['Saída'].sum()
            stats[f'consumo_{dias}d'] = consumo
            stats[f'media_diaria_{dias}d'] = consumo / dias

        return stats

    def detectar_sazonalidade(self, item_nome):
        """Detecta padrões sazonais no consumo"""
        df_item = self.df_historico[
            self.df_historico['Item'].str.upper() == item_nome.upper()
        ].copy()

        if df_item.empty or len(df_item) < 12:
            return None

        df_item['mes'] = df_item['_data'].dt.month
        df_item['dia_semana'] = df_item['_data'].dt.dayofweek

        # Consumo por mês
        consumo_mensal = df_item.groupby('mes')['Saída'].sum()

        # Identificar meses de pico
        media_mensal = consumo_mensal.mean()
        meses_pico = consumo_mensal[consumo_mensal > media_mensal * 1.3].index.tolist()
        meses_baixa = consumo_mensal[consumo_mensal < media_mensal * 0.7].index.tolist()

        nomes_meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }

        return {
            'consumo_por_mes': consumo_mensal.to_dict(),
            'meses_pico': [nomes_meses.get(m, m) for m in meses_pico],
            'meses_baixa': [nomes_meses.get(m, m) for m in meses_baixa],
            'variacao_sazonal': consumo_mensal.std() / consumo_mensal.mean() if consumo_mensal.mean() > 0 else 0
        }

    def prever_consumo(self, item_nome, dias_futuro=30):
        """Prevê consumo futuro usando média móvel ponderada"""
        stats = self.calcular_estatisticas_item(item_nome)
        if not stats:
            return None

        # Pesos: últimos 30 dias pesam mais
        peso_30d = 0.5
        peso_60d = 0.3
        peso_90d = 0.2

        media_ponderada = (
            stats['media_diaria_30d'] * peso_30d +
            stats['media_diaria_60d'] * peso_60d +
            stats['media_diaria_90d'] * peso_90d
        )

        # Ajuste por sazonalidade
        sazonalidade = self.detectar_sazonalidade(item_nome)
        fator_sazonal = 1.0
        if sazonalidade:
            mes_atual = datetime.now().month
            consumo_mes_atual = sazonalidade['consumo_por_mes'].get(mes_atual, 0)
            media_geral = sum(sazonalidade['consumo_por_mes'].values()) / 12
            if media_geral > 0:
                fator_sazonal = consumo_mes_atual / media_geral
                fator_sazonal = max(0.5, min(2.0, fator_sazonal))  # Limitar entre 0.5x e 2x

        consumo_previsto = media_ponderada * dias_futuro * fator_sazonal

        # Calcular intervalo de confiança
        margem_erro = stats['desvio_padrao'] * 1.96 / np.sqrt(stats['qtd_movimentacoes']) if stats['qtd_movimentacoes'] > 0 else stats['media_saida'] * 0.2

        previsao = {
            'item': item_nome,
            'dias_previsao': dias_futuro,
            'consumo_previsto': round(consumo_previsto, 2),
            'consumo_minimo': round(max(0, consumo_previsto - margem_erro * dias_futuro), 2),
            'consumo_maximo': round(consumo_previsto + margem_erro * dias_futuro, 2),
            'media_diaria': round(media_ponderada * fator_sazonal, 2),
            'saldo_atual': stats['saldo_atual'],
            'saldo_previsto': round(stats['saldo_atual'] - consumo_previsto, 2),
            'dias_cobertura': round(stats['saldo_atual'] / (media_ponderada * fator_sazonal), 1) if media_ponderada > 0 else 999,
            'fator_sazonal': round(fator_sazonal, 2),
            'confianca': 'alta' if stats['qtd_movimentacoes'] > 20 else ('media' if stats['qtd_movimentacoes'] > 5 else 'baixa')
        }

        # Alerta de reposição
        if previsao['saldo_previsto'] < 0:
            previsao['alerta'] = 'CRITICO'
            previsao['recomendacao'] = f"Repor URGENTE! Estoque zerado em ~{previsao['dias_cobertura']:.0f} dias"
        elif previsao['dias_cobertura'] < 15:
            previsao['alerta'] = 'URGENTE'
            previsao['recomendacao'] = f"Programar compra em até 7 dias"
        elif previsao['dias_cobertura'] < 30:
            previsao['alerta'] = 'ATENCAO'
            previsao['recomendacao'] = f"Incluir na próxima lista de compras"
        else:
            previsao['alerta'] = 'NORMAL'
            previsao['recomendacao'] = f"Estoque adequado para {previsao['dias_cobertura']:.0f} dias"

        return previsao

    def prever_multiplos_periodos(self, item_nome):
        """Gera previsões para múltiplos períodos"""
        previsoes = []
        for dias in DIAS_PREVISAO:
            prev = self.prever_consumo(item_nome, dias)
            if prev:
                previsoes.append(prev)
        return previsoes

    def gerar_relatorio_ia(self, item_nome):
        """Gera análise detalhada usando IA"""
        stats = self.calcular_estatisticas_item(item_nome)
        previsoes = self.prever_multiplos_periodos(item_nome)
        sazonalidade = self.detectar_sazonalidade(item_nome)

        if not stats or not self.client_groq:
            return None

        # Construir contexto para IA
        unidade = stats.get('unidade', 'UN')
        contexto = f"""
ANÁLISE DE DEMANDA - {item_nome}

ESTATÍSTICAS ATUAIS:
- Unidade de medida: {unidade}
- Saldo atual: {stats['saldo_atual']} {unidade}
- Consumo últimos 30 dias: {stats['consumo_30d']:.0f} {unidade}
- Consumo últimos 60 dias: {stats['consumo_60d']:.0f} {unidade}
- Consumo últimos 90 dias: {stats['consumo_90d']:.0f} {unidade}
- Média por saída: {stats['media_saida']:.1f} {unidade}
- Frequência média: a cada {stats['frequencia_dias']:.0f} dias

PREVISÕES:
"""
        for p in previsoes:
            contexto += f"- {p['dias_previsao']} dias: {p['consumo_previsto']:.0f} {unidade} (saldo restante: {p['saldo_previsto']:.0f} {unidade})\n"

        if sazonalidade and sazonalidade['meses_pico']:
            contexto += f"\nSAZONALIDADE:\n- Meses de pico: {', '.join(sazonalidade['meses_pico'])}\n"

        prompt = f"""
{contexto}

Com base nestes dados, forneça:
1. Análise do padrão de consumo (crescente, estável ou decrescente)
2. Previsão de quando o estoque ficará crítico
3. Quantidade recomendada para compra
4. Melhor momento para fazer o pedido
5. Riscos identificados

Seja direto, técnico e use português do Brasil.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é um analista de supply chain especializado em previsão de demanda para indústria têxtil."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURA_ANALISE
            )
            return {
                'item': item_nome,
                'estatisticas': stats,
                'previsoes': previsoes,
                'sazonalidade': sazonalidade,
                'analise_ia': completion.choices[0].message.content
            }
        except Exception as e:
            return {
                'item': item_nome,
                'estatisticas': stats,
                'previsoes': previsoes,
                'sazonalidade': sazonalidade,
                'analise_ia': f"Erro ao consultar IA: {e}"
            }

    def prever_todos_criticos(self, limite_dias=30):
        """Prevê demanda de todos os itens com cobertura baixa"""
        if self.df_historico is None:
            self.carregar_historico()

        print(f"\n🔮 Analisando previsões para itens com cobertura < {limite_dias} dias...")

        itens_unicos = self.df_historico['Item'].unique()
        itens_criticos = []

        for item in itens_unicos:
            prev = self.prever_consumo(item, 30)
            if prev and prev['dias_cobertura'] < limite_dias:
                itens_criticos.append(prev)

        # Ordenar por urgência
        itens_criticos.sort(key=lambda x: x['dias_cobertura'])

        self.df_previsoes = pd.DataFrame(itens_criticos)
        return itens_criticos

def executar_previsao():
    """Função principal para execução via CLI"""
    motor = PrevisaoDemanda()
    motor.carregar_historico()

    print("\n" + "=" * 60)
    print(" MÓDULO DE PREVISÃO DE DEMANDA - MARFIM IA")
    print("=" * 60)

    while True:
        print("\n📊 Opções:")
        print("1. Prever demanda de um item específico")
        print("2. Listar todos os itens críticos")
        print("3. Análise completa com IA")
        print("0. Sair")

        opcao = input("\nEscolha: ").strip()

        if opcao == "1":
            item = input("Nome do item: ").strip().upper()
            previsoes = motor.prever_multiplos_periodos(item)
            if previsoes:
                # Obter unidade do item
                stats = motor.calcular_estatisticas_item(item)
                unidade = stats.get('unidade', 'UN') if stats else 'UN'
                print(f"\n📈 PREVISÃO DE DEMANDA: {item} (Unidade: {unidade})")
                print("-" * 50)
                for p in previsoes:
                    emoji = {"CRITICO": "🔴", "URGENTE": "🟠", "ATENCAO": "🟡", "NORMAL": "🟢"}.get(p['alerta'], "⚪")
                    print(f"\n{p['dias_previsao']} dias:")
                    print(f"  Consumo previsto: {p['consumo_previsto']:.0f} {unidade}")
                    print(f"  Saldo restante: {p['saldo_previsto']:.0f} {unidade}")
                    print(f"  {emoji} {p['recomendacao']}")
            else:
                print("❌ Item não encontrado")

        elif opcao == "2":
            criticos = motor.prever_todos_criticos()
            if criticos:
                print(f"\n🚨 {len(criticos)} ITENS CRÍTICOS:")
                print("-" * 60)
                for i, p in enumerate(criticos[:20], 1):
                    emoji = {"CRITICO": "🔴", "URGENTE": "🟠", "ATENCAO": "🟡"}.get(p['alerta'], "⚪")
                    print(f"{i:2}. {emoji} {p['item'][:30]:<30} | {p['dias_cobertura']:.0f} dias")
            else:
                print("✅ Nenhum item crítico!")

        elif opcao == "3":
            item = input("Nome do item para análise completa: ").strip().upper()
            resultado = motor.gerar_relatorio_ia(item)
            if resultado:
                print(f"\n{'='*60}")
                print(f"🤖 ANÁLISE IA: {item}")
                print(f"{'='*60}")
                print(resultado['analise_ia'])
            else:
                print("❌ Item não encontrado ou IA indisponível")

        elif opcao == "0":
            print("\n👋 Até logo!")
            break

if __name__ == "__main__":
    executar_previsao()
