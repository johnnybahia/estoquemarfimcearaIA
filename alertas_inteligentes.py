"""
Sistema de Alertas Inteligentes e Proativos
Monitora estoque e gera alertas automáticos com priorização
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, NIVEIS_ALERTA, converter_para_numero
)

class SistemaAlertas:
    """Sistema inteligente de alertas de estoque"""

    def __init__(self):
        self.alertas = []
        self.df_estoque = None
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_dados(self):
        """Carrega dados do estoque"""
        print("📡 Carregando dados...")
        ss = self.conectar()

        # Carregar índice
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")
        dados = sheet_indice.get_all_values()
        self.df_estoque = pd.DataFrame(dados[1:], columns=dados[0])

        # Converter saldo
        if 'Saldo Atual' in self.df_estoque.columns:
            self.df_estoque['Saldo'] = self.df_estoque['Saldo Atual'].apply(converter_para_numero)

        # Carregar histórico para calcular consumo
        sheet_hist = ss.worksheet("ESTOQUE")
        dados_hist = sheet_hist.get_all_values()
        df_hist = pd.DataFrame(dados_hist[1:], columns=dados_hist[0])

        # Calcular consumo médio dos últimos 30 dias
        df_hist['Saída'] = df_hist['Saída'].apply(converter_para_numero)
        df_hist['Data'] = pd.to_datetime(df_hist['Data'], format='%d/%m/%Y', errors='coerce')

        data_30_dias = datetime.now() - timedelta(days=30)
        consumo_30d = df_hist[df_hist['Data'] >= data_30_dias].groupby('Item')['Saída'].sum()

        self.df_estoque['Consumo_30d'] = self.df_estoque['Item'].map(consumo_30d).fillna(0)
        self.df_estoque['Media_Diaria'] = self.df_estoque['Consumo_30d'] / 30
        self.df_estoque['Dias_Cobertura'] = self.df_estoque.apply(
            lambda r: r['Saldo'] / r['Media_Diaria'] if r['Media_Diaria'] > 0 else 999, axis=1
        )

        print(f"✅ {len(self.df_estoque)} itens carregados")
        return self.df_estoque

    def classificar_nivel_alerta(self, dias_cobertura, saldo):
        """Classifica o nível de alerta baseado na cobertura"""
        if saldo < 0:
            return "CRITICO", "Saldo negativo - ruptura de estoque!"
        elif dias_cobertura <= 7:
            return "CRITICO", "Estoque para menos de 7 dias"
        elif dias_cobertura <= 15:
            return "URGENTE", "Estoque para menos de 15 dias"
        elif dias_cobertura <= 30:
            return "ATENCAO", "Estoque para menos de 30 dias"
        else:
            return "NORMAL", "Estoque adequado"

    def gerar_alertas(self):
        """Gera todos os alertas do sistema"""
        if self.df_estoque is None:
            self.carregar_dados()

        self.alertas = []

        for _, row in self.df_estoque.iterrows():
            item = row['Item']
            saldo = row.get('Saldo', 0)
            dias_cob = row.get('Dias_Cobertura', 999)
            consumo = row.get('Consumo_30d', 0)

            nivel, motivo = self.classificar_nivel_alerta(dias_cob, saldo)

            if nivel != "NORMAL":
                alerta = {
                    'item': item,
                    'nivel': nivel,
                    'motivo': motivo,
                    'saldo_atual': saldo,
                    'dias_cobertura': dias_cob,
                    'consumo_30d': consumo,
                    'media_diaria': row.get('Media_Diaria', 0),
                    'data_alerta': datetime.now(),
                    'prioridade': NIVEIS_ALERTA[nivel]['prioridade'],
                    'emoji': NIVEIS_ALERTA[nivel]['cor']
                }

                # Calcular quantidade sugerida para compra (30 dias de cobertura)
                if row.get('Media_Diaria', 0) > 0:
                    qtd_ideal = row['Media_Diaria'] * 45  # 45 dias de cobertura
                    alerta['qtd_sugerida'] = max(0, qtd_ideal - saldo)
                else:
                    alerta['qtd_sugerida'] = 0

                self.alertas.append(alerta)

        # Ordenar por prioridade
        self.alertas.sort(key=lambda x: (x['prioridade'], -x['consumo_30d']))

        return self.alertas

    def alertas_por_nivel(self):
        """Retorna alertas agrupados por nível"""
        if not self.alertas:
            self.gerar_alertas()

        agrupados = {
            'CRITICO': [],
            'URGENTE': [],
            'ATENCAO': []
        }

        for alerta in self.alertas:
            if alerta['nivel'] in agrupados:
                agrupados[alerta['nivel']].append(alerta)

        return agrupados

    def gerar_resumo_ia(self):
        """Gera resumo executivo dos alertas usando IA"""
        if not self.alertas:
            self.gerar_alertas()

        if not self.client_groq:
            return "IA não disponível - configure CHAVE_GROQ"

        agrupados = self.alertas_por_nivel()

        contexto = f"""
RELATÓRIO DE ALERTAS DE ESTOQUE - {datetime.now().strftime('%d/%m/%Y %H:%M')}

RESUMO:
- Alertas CRÍTICOS: {len(agrupados['CRITICO'])} itens
- Alertas URGENTES: {len(agrupados['URGENTE'])} itens
- Alertas de ATENÇÃO: {len(agrupados['ATENCAO'])} itens

ITENS CRÍTICOS (ruptura iminente):
"""
        for a in agrupados['CRITICO'][:10]:
            contexto += f"- {a['item']}: saldo {a['saldo_atual']:.0f}, cobertura {a['dias_cobertura']:.0f} dias\n"

        contexto += "\nITENS URGENTES:\n"
        for a in agrupados['URGENTE'][:10]:
            contexto += f"- {a['item']}: saldo {a['saldo_atual']:.0f}, cobertura {a['dias_cobertura']:.0f} dias\n"

        prompt = f"""
{contexto}

Como analista de supply chain, forneça:
1. Avaliação geral da situação do estoque
2. Top 5 itens que precisam de ação IMEDIATA
3. Recomendações práticas para os próximos 7 dias
4. Riscos de ruptura de produção

Seja direto, use português brasileiro e foque em ações concretas.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é um gestor de supply chain experiente em indústria têxtil."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Erro ao gerar resumo: {e}"

    def exibir_painel(self):
        """Exibe painel de alertas no terminal"""
        if not self.alertas:
            self.gerar_alertas()

        agrupados = self.alertas_por_nivel()

        print("\n" + "=" * 70)
        print(" 🚨 PAINEL DE ALERTAS INTELIGENTES - MARFIM IA")
        print(" " + datetime.now().strftime('%d/%m/%Y %H:%M'))
        print("=" * 70)

        # Resumo
        print(f"""
📊 RESUMO GERAL
{'─' * 50}
🔴 CRÍTICOS:  {len(agrupados['CRITICO']):>4} itens (ação imediata!)
🟠 URGENTES:  {len(agrupados['URGENTE']):>4} itens (7 dias)
🟡 ATENÇÃO:   {len(agrupados['ATENCAO']):>4} itens (15 dias)
{'─' * 50}
   TOTAL:     {len(self.alertas):>4} alertas ativos
""")

        # Críticos
        if agrupados['CRITICO']:
            print("\n🔴 ALERTAS CRÍTICOS - AÇÃO IMEDIATA")
            print("-" * 70)
            print(f"{'Item':<35} {'Saldo':>10} {'Cobertura':>12} {'Comprar':>10}")
            print("-" * 70)
            for a in agrupados['CRITICO'][:15]:
                cob = f"{a['dias_cobertura']:.0f} dias" if a['dias_cobertura'] < 999 else "N/A"
                print(f"{a['item'][:34]:<35} {a['saldo_atual']:>10.0f} {cob:>12} {a['qtd_sugerida']:>10.0f}")

        # Urgentes
        if agrupados['URGENTE']:
            print("\n🟠 ALERTAS URGENTES - PRÓXIMOS 7 DIAS")
            print("-" * 70)
            for a in agrupados['URGENTE'][:10]:
                cob = f"{a['dias_cobertura']:.0f} dias"
                print(f"  • {a['item'][:40]:<40} | {cob:>10} | Comprar: {a['qtd_sugerida']:.0f}")

        # Atenção
        if agrupados['ATENCAO']:
            print(f"\n🟡 ATENÇÃO - {len(agrupados['ATENCAO'])} itens para monitorar")

        return agrupados

    def exportar_alertas(self, arquivo=None):
        """Exporta alertas para Excel"""
        if not self.alertas:
            self.gerar_alertas()

        if not arquivo:
            arquivo = f"alertas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        df = pd.DataFrame(self.alertas)
        df.to_excel(arquivo, index=False)
        print(f"✅ Alertas exportados para: {arquivo}")
        return arquivo


def executar_alertas():
    """Execução via CLI"""
    sistema = SistemaAlertas()
    sistema.carregar_dados()
    sistema.exibir_painel()

    print("\n" + "=" * 70)
    opcao = input("\nDeseja análise IA detalhada? (s/n): ").strip().lower()
    if opcao == 's':
        print("\n🤖 Gerando análise com IA...")
        analise = sistema.gerar_resumo_ia()
        print("\n" + "=" * 70)
        print(" ANÁLISE INTELIGENTE")
        print("=" * 70)
        print(analise)

    opcao = input("\nExportar alertas para Excel? (s/n): ").strip().lower()
    if opcao == 's':
        sistema.exportar_alertas()


if __name__ == "__main__":
    executar_alertas()
