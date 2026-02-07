"""
Chatbot Inteligente de Estoque
Permite consultas em linguagem natural sobre o estoque
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, TEMPERATURA_CHAT, converter_para_numero
)

class ChatbotEstoque:
    """Chatbot para consultas de estoque em linguagem natural"""

    def __init__(self):
        self.df_estoque = None
        self.df_historico = None
        self.contexto_conversa = []
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_dados(self):
        """Carrega dados do estoque"""
        print("📡 Carregando base de dados...")
        ss = self.conectar()

        # Índice
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")
        dados = sheet_indice.get_all_values()
        self.df_estoque = pd.DataFrame(dados[1:], columns=dados[0])

        if 'Saldo Atual' in self.df_estoque.columns:
            self.df_estoque['Saldo'] = self.df_estoque['Saldo Atual'].apply(converter_para_numero)

        # Histórico
        sheet_hist = ss.worksheet("ESTOQUE")
        dados_hist = sheet_hist.get_all_values()
        self.df_historico = pd.DataFrame(dados_hist[1:], columns=dados_hist[0])

        # Mapear Unidade de cada item a partir do histórico (último registro)
        if 'Unidade' in self.df_historico.columns:
            unidades = self.df_historico.groupby('Item')['Unidade'].last()
            self.df_estoque['Unidade'] = self.df_estoque['Item'].map(unidades).fillna('UN')

        for col in ['Entrada', 'Saída', 'Saldo']:
            if col in self.df_historico.columns:
                self.df_historico[col] = self.df_historico[col].apply(converter_para_numero)

        self.df_historico['Data'] = pd.to_datetime(
            self.df_historico['Data'], format='%d/%m/%Y', errors='coerce'
        )

        # Calcular métricas básicas
        hoje = datetime.now()
        data_30d = hoje - timedelta(days=30)

        consumo_30d = self.df_historico[
            self.df_historico['Data'] >= data_30d
        ].groupby('Item')['Saída'].sum()

        self.df_estoque['Consumo_30d'] = self.df_estoque['Item'].map(consumo_30d).fillna(0)
        self.df_estoque['Media_Diaria'] = self.df_estoque['Consumo_30d'] / 30
        self.df_estoque['Dias_Cobertura'] = self.df_estoque.apply(
            lambda r: r['Saldo'] / r['Media_Diaria'] if r['Media_Diaria'] > 0 else 999,
            axis=1
        )

        print(f"✅ {len(self.df_estoque)} itens disponíveis para consulta")

    def buscar_item(self, termo):
        """Busca itens pelo nome"""
        if self.df_estoque is None:
            self.carregar_dados()

        resultado = self.df_estoque[
            self.df_estoque['Item'].str.upper().str.contains(termo.upper(), na=False)
        ]
        return resultado

    def obter_estatisticas_gerais(self):
        """Retorna estatísticas gerais do estoque"""
        if self.df_estoque is None:
            self.carregar_dados()

        total_itens = len(self.df_estoque)
        itens_zerados = len(self.df_estoque[self.df_estoque['Saldo'] == 0])
        itens_negativos = len(self.df_estoque[self.df_estoque['Saldo'] < 0])
        itens_criticos = len(self.df_estoque[
            (self.df_estoque['Dias_Cobertura'] < 15) &
            (self.df_estoque['Dias_Cobertura'] < 999)
        ])

        return {
            'total_itens': total_itens,
            'itens_zerados': itens_zerados,
            'itens_negativos': itens_negativos,
            'itens_criticos': itens_criticos,
            'total_unidades': self.df_estoque['Saldo'].sum(),
            'consumo_30d_total': self.df_estoque['Consumo_30d'].sum()
        }

    def obter_top_consumo(self, n=10):
        """Retorna itens com maior consumo"""
        if self.df_estoque is None:
            self.carregar_dados()

        colunas = ['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']
        if 'Unidade' in self.df_estoque.columns:
            colunas.append('Unidade')
        return self.df_estoque.nlargest(n, 'Consumo_30d')[colunas]

    def obter_itens_criticos(self, n=10):
        """Retorna itens mais críticos"""
        if self.df_estoque is None:
            self.carregar_dados()

        criticos = self.df_estoque[
            (self.df_estoque['Dias_Cobertura'] < 30) &
            (self.df_estoque['Dias_Cobertura'] < 999)
        ].nsmallest(n, 'Dias_Cobertura')

        colunas = ['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']
        if 'Unidade' in self.df_estoque.columns:
            colunas.append('Unidade')
        return criticos[colunas]

    def construir_contexto_dados(self, pergunta):
        """Constrói contexto de dados relevante para a pergunta"""
        contexto = f"""
DADOS DO ESTOQUE MARFIM - {datetime.now().strftime('%d/%m/%Y %H:%M')}

"""
        # Estatísticas gerais
        stats = self.obter_estatisticas_gerais()
        contexto += f"""VISÃO GERAL:
- Total de itens cadastrados: {stats['total_itens']}
- Itens com saldo zero: {stats['itens_zerados']}
- Itens com saldo negativo: {stats['itens_negativos']}
- Itens críticos (< 15 dias cobertura): {stats['itens_criticos']}
- Total em estoque: {stats['total_unidades']:,.0f} unidades
- Consumo total últimos 30 dias: {stats['consumo_30d_total']:,.0f} unidades

"""

        # Se menciona item específico, buscar
        palavras = pergunta.upper().split()
        itens_mencionados = []
        for palavra in palavras:
            if len(palavra) > 3:
                encontrados = self.buscar_item(palavra)
                if not encontrados.empty and len(encontrados) <= 5:
                    itens_mencionados.extend(encontrados['Item'].tolist())

        if itens_mencionados:
            contexto += "ITENS MENCIONADOS NA PERGUNTA:\n"
            for item_nome in set(itens_mencionados[:5]):
                item_data = self.df_estoque[self.df_estoque['Item'] == item_nome].iloc[0]
                unidade = item_data.get('Unidade', 'UN')
                contexto += f"""
{item_nome}:
  - Saldo atual: {item_data['Saldo']:.0f} {unidade}
  - Unidade de medida: {unidade}
  - Consumo 30d: {item_data['Consumo_30d']:.0f} {unidade}
  - Cobertura: {item_data['Dias_Cobertura']:.0f} dias
"""

        # Top consumo
        contexto += "\nTOP 5 MAIOR CONSUMO (30 dias):\n"
        top_consumo = self.obter_top_consumo(5)
        for _, row in top_consumo.iterrows():
            unidade = row.get('Unidade', 'UN')
            contexto += f"- {row['Item']}: consumo {row['Consumo_30d']:.0f} {unidade}, saldo {row['Saldo']:.0f} {unidade}\n"

        # Críticos
        contexto += "\nITENS MAIS CRÍTICOS:\n"
        criticos = self.obter_itens_criticos(5)
        for _, row in criticos.iterrows():
            unidade = row.get('Unidade', 'UN')
            contexto += f"- {row['Item']}: {row['Dias_Cobertura']:.0f} dias de cobertura, saldo {row['Saldo']:.0f} {unidade}\n"

        return contexto

    def processar_pergunta(self, pergunta):
        """Processa pergunta do usuário usando IA"""
        if not self.client_groq:
            return "❌ IA não configurada. Configure CHAVE_GROQ no config.py"

        if self.df_estoque is None:
            self.carregar_dados()

        # Construir contexto
        contexto_dados = self.construir_contexto_dados(pergunta)

        # Adicionar histórico de conversa (últimas 3 interações)
        historico = ""
        if self.contexto_conversa:
            historico = "\nHISTÓRICO DA CONVERSA:\n"
            for msg in self.contexto_conversa[-6:]:
                role = "Usuário" if msg['role'] == 'user' else "Assistente"
                historico += f"{role}: {msg['content'][:200]}\n"

        mensagens = [
            {
                "role": "system",
                "content": f"""Você é o assistente de estoque da Marfim Indústria Têxtil.
Responda perguntas sobre estoque de forma direta, clara e em português brasileiro.
Use os dados fornecidos para dar respostas precisas.
Se não souber algo específico, diga que precisa verificar.
Seja conciso mas completo.

IMPORTANTE: Cada item tem sua própria unidade de medida (KG, UN, MT, PC, CX, ROL, PCT, etc).
Sempre mencione a unidade correta ao informar quantidades.
Exemplos de unidades: KG (quilograma), MT (metro), UN (unidade), PC (peça), CX (caixa), ROL (rolo), PCT (pacote).

{contexto_dados}
{historico}"""
            },
            {
                "role": "user",
                "content": pergunta
            }
        ]

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=mensagens,
                temperature=TEMPERATURA_CHAT,
                max_tokens=1000
            )

            resposta = completion.choices[0].message.content

            # Guardar no histórico
            self.contexto_conversa.append({"role": "user", "content": pergunta})
            self.contexto_conversa.append({"role": "assistant", "content": resposta})

            return resposta

        except Exception as e:
            return f"❌ Erro ao processar: {e}"

    def limpar_historico(self):
        """Limpa histórico de conversa"""
        self.contexto_conversa = []
        print("🗑️ Histórico limpo!")

    def executar_chat(self):
        """Executa interface de chat interativo"""
        print("\n" + "=" * 60)
        print(" 🤖 CHATBOT DE ESTOQUE - MARFIM IA")
        print("=" * 60)
        print("""
Faça perguntas sobre o estoque em linguagem natural!

Exemplos:
  • "Qual o saldo de acetato?"
  • "Quais itens estão críticos?"
  • "Quanto consumimos de linha no último mês?"
  • "Preciso comprar botões?"
  • "Mostre os 10 itens mais consumidos"

Comandos especiais:
  • /limpar - Limpa histórico da conversa
  • /stats  - Mostra estatísticas gerais
  • /sair   - Encerra o chat
""")

        self.carregar_dados()
        print("\n✅ Pronto! Digite sua pergunta:\n")

        while True:
            try:
                pergunta = input("Você: ").strip()

                if not pergunta:
                    continue

                if pergunta.lower() == '/sair':
                    print("\n👋 Até logo!")
                    break

                if pergunta.lower() == '/limpar':
                    self.limpar_historico()
                    continue

                if pergunta.lower() == '/stats':
                    stats = self.obter_estatisticas_gerais()
                    print(f"""
📊 ESTATÍSTICAS GERAIS
{'─' * 40}
Total de itens: {stats['total_itens']}
Itens zerados: {stats['itens_zerados']}
Itens negativos: {stats['itens_negativos']}
Itens críticos: {stats['itens_criticos']}
Total em estoque: {stats['total_unidades']:,.0f} un
Consumo 30d: {stats['consumo_30d_total']:,.0f} un
""")
                    continue

                print("\n🤖 Processando...\n")
                resposta = self.processar_pergunta(pergunta)
                print(f"Assistente: {resposta}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Chat encerrado!")
                break
            except Exception as e:
                print(f"\n❌ Erro: {e}\n")


def iniciar_chatbot():
    """Inicia o chatbot"""
    chatbot = ChatbotEstoque()
    chatbot.executar_chat()


if __name__ == "__main__":
    iniciar_chatbot()
