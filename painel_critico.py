import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
ARQUIVO_JSON = "credentials.json"

def gerar_painel():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open(NOME_PLANILHA)
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")

        # 1. LER O ÍNDICE (O mapa que recalibramos)
        print(f"📊 Gerando Relatório de Alertas para Marfim...")
        dados = sheet_indice.get_all_values()
        df = pd.DataFrame(dados[1:], columns=dados[0])

        # Converter Saldo para número
        df['Saldo Atual'] = df['Saldo Atual'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Saldo Atual'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
        
        # Converter Data para formato Python
        df['Última Data'] = pd.to_datetime(df['Última Data'], dayfirst=True, errors='coerce')

        # 2. IDENTIFICAR ALERTAS
        hoje = datetime.now()
        prazo_desatualizado = hoje - timedelta(days=15)

        # Alerta A: Saldo Negativo ou Zerado
        criticos = df[df['Saldo Atual'] <= 0]

        # Alerta B: Sem atualização há mais de 15 dias
        desatualizados = df[df['Última Data'] < prazo_desatualizado]

        # 3. EXIBIR RESULTADOS
        print("\n" + "="*50)
        print(f"⚠️ ITENS COM SALDO CRÍTICO ({len(criticos)})")
        print("="*50)
        if not criticos.empty:
            for _, row in criticos.iterrows():
                print(f"• {row['Item']} | Saldo: {row['Saldo Atual']} | Grupo: {row['Grupo']}")
        else:
            print("✅ Nenhum item zerado ou negativo.")

        print("\n" + "="*50)
        print(f"⏳ ITENS SEM MOVIMENTAÇÃO > 15 DIAS ({len(desatualizados)})")
        print("="*50)
        if not desatualizados.empty:
            for _, row in desatualizados.head(10).iterrows(): # Mostra os 10 primeiros
                data_str = row['Última Data'].strftime('%d/%m/%Y') if not pd.isnull(row['Última Data']) else "N/A"
                print(f"• {row['Item']} | Última vez: {data_str}")
        
        print("\n" + "="*50)
        print("💡 DICA: Use o 'lancar_estoque.py' para atualizar esses itens.")

    except Exception as e:
        print(f"❌ Erro ao gerar painel: {e}")

if __name__ == "__main__":
    gerar_painel()