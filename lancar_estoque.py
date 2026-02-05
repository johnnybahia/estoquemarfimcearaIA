import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURAÇÃO ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
ARQUIVO_JSON = "credentials.json"

def converter_para_numero(valor):
    if valor is None or valor == "": return 0.0
    try:
        s = str(valor).strip().replace('.', '').replace(',', '.')
        return float(s)
    except: return 0.0

def realizar_lancamento():
    try:
        # 1. Conexão
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open(NOME_PLANILHA)
        
        sheet_estoque = ss.worksheet("ESTOQUE")
        sheet_indice = ss.worksheet("ÍNDICE_ITENS")

        # 2. Entrada de Dados
        item_nome = input("\nNome do Item para lançamento: ").strip().upper()
        
        dados_indice = sheet_indice.get_all_values()
        df_indice = [row for row in dados_indice if row[0].upper() == item_nome]

        if not df_indice:
            print(f"❌ Item '{item_nome}' não encontrado no índice.")
            return

        item_info = df_indice[0]
        saldo_anterior = converter_para_numero(item_info[1])
        grupo = item_info[3]
        linha_antiga = int(item_info[4]) # Linha do último registro no ESTOQUE
        
        print(f"\n📦 Item: {item_nome} | Saldo Atual: {saldo_anterior}")

        tipo = input("Tipo (E para Entrada / S para Saída): ").strip().upper()
        quantidade = converter_para_numero(input("Quantidade: "))
        nf = input("NF / Documento (Deixe vazio se não houver): ").strip()
        
        # --- LÓGICA DE PREÇO UNITÁRIO ---
        preco_unitario = 0.0
        
        if tipo == 'E' and nf != "":
            # Se for entrada com NF, solicita o preço
            preco_unitario = converter_para_numero(input("Informe o Preço Unitário desta NF: "))
        else:
            # Busca o último preço praticado na aba ESTOQUE (Coluna K - índice 11)
            try:
                ultimo_registro = sheet_estoque.row_values(linha_antiga)
                # Na sua planilha Coluna K é o índice 10 (considerando A=1, B=2...)
                # No row_values do gspread, os índices da lista começam em 0, então K é 10.
                preco_unitario = converter_para_numero(ultimo_registro[10])
                print(f"ℹ️ Repetindo o último preço unitário: R$ {preco_unitario}")
            except:
                preco_unitario = 0.0
                print("⚠️ Não foi possível recuperar o último preço. Definido como 0.")

        obs = input("Observação: ").strip()
        usuario = "Johnny_AI"

        # 3. Cálculo do Novo Saldo
        entrada = quantidade if tipo == 'E' else 0
        saida = quantidade if tipo == 'S' else 0
        novo_saldo = saldo_anterior + entrada - saida
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # 4. Gravação na aba ESTOQUE
        # Colunas: Grupo(A), Item(B), Unidade(C), Data(D), NF(E), Obs(F), S.Ant(G), Ent(H), Sai(I), Saldo(J), Val.Unit(K), AltEm(L), AltPor(M)
        nova_linha = [
            grupo, item_nome, "", agora, nf, obs, 
            str(saldo_anterior).replace('.', ','), 
            str(entrada).replace('.', ','), 
            str(saida).replace('.', ','), 
            str(novo_saldo).replace('.', ','), 
            str(preco_unitario).replace('.', ','), # Coluna K
            agora, usuario
        ]

        # Append row e pega a linha onde foi gravado
        sheet_estoque.append_row(nova_linha, value_input_option='USER_ENTERED')
        
        # Descobrir a linha onde o append_row gravou (última linha)
        # Uma forma simples é contar as linhas totais agora
        nova_linha_no_estoque = len(sheet_estoque.get_col(2)) # Conta nomes na coluna B

        # 5. Atualização do ÍNDICE_ITENS
        for i, row in enumerate(dados_indice):
            if row[0].upper() == item_nome:
                idx = i + 1
                # Atualiza Saldo(B), Data(C) e a nova Linha do Estoque(E)
                sheet_indice.update(f'B{idx}:C{idx}', [[str(novo_saldo).replace('.', ','), agora]])
                sheet_indice.update_cell(idx, 5, nova_linha_no_estoque)
                break

# --- DENTRO DA FUNÇÃO realizar_lancamento(), APÓS O SUCESSO DO LANÇAMENTO ---

        # 6. GATILHO DE INTELIGÊNCIA (Só gasta cota se necessário)
        ponto_critico = 10  # Exemplo: se baixar de 10 unidades
        if novo_saldo <= ponto_critico:
            print("\n🤖 IA: Detectado estoque baixo. Solicitando análise estratégica...")
            
            # Pegamos apenas os últimos 10 movimentos para economizar tokens
            historico_ia = sheet_estoque.get_all_values()[-10:] 
            prompt = f"O item {item_nome} chegou ao saldo {novo_saldo}. Com base nestes últimos movimentos {historico_ia}, qual a urgência de compra de 1 a 10?"
            
            try:
                # Chamada ao Gemini
                response = model.generate_content(prompt)
                print(f"💡 SUGESTÃO IA: {response.text}")
            except Exception as e:
                print("⚠️ IA indisponível ou limite de cota atingido, mas o lançamento foi gravado!")
        else:
            print(f"✅ Saldo {novo_saldo} está em nível seguro. IA em standby para economizar sua cota.")

        print(f"\n✅ LANÇAMENTO REALIZADO!")
        print(f"Item: {item_nome} | Novo Saldo: {novo_saldo} | Preço Unit: {preco_unitario}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    realizar_lancamento()