import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- CONFIGURAÇÃO ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
ARQUIVO_JSON = "credentials.json"

def converter_para_numero(valor):
    """
    Tratamento rigoroso para o padrão brasileiro.
    Garante que '2,6' seja 2.6 e não 26.
    """
    if valor is None or valor == "":
        return 0.0
    
    # Se já for um número (float ou int), apenas retorna
    if isinstance(valor, (int, float)):
        return float(valor)
    
    try:
        # Converte para string e limpa espaços
        s = str(valor).strip()
        
        # Se houver vírgula e ponto, o ponto costuma ser milhar (ex: 1.200,50)
        if ',' in s and '.' in s:
            s = s.replace('.', '') # Remove o ponto de milhar
            s = s.replace(',', '.') # Troca a vírgula decimal por ponto
        # Se houver apenas vírgula (ex: 2,6)
        elif ',' in s:
            s = s.replace(',', '.')
            
        return float(s)
    except Exception:
        return 0.0

def realizar_consulta():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open(NOME_PLANILHA)
        
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")
        sheet_estoque = ss.worksheet("ESTOQUE")
        
        # O PULO DO GATO: Lemos o índice como TEXTO puro primeiro para o pandas não estragar a vírgula
        dados_indice = sheet_indice.get_all_values()
        df_indice = pd.DataFrame(dados_indice[1:], columns=dados_indice[0])
        
        item_busca = input("\nDigite o nome do Item (ou parte dele): ").strip().upper()
        resultado = df_indice[df_indice['Item'].astype(str).str.upper().str.contains(item_busca)]
        
        if resultado.empty:
            print(f"❌ Nenhum item encontrado.")
            return

        print(f"\n✅ Analisando {len(resultado)} itens...")
        print("=" * 70)
        
        for _, row in resultado.iterrows():
            item_nome = row['Item']
            # Usamos a conversão blindada aqui
            saldo_index = converter_para_numero(row['Saldo Atual'])
            linha_estoque = int(row['Linha ESTOQUE'])
            
            # Buscamos o valor real na aba estoque
            valor_celula_estoque = sheet_estoque.cell(linha_estoque, 10).value
            saldo_estoque_real = converter_para_numero(valor_celula_estoque)
            
            print(f"ITEM: {item_nome}")
            print(f"SALDO ÍNDICE: {saldo_index} | SALDO ESTOQUE: {saldo_estoque_real}")
            
            if abs(saldo_index - saldo_estoque_real) < 0.001:
                print("🟢 STATUS: Sincronizado")
            else:
                print(f"🔴 STATUS: Divergência! Diferença de {round(saldo_index - saldo_estoque_real, 3)}")
            print("-" * 70)

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    realizar_consulta()