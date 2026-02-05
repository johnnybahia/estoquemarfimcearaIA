from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from groq import Groq

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
CHAVE_GROQ = ""
ARQUIVO_JSON = "credentials.json"
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
client_groq = Groq(api_key=CHAVE_GROQ)

def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
    return gspread.authorize(creds).open(NOME_PLANILHA)

def converter_para_numero(valor):
    if valor is None or str(valor).strip() == "": return 0.0
    try:
        s = str(valor).strip().replace('.', '').replace(',', '.')
        return float(s)
    except: return 0.0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    item_nome = request.json.get('item').upper()
    ss = conectar_google()
    sh = ss.worksheet("ÍNDICE_ITENS")
    dados = sh.get_all_values()
    df = pd.DataFrame(dados[1:], columns=dados[0])
    
    # Filtra e garante que o retorno contenha a coluna 'Unidade'
    res = df[df['Item'].astype(str).str.upper().str.contains(item_nome)]
    return res.to_json(orient='records')

@app.route('/analisar', methods=['POST'])
def analisar():
    dados = request.json
    item_alvo = dados['item']
    
    try:
        ss = conectar_google()
        sh_estoque = ss.worksheet("ESTOQUE")
        
        # Pega dados brutos do estoque
        dados_est = sh_estoque.get_all_values()
        df_est = pd.DataFrame(dados_est[1:], columns=dados_est[0])
        
        # Filtra histórico específico
        df_est['Item'] = df_est['Item'].astype(str)
        hist = df_est[df_est['Item'].str.upper() == item_alvo.upper()].tail(12)
        
        if hist.empty:
            return jsonify({"resposta": "Não há movimentações registradas para este item."})

        # Captura a UNIDADE de medida do último registro
        unidade_medida = hist['Unidade'].iloc[-1] if 'Unidade' in hist.columns else "unid"
        
        # Limpa colunas numéricas
        for col in ['Entrada', 'Saída', 'Saldo']:
            hist[col] = hist[col].apply(converter_para_numero)
        
        resumo_texto = hist[['Data', 'Entrada', 'Saída', 'Saldo', 'Obs']].to_string(index=False)
        saldo_final = hist['Saldo'].iloc[-1]
        
        prompt = f"""
        Você é o Analista de Suprimentos da Marfim Indústria Têxtil. 
        PRODUTO: {item_alvo}
        UNIDADE: {unidade_medida}
        SALDO ATUAL: {saldo_final} {unidade_medida}
        
        HISTÓRICO RECENTE:
        {resumo_texto}
        
        INSTRUÇÕES:
        1. Baseado nas datas e quantidades de saída, calcule o consumo médio em {unidade_medida}.
        2. Analise se o saldo de {saldo_final} {unidade_medida} é suficiente para os próximos 15 dias.
        3. Dê uma recomendação clara de compra (Sim/Não) e a quantidade em {unidade_medida}.
        
        Seja técnico, use português do Brasil e não seja genérico.
        """
        
        chat = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Analista de inventário industrial. Unidade de medida: {unidade_medida}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return jsonify({"resposta": chat.choices[0].message.content, "unidade": unidade_medida})
    
    except Exception as e:
        return jsonify({"resposta": f"Erro técnico: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)