import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

class GestorMarfim:
    def __init__(self, planilha_nome, credentials_file):
        # Configuração de acesso
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        self.client = gspread.authorize(creds)
        self.ss = self.client.open(planilha_nome)
        
        # Abas principais
        self.sheet_estoque = self.ss.worksheet("ESTOQUE")
        self.sheet_indice = self.ss.worksheet("ÍNDICE_ITENS")

    def obter_ultimo_registro(self, nome_item):
        """
        Busca O(1) no Índice para saber o saldo atual e grupo.
        Simula a função getLastRegistrationFromIndex do seu .gs
        """
        # Lendo a aba de Índice
        dados_indice = self.sheet_indice.get_all_records()
        df_indice = pd.DataFrame(dados_indice)
        
        # Padronizando para busca
        nome_item = str(nome_item).strip().upper()
        
        # Filtrando o item
        registro = df_indice[df_indice['Item'].str.upper() == nome_item]
        def lancar_movimentacao(self, item, entrada=0, saida=0, nf="", obs="", usuario="Python_System"):
        # 1. Busca o saldo anterior no índice
        info_item = self.obter_ultimo_registro(item)
        
        if info_item:
            saldo_anterior = info_item['saldo_atual']
            grupo = info_item['grupo']
        else:
            # Se o item não existe no índice, saldo é 0 e precisamos definir o grupo
            saldo_anterior = 0
            grupo = "NÃO DEFINIDO" # Aqui poderíamos forçar o usuário a escolher um grupo
            print(f"Aviso: Item {item} não encontrado no índice. Iniciando com saldo 0.")

        # 2. Calcula novo saldo
        novo_saldo = saldo_anterior + entrada - saida
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # 3. Prepara a linha (Seguindo a estrutura da sua planilha)
        # Colunas: Grupo(A), Item(B), Unidade(C), Data(D), NF(E), Obs(F), S.Ant(G), Ent(H), Sai(I), Saldo(J)...
        nova_linha = [
            grupo,           # A
            item.upper(),    # B
            "",              # C (Unidade - pode ser parametrizado)
            agora,           # D
            nf,              # E
            obs,             # F
            saldo_anterior,  # G
            entrada,         # H
            saida,           # I
            novo_saldo,      # J
            0,               # K (Valor Unitário)
            agora,           # L (Alterado Em)
            usuario          # M (Alterado Por)
        ]

        # 4. Insere na aba ESTOQUE
        self.sheet_estoque.append_row(nova_linha, value_input_option='USER_ENTERED')
        
        # 5. Atualiza o ÍNDICE_ITENS (Crucial para o próximo lançamento)
        self.atualizar_indice(item, novo_saldo, grupo)
        
        return f"Sucesso! Item {item} lançado. Novo Saldo: {novo_saldo}"

    def atualizar_indice(self, item, novo_saldo, grupo):
        # Localiza a linha do item no índice e atualiza
        # Para simplificar agora, podemos usar a mesma lógica do seu .gs
        # ou reconstruir a linha do item.
        print(f"Atualizando índice para {item}...")
        # (Lógica de atualização do índice virá no próximo passo)

        if not registro.empty:
            return {
                "item": registro.iloc[0]['Item'],
                "saldo_atual": float(str(registro.iloc[0]['Saldo Atual']).replace(',', '.')),
                "grupo": registro.iloc[0]['Grupo'],
                "linha_estoque": registro.iloc[0]['Linha ESTOQUE']
            }
        else:
            return None # Item novo