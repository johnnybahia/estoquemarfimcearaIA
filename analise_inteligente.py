import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from groq import Groq  # Importando a nova biblioteca
from datetime import datetime
import time

# --- CONFIGURAÇÕES ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
ARQUIVO_JSON = "credentials.json"
CHAVE_GROQ = "" # Cole sua chave aqui

# INICIALIZAÇÃO GROQ
client_groq = Groq(api_key=CHAVE_GROQ)

def converter_para_numero(valor):
    if valor is None or valor == "":
        return 0.0
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        s = str(valor).strip().replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

def consultar_ia_groq(prompt):
    """Consulta a IA via Groq (Llama 3.3)"""
    try:
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um especialista em logística e gestão de estoque. Forneça respostas curtas, diretas e técnicas."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.5, # Menor temperatura = mais precisão técnica
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Erro na Groq: {e}")
        return None

def analisar_item_estrategico(nome_item):
    try:
        # 1. CONEXÃO COM GOOGLE SHEETS
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open(NOME_PLANILHA)
        sheet_estoque = ss.worksheet("ESTOQUE")
        
        print(f"\n📡 Conectando ao Banco de Dados: {NOME_PLANILHA}...")

        # 2. TRATAMENTO DOS DADOS
        dados_brutos = sheet_estoque.get_all_values()
        df = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
        
        # Filtra o item ignorando maiúsculas/minúsculas
        historico_item = df[df['Item'].str.upper() == nome_item.upper()].copy()

        if historico_item.empty:
            print(f"❌ Item '{nome_item}' não encontrado na aba ESTOQUE.")
            return

        # Converte colunas numéricas
        for col in ['Entrada', 'Saída', 'Saldo']:
            historico_item[col] = historico_item[col].apply(converter_para_numero)

        saldo_atual = historico_item['Saldo'].iloc[-1]
        saidas = historico_item[historico_item['Saída'] > 0]['Saída']
        media_saida = saidas.mean() if not saidas.empty else 0
        total_saidas = saidas.count()

        # Obter unidade de medida do último registro
        unidade = historico_item['Unidade'].iloc[-1] if 'Unidade' in historico_item.columns else 'UN'
        if not unidade or unidade.strip() == '':
            unidade = 'UN'

        print("\n" + "=" * 60)
        print(f"📊 RELATÓRIO TÉCNICO: {nome_item}")
        print("=" * 60)
        print(f"📏 Unidade de Medida: {unidade}")
        print(f"✅ Saldo Atual: {saldo_atual} {unidade}")
        print(f"📉 Média por Saída: {media_saida:.2f} {unidade}")
        print(f"📦 Movimentações de Saída: {total_saidas}")

        # 3. CONSTRUÇÃO DO PROMPT
        # Pegamos os últimos 10 lançamentos para dar contexto à IA
        contexto_recente = historico_item[['Data', 'Saída', 'Saldo', 'Obs']].tail(10).to_string(index=False)
        
        prompt = f"""
        Analise o estoque do item: {nome_item}

        DADOS ATUAIS:
        - Unidade de medida: {unidade}
        - Saldo em mãos: {saldo_atual} {unidade}
        - Média histórica de consumo: {media_saida:.2f} {unidade} por saída.

        HISTÓRICO RECENTE:
        {contexto_recente}

        TAREFA:
        Com base no saldo e na média de consumo, o estoque está em nível crítico?
        Recomende se devo comprar mais agora e em qual quantidade aproximada (usando a unidade {unidade}).
        Seja direto e use português do Brasil.
        """

        # 4. CHAMADA DA IA
        print("\n🤖 Processando Insights com Groq (Llama 3.3)... Aguarde.")
        resposta = consultar_ia_groq(prompt)
        
        if resposta:
            print("\n" + "=" * 60)
            print(f"🤖 PARECER DA IA")
            print("=" * 60)
            print(resposta.strip())
            print("=" * 60)
        else:
            print("\n❌ Não foi possível obter o parecer da IA.")

    except Exception as e:
        print(f"\n❌ Erro Geral: {e}")

if __name__ == "__main__":
    # Garante a instalação da biblioteca se não houver
    # Use: pip install groq gspread oauth2client pandas
    
    item = input("\nQual item deseja analisar agora? ").strip().upper()
    analisar_item_estrategico(item)