"""
Classificador Inteligente de Itens
Usa IA para categorizar itens automaticamente
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from groq import Groq
from config import (
    NOME_PLANILHA, ARQUIVO_CREDENTIALS, CHAVE_GROQ,
    MODELO_GROQ, CATEGORIAS_ITEM, converter_para_numero
)

class ClassificadorItens:
    """Classifica itens automaticamente usando IA"""

    def __init__(self):
        self.df_itens = None
        self.classificacoes = {}
        self.client_groq = Groq(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

    def conectar(self):
        """Conecta ao Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_PLANILHA)

    def carregar_itens(self):
        """Carrega lista de itens"""
        print("📡 Carregando itens...")
        ss = self.conectar()

        sheet = ss.worksheet("ÍNDICE_ITENS")
        dados = sheet.get_all_values()
        self.df_itens = pd.DataFrame(dados[1:], columns=dados[0])

        if 'Saldo Atual' in self.df_itens.columns:
            self.df_itens['Saldo'] = self.df_itens['Saldo Atual'].apply(converter_para_numero)

        print(f"✅ {len(self.df_itens)} itens carregados")
        return self.df_itens

    def classificar_por_regras(self, nome_item):
        """Classifica item baseado em regras simples (palavras-chave)"""
        nome = nome_item.upper()

        regras = {
            'TECIDO': ['TECIDO', 'MALHA', 'JEANS', 'SARJA', 'TRICOLINE', 'VISCOSE', 'ALGODAO', 'POLIESTER', 'LINHO'],
            'LINHA': ['LINHA', 'FIO', 'COSTURA'],
            'BOTAO': ['BOTAO', 'BOTÕES', 'BOTOES'],
            'ZIPER': ['ZIPER', 'ZIPPER', 'ZÍPER'],
            'ELASTICO': ['ELASTICO', 'ELÁSTICO', 'LASTEX'],
            'FITA': ['FITA', 'VIÉS', 'VIES', 'CADARÇO', 'CADARCO'],
            'ETIQUETA': ['ETIQUETA', 'TAG', 'LABEL'],
            'ENTRETELA': ['ENTRETELA', 'INTERLINING'],
            'QUIMICO': ['CORANTE', 'TINTA', 'SOLVENTE', 'AMACIANTE', 'BRANQUEADOR', 'QUIMICO'],
            'EMBALAGEM': ['SACO', 'CAIXA', 'SACOLA', 'EMBALAGEM', 'PLASTICO', 'PAPEL'],
            'AVIAMENTO': ['REBITE', 'ILHOS', 'COLCHETE', 'VELCRO', 'FIVELA', 'REGULADOR'],
            'AGULHA': ['AGULHA', 'ALFINETE'],
            'FORRO': ['FORRO', 'ENTREFORRO']
        }

        for categoria, palavras in regras.items():
            for palavra in palavras:
                if palavra in nome:
                    return categoria

        return 'OUTROS'

    def classificar_com_ia(self, nome_item):
        """Classifica item usando IA para casos mais complexos"""
        if not self.client_groq:
            return self.classificar_por_regras(nome_item)

        categorias_str = ", ".join(CATEGORIAS_ITEM)

        prompt = f"""
Classifique este item de indústria têxtil em UMA das categorias abaixo:
Categorias: {categorias_str}

Item: {nome_item}

Responda APENAS com o nome da categoria, sem explicação.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você classifica itens de estoque têxtil. Responda apenas com a categoria."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20
            )

            categoria = completion.choices[0].message.content.strip().upper()

            # Validar se é categoria válida
            if categoria in CATEGORIAS_ITEM:
                return categoria

            # Tentar encontrar categoria mais próxima
            for cat in CATEGORIAS_ITEM:
                if cat in categoria or categoria in cat:
                    return cat

            return 'OUTROS'

        except Exception:
            return self.classificar_por_regras(nome_item)

    def classificar_todos(self, usar_ia=False):
        """Classifica todos os itens"""
        if self.df_itens is None:
            self.carregar_itens()

        print(f"\n🏷️ Classificando itens (IA: {'Sim' if usar_ia else 'Não'})...")

        for _, row in self.df_itens.iterrows():
            item = row['Item']
            grupo_atual = row.get('Grupo', '')

            if usar_ia:
                categoria = self.classificar_com_ia(item)
            else:
                categoria = self.classificar_por_regras(item)

            self.classificacoes[item] = {
                'item': item,
                'categoria_sugerida': categoria,
                'grupo_atual': grupo_atual,
                'mudou': categoria != grupo_atual.upper() if grupo_atual else True
            }

        print(f"✅ {len(self.classificacoes)} itens classificados")
        return self.classificacoes

    def analisar_classificacoes(self):
        """Analisa distribuição das classificações"""
        if not self.classificacoes:
            self.classificar_todos()

        # Contar por categoria
        contagem = {}
        mudancas = []

        for item, dados in self.classificacoes.items():
            cat = dados['categoria_sugerida']
            contagem[cat] = contagem.get(cat, 0) + 1

            if dados['mudou']:
                mudancas.append(dados)

        return {
            'distribuicao': contagem,
            'total_itens': len(self.classificacoes),
            'total_mudancas': len(mudancas),
            'mudancas': mudancas
        }

    def gerar_relatorio_ia(self):
        """Gera relatório de classificação com IA"""
        if not self.client_groq:
            return "IA não disponível"

        analise = self.analisar_classificacoes()

        contexto = f"""
ANÁLISE DE CLASSIFICAÇÃO DE ITENS

Total de itens: {analise['total_itens']}
Itens que mudariam de categoria: {analise['total_mudancas']}

Distribuição por categoria:
"""
        for cat, qtd in sorted(analise['distribuicao'].items(), key=lambda x: -x[1]):
            contexto += f"- {cat}: {qtd} itens ({qtd/analise['total_itens']*100:.1f}%)\n"

        if analise['mudancas']:
            contexto += "\nExemplos de mudanças sugeridas:\n"
            for m in analise['mudancas'][:10]:
                contexto += f"- {m['item']}: {m['grupo_atual'] or 'SEM GRUPO'} → {m['categoria_sugerida']}\n"

        prompt = f"""
{contexto}

Analise esta classificação de itens e forneça:
1. A classificação está bem distribuída?
2. Há categorias com muitos ou poucos itens?
3. Recomendações para melhorar a organização
4. Benefícios de manter a classificação atualizada

Use português brasileiro.
"""

        try:
            completion = self.client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": "Você é especialista em organização de estoques industriais."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Erro: {e}"

    def exibir_resultado(self):
        """Exibe resultado da classificação"""
        analise = self.analisar_classificacoes()

        print("\n" + "=" * 60)
        print(" 🏷️ CLASSIFICADOR INTELIGENTE - MARFIM IA")
        print("=" * 60)

        print(f"""
📊 DISTRIBUIÇÃO POR CATEGORIA
{'─' * 50}""")

        total = analise['total_itens']
        for cat, qtd in sorted(analise['distribuicao'].items(), key=lambda x: -x[1]):
            barra = '█' * int(qtd / total * 30)
            print(f"{cat:<15} {qtd:>5} ({qtd/total*100:>5.1f}%) {barra}")

        print(f"""
{'─' * 50}
Total: {total} itens

📝 MUDANÇAS SUGERIDAS: {analise['total_mudancas']} itens
""")

        if analise['mudancas']:
            print("-" * 60)
            print(f"{'Item':<35} {'Atual':>10} → {'Sugerido':<10}")
            print("-" * 60)
            for m in analise['mudancas'][:15]:
                atual = m['grupo_atual'][:10] if m['grupo_atual'] else 'N/A'
                print(f"{m['item'][:34]:<35} {atual:>10} → {m['categoria_sugerida']:<10}")

            if len(analise['mudancas']) > 15:
                print(f"\n... e mais {len(analise['mudancas']) - 15} mudanças")

    def exportar_classificacoes(self, arquivo=None):
        """Exporta classificações para Excel"""
        if not self.classificacoes:
            self.classificar_todos()

        if not arquivo:
            arquivo = f"classificacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        df = pd.DataFrame(list(self.classificacoes.values()))

        with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Todas Classificações', index=False)

            # Aba de mudanças
            df_mudancas = df[df['mudou'] == True]
            if not df_mudancas.empty:
                df_mudancas.to_excel(writer, sheet_name='Mudanças Sugeridas', index=False)

            # Aba por categoria
            for cat in CATEGORIAS_ITEM:
                df_cat = df[df['categoria_sugerida'] == cat]
                if not df_cat.empty:
                    df_cat.to_excel(writer, sheet_name=cat[:31], index=False)

        print(f"✅ Exportado: {arquivo}")
        return arquivo


def executar_classificador():
    """Execução via CLI"""
    classificador = ClassificadorItens()
    classificador.carregar_itens()

    print("\n📊 Opções:")
    print("1. Classificar por regras (rápido)")
    print("2. Classificar com IA (mais preciso)")
    print("0. Sair")

    opcao = input("\nEscolha: ").strip()

    if opcao in ["1", "2"]:
        usar_ia = opcao == "2"
        classificador.classificar_todos(usar_ia=usar_ia)
        classificador.exibir_resultado()

        if input("\nGerar análise IA? (s/n): ").lower() == 's':
            print("\n🤖 Analisando...")
            print("\n" + classificador.gerar_relatorio_ia())

        if input("\nExportar para Excel? (s/n): ").lower() == 's':
            classificador.exportar_classificacoes()


if __name__ == "__main__":
    executar_classificador()
