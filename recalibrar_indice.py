import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
ARQUIVO_JSON = "credentials.json"

def reconstruir_indice():
    try:
        # 1. Conexão com a Planilha de Teste
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open(NOME_PLANILHA)
        
        sheet_estoque = ss.worksheet("ESTOQUE")
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")

        print(f"🚀 Conectado à planilha de teste: {NOME_PLANILHA}")
        print("📥 Lendo aba ESTOQUE (40k+ linhas)... Isso pode levar alguns segundos.")
        
        # Lê todos os valores de uma vez (Método mais rápido)
        dados_estoque = sheet_estoque.get_all_values()
        
        if len(dados_estoque) < 2:
            print("⚠️ A aba ESTOQUE parece estar vazia ou sem cabeçalho.")
            return

        # Criar DataFrame (Tabela na memória do Python)
        # Colunas esperadas: A=Grupo, B=Item, D=Data, J=Saldo
        df = pd.DataFrame(dados_estoque[1:], columns=dados_estoque[0])
        
        # Criar a coluna com o número real da linha (index + 2)
        df['Linha_Real'] = df.index + 2
        
        print(f"📊 {len(df)} registros encontrados. Iniciando filtragem dos últimos lançamentos...")

        # Limpeza: Remove linhas onde o nome do Item está vazio
        df = df[df['Item'].str.strip() != ""]
        
        # O PULO DO GATO:
        # O comando 'last()' pega o registro que está mais ao fim da planilha para cada item.
        indice_novo = df.groupby('Item').last().reset_index()
        
        linhas_para_indice = []
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        for _, row in indice_novo.iterrows():
            linhas_para_indice.append([
                row['Item'],      # A: Item
                row['Saldo'],     # B: Saldo Atual
                row['Data'],      # C: Última Data
                row['Grupo'],     # D: Grupo
                row['Linha_Real'],# E: Linha ESTOQUE
                agora             # F: Última Atualização (agora)
            ])

        print(f"✨ Total de {len(linhas_para_indice)} itens únicos identificados.")
        
        # 2. Atualização da aba de Índice
        print("🧹 Limpando índice antigo na planilha de teste...")
        # Limpamos uma área grande para garantir que não sobre sujeira
        sheet_indice.batch_clear(["A2:F10000"]) 
        
        print("✍️ Escrevendo novo índice recalibrado...")
        sheet_indice.update('A2', linhas_para_indice)
        
        print("\n" + "="*40)
        print("✅ RECALIBRAGEM CONCLUÍDA NO TESTE!")
        print("="*40)
        print("Próximo passo: Rode o 'consulta_estoque.py' (apontando para a planilha teste) ")
        print("e veja se os Acetatos agora aparecem como Sincronizados.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Erro: Planilha '{NOME_PLANILHA}' não encontrada. Verifique se o nome está correto e se você a compartilhou com o e-mail do credentials.json.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    reconstruir_indice()