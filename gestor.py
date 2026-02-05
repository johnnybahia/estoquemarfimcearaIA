import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import re
import warnings

warnings.filterwarnings("ignore")

# --- CONFIGURAÇÕES ---
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE"
ABA_ESTOQUE = "ESTOQUE"
ABA_INDICE = "ÍNDICE_ITENS"

# PARÂMETROS DE ANÁLISE
LIMITE_ESTOQUE_BAIXO = 21
DIAS_SEM_MOVIMENTO = 30
DIAS_ATENCAO = 60
DIAS_OBSOLETO = 90
SIMILARIDADE_DUPLICADO = 0.85
MESES_ANALISE_CONSUMO = 3  # Período para análise de consumo

# Configuração Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# ============================================================
# FUNÇÕES DE FORMATAÇÃO
# ============================================================
def titulo(texto):
    print(f"\n{'='*70}")
    print(f" {texto.upper()}")
    print(f"{'='*70}")

def secao(texto, emoji="📌"):
    print(f"\n{emoji} {texto}")
    print("-" * 60)

def subsecao(texto):
    print(f"\n  ▸ {texto}")

def linha_item(col1, col2, col3="", largura=35):
    col1_fmt = (str(col1)[:largura-2] + '..') if len(str(col1)) > largura else str(col1)
    print(f"    {col1_fmt:<{largura}} {str(col2):>12} {str(col3):>15}")

def separador():
    print(f"    {'-'*62}")

def tabela_header(col1, col2, col3, largura=35):
    print(f"    {col1:<{largura}} {col2:>12} {col3:>15}")
    separador()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def converter_data(valor):
    """Converte string para datetime"""
    if pd.isna(valor) or str(valor).strip() == '':
        return None
    
    formatos = ['%d/%m/%Y', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']
    valor_str = str(valor).strip()
    
    for fmt in formatos:
        try:
            return datetime.strptime(valor_str.split()[0], fmt)
        except:
            continue
    return None

def similaridade(a, b):
    """Calcula similaridade entre duas strings"""
    a_limpo = re.sub(r'\s+', ' ', str(a).lower().strip())
    b_limpo = re.sub(r'\s+', ' ', str(b).lower().strip())
    return SequenceMatcher(None, a_limpo, b_limpo).ratio()

def normalizar_texto(texto):
    """Normaliza texto para comparação"""
    texto = str(texto).lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto

# ============================================================
# CALCULAR CONSUMO DOS ÚLTIMOS 3 MESES
# ============================================================

def calcular_consumo_periodo(df_historico, meses=3):
    """
    Calcula o consumo (saídas) dos últimos X meses para cada item.
    Retorna DataFrame com: Item, Consumo_Periodo, Media_Mensal
    """
    hoje = datetime.now()
    data_inicio = hoje - timedelta(days=meses * 30)
    
    # Converter datas
    df_historico['_data_mov'] = df_historico['Data'].apply(converter_data)
    
    # Filtrar movimentações do período
    df_periodo = df_historico[
        (df_historico['_data_mov'] >= data_inicio) & 
        (df_historico['_data_mov'] <= hoje)
    ].copy()
    
    # Somar saídas por item no período
    consumo = df_periodo.groupby('Item').agg({
        'Saída': 'sum',
        'Entrada': 'sum',
        '_data_mov': ['min', 'max', 'count']
    }).reset_index()
    
    # Ajustar nomes das colunas
    consumo.columns = ['Item', 'Consumo_3M', 'Entrada_3M', 'Primeira_Mov', 'Ultima_Mov', 'Qtd_Movs_3M']
    
    # Calcular média mensal
    consumo['Media_Mensal'] = consumo['Consumo_3M'] / meses
    
    return consumo, data_inicio, hoje


# ============================================================
# CONSOLIDAR HISTÓRICO -> VISÃO POR ITEM
# ============================================================

def consolidar_estoque(df_historico):
    """
    Consolida o histórico de movimentações em uma visão por item.
    Pega o ÚLTIMO lançamento de cada item para ter o saldo atual.
    Soma todas as entradas e saídas do período.
    """
    secao("CONSOLIDANDO HISTÓRICO DE MOVIMENTAÇÕES", "🔄")
    
    if 'Item' not in df_historico.columns:
        print("    ❌ Coluna 'Item' não encontrada!")
        return pd.DataFrame(), pd.DataFrame()
    
    # Adicionar índice de linha original
    df_historico['_linha_original'] = range(len(df_historico))
    
    # Converter datas
    df_historico['_data_mov'] = df_historico['Data'].apply(converter_data)
    if 'Alterado Em' in df_historico.columns:
        df_historico['_data_alt'] = df_historico['Alterado Em'].apply(converter_data)
    else:
        df_historico['_data_alt'] = None
    
    # Contagem de movimentações por item
    movimentacoes = df_historico.groupby('Item').size().reset_index(name='Qtd_Movimentacoes')
    
    # Para cada item, pegar o ÚLTIMO registro
    idx_ultimo = df_historico.groupby('Item')['_linha_original'].idxmax()
    df_ultimo = df_historico.loc[idx_ultimo].copy()
    
    # Para cada item, pegar o PRIMEIRO registro
    idx_primeiro = df_historico.groupby('Item')['_linha_original'].idxmin()
    df_primeiro = df_historico.loc[idx_primeiro][['Item', '_data_mov']].copy()
    df_primeiro.columns = ['Item', '_primeira_mov']
    
    # Somar TODAS as entradas e saídas de cada item
    totais = df_historico.groupby('Item').agg({
        'Entrada': 'sum',
        'Saída': 'sum'
    }).reset_index()
    totais.columns = ['Item', 'Total_Entradas', 'Total_Saidas']
    
    # Calcular consumo dos últimos 3 meses
    print(f"    ⏳ Calculando consumo dos últimos {MESES_ANALISE_CONSUMO} meses...")
    consumo_3m, data_inicio, data_fim = calcular_consumo_periodo(df_historico, MESES_ANALISE_CONSUMO)
    
    # Juntar tudo
    df_consolidado = df_ultimo.merge(movimentacoes, on='Item', how='left')
    df_consolidado = df_consolidado.merge(totais, on='Item', how='left')
    df_consolidado = df_consolidado.merge(df_primeiro, on='Item', how='left')
    df_consolidado = df_consolidado.merge(consumo_3m, on='Item', how='left')
    
    # Preencher NaN com 0 para itens sem movimentação nos últimos 3 meses
    df_consolidado['Consumo_3M'] = df_consolidado['Consumo_3M'].fillna(0)
    df_consolidado['Entrada_3M'] = df_consolidado['Entrada_3M'].fillna(0)
    df_consolidado['Media_Mensal'] = df_consolidado['Media_Mensal'].fillna(0)
    df_consolidado['Qtd_Movs_3M'] = df_consolidado['Qtd_Movs_3M'].fillna(0)
    
    # Calcular cobertura de estoque (em meses)
    df_consolidado['Cobertura_Meses'] = df_consolidado.apply(
        lambda row: row['Saldo'] / row['Media_Mensal'] if row['Media_Mensal'] > 0 else 999,
        axis=1
    )
    
    # Calcular dias desde última movimentação
    hoje = datetime.now()
    df_consolidado['Dias_Sem_Mov'] = df_consolidado['_data_mov'].apply(
        lambda x: (hoje - x).days if x else 9999
    )
    
    # Limpar colunas auxiliares
    df_consolidado = df_consolidado.drop(columns=['_linha_original'], errors='ignore')
    
    total_itens = len(df_consolidado)
    total_movs = len(df_historico)
    
    print(f"    📦 {total_itens} itens únicos encontrados")
    print(f"    📝 {total_movs} movimentações no histórico")
    print(f"    📊 Média de {total_movs/total_itens:.1f} movimentações por item")
    print(f"    📅 Período de consumo: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
    
    return df_consolidado, consumo_3m


# ============================================================
# ANÁLISE DE CONSUMO DOS ÚLTIMOS 3 MESES
# ============================================================

def analisar_consumo_3_meses(df):
    """Análise detalhada do consumo dos últimos 3 meses"""
    secao(f"ANÁLISE DE CONSUMO - ÚLTIMOS {MESES_ANALISE_CONSUMO} MESES", "📈")
    
    # Filtrar itens com consumo no período
    df_consumo = df[df['Consumo_3M'] > 0].copy()
    df_sem_consumo = df[(df['Consumo_3M'] == 0) & (df['Saldo'] > 0)].copy()
    
    # Resumo geral
    total_consumo = df['Consumo_3M'].sum()
    total_entrada = df['Entrada_3M'].sum()
    itens_com_consumo = len(df_consumo)
    itens_sem_consumo = len(df_sem_consumo)
    
    print(f"""
    📊 RESUMO DO PERÍODO ({MESES_ANALISE_CONSUMO} MESES)
    {'─'*50}
    Total consumido (saídas)........: {total_consumo:>12,.0f} un
    Total recebido (entradas).......: {total_entrada:>12,.0f} un
    Balanço do período..............: {total_entrada - total_consumo:>+12,.0f} un
    
    Itens com consumo...............: {itens_com_consumo:>12}
    Itens sem consumo (com saldo)...: {itens_sem_consumo:>12}
    """)
    
    # TOP 20 maiores consumos
    subsecao("🔥 TOP 20 - MAIORES CONSUMOS (3 meses)")
    top_consumo = df_consumo.sort_values('Consumo_3M', ascending=False).head(20)
    if not top_consumo.empty:
        tabela_header("Item", "Consumo 3M", "Média/Mês")
        for _, row in top_consumo.iterrows():
            linha_item(row['Item'], f"{row['Consumo_3M']:.0f}", f"{row['Media_Mensal']:.1f}/mês")
    
    # Itens com alto consumo mas estoque baixo (CRÍTICO)
    subsecao("🚨 CRÍTICO: Alto consumo + Estoque baixo")
    criticos = df_consumo[
        (df_consumo['Consumo_3M'] > 0) & 
        (df_consumo['Saldo'] < df_consumo['Media_Mensal'] * 2)  # Menos de 2 meses de cobertura
    ].sort_values('Cobertura_Meses')
    
    if not criticos.empty:
        print(f"    ⚠️  {len(criticos)} itens com menos de 2 meses de cobertura!\n")
        tabela_header("Item", "Saldo", "Cobertura")
        for _, row in criticos.head(15).iterrows():
            cobertura = f"{row['Cobertura_Meses']:.1f} meses" if row['Cobertura_Meses'] < 999 else "N/A"
            linha_item(row['Item'], f"{row['Saldo']:.0f}", cobertura)
    else:
        print("    ✅ Nenhum item crítico!")
    
    # Cobertura de estoque
    subsecao("📦 COBERTURA DE ESTOQUE (baseado no consumo médio)")
    
    # Cobertura < 1 mês
    cob_critica = df_consumo[(df_consumo['Cobertura_Meses'] < 1) & (df_consumo['Saldo'] > 0)]
    cob_baixa = df_consumo[(df_consumo['Cobertura_Meses'] >= 1) & (df_consumo['Cobertura_Meses'] < 2)]
    cob_normal = df_consumo[(df_consumo['Cobertura_Meses'] >= 2) & (df_consumo['Cobertura_Meses'] < 6)]
    cob_alta = df_consumo[(df_consumo['Cobertura_Meses'] >= 6) & (df_consumo['Cobertura_Meses'] < 999)]
    
    print(f"""
    🔴 Cobertura < 1 mês (crítico)....: {len(cob_critica):>6} itens
    🟡 Cobertura 1-2 meses (baixa)....: {len(cob_baixa):>6} itens
    🟢 Cobertura 2-6 meses (normal)...: {len(cob_normal):>6} itens
    🔵 Cobertura > 6 meses (alta).....: {len(cob_alta):>6} itens
    """)
    
    # Itens com cobertura crítica
    if not cob_critica.empty:
        print("    Itens com cobertura < 1 mês:")
        separador()
        for _, row in cob_critica.sort_values('Cobertura_Meses').head(10).iterrows():
            dias = row['Cobertura_Meses'] * 30
            linha_item(row['Item'], f"{row['Saldo']:.0f}", f"~{dias:.0f} dias")
    
    # Itens SEM consumo nos últimos 3 meses mas com saldo
    subsecao("😴 ITENS SEM CONSUMO NOS ÚLTIMOS 3 MESES (com saldo)")
    if not df_sem_consumo.empty:
        df_sem_consumo = df_sem_consumo.sort_values('Saldo', ascending=False)
        valor_parado = df_sem_consumo['Saldo'].sum()
        print(f"    ⚠️  {len(df_sem_consumo)} itens sem giro!")
        print(f"    💰 Total parado: {valor_parado:,.0f} unidades\n")
        tabela_header("Item", "Saldo Parado", "Dias s/ Mov")
        for _, row in df_sem_consumo.head(15).iterrows():
            dias = f"{row['Dias_Sem_Mov']:.0f}d" if row['Dias_Sem_Mov'] < 9999 else "N/A"
            linha_item(row['Item'], f"{row['Saldo']:.0f}", dias)
    else:
        print("    ✅ Todos os itens com saldo tiveram consumo!")
    
    # Tendência: Consumo vs Entrada
    subsecao("📊 BALANÇO: ENTRADA vs CONSUMO (3 meses)")
    df_balanco = df_consumo.copy()
    df_balanco['Balanco_3M'] = df_balanco['Entrada_3M'] - df_balanco['Consumo_3M']
    
    # Itens onde saiu mais do que entrou
    deficit = df_balanco[df_balanco['Balanco_3M'] < 0].sort_values('Balanco_3M')
    if not deficit.empty:
        print(f"    📉 {len(deficit)} itens com mais saída que entrada:\n")
        tabela_header("Item", "Entrada", "Saída → Bal")
        for _, row in deficit.head(10).iterrows():
            linha_item(row['Item'], f"+{row['Entrada_3M']:.0f}", f"-{row['Consumo_3M']:.0f} → {row['Balanco_3M']:+.0f}")
    
    return df_consumo


# ============================================================
# ANÁLISE DE DUPLICADOS (ABA ÍNDICE_ITENS)
# ============================================================

def analisar_duplicados_indice(df_indice):
    """Encontra itens duplicados ou muito similares no índice"""
    secao("ANÁLISE DE DUPLICADOS - ÍNDICE_ITENS", "🔎")
    
    if df_indice.empty:
        print("    Aba ÍNDICE_ITENS vazia ou não encontrada")
        return pd.DataFrame()
    
    print(f"    Colunas encontradas: {list(df_indice.columns)}")
    
    col_item = None
    for possivel in ['Item', 'ITEM', 'item', 'Descrição', 'DESCRIÇÃO', 'Produto', 'PRODUTO', 'Nome', 'NOME', 'Material', 'MATERIAL']:
        if possivel in df_indice.columns:
            col_item = possivel
            break
    
    if col_item is None:
        for col in df_indice.columns:
            if str(col).strip() != '':
                col_item = col
                break
    
    if col_item is None:
        col_item = df_indice.columns[0]
    
    print(f"    Usando coluna: '{col_item}'")
    print(f"    Total de itens no índice: {len(df_indice)}\n")
    
    itens = df_indice[col_item].astype(str).values.tolist()
    duplicados = []
    
    # 1. DUPLICADOS EXATOS
    subsecao("DUPLICADOS EXATOS (mesmo nome)")
    itens_normalizados = [normalizar_texto(i) for i in itens]
    vistos = {}
    exatos = []
    
    for i, (original, normalizado) in enumerate(zip(itens, itens_normalizados)):
        if normalizado in vistos and normalizado.strip() != '':
            exatos.append({
                'Item 1': vistos[normalizado]['original'],
                'Linha 1': vistos[normalizado]['linha'],
                'Item 2': original,
                'Linha 2': i + 2,
                'Tipo': 'EXATO'
            })
        else:
            vistos[normalizado] = {'original': original, 'linha': i + 2}
    
    if exatos:
        print(f"    ⚠️  {len(exatos)} DUPLICADOS EXATOS ENCONTRADOS!\n")
        separador()
        for dup in exatos[:15]:
            print(f"    Linha {dup['Linha 1']:>4}: {str(dup['Item 1'])[:40]}")
            print(f"    Linha {dup['Linha 2']:>4}: {str(dup['Item 2'])[:40]}")
            print(f"    {'─'*50}")
        if len(exatos) > 15:
            print(f"\n    ... e mais {len(exatos)-15} duplicados")
        duplicados.extend(exatos)
    else:
        print("    ✅ Nenhum duplicado exato encontrado")
    
    # 2. SIMILARES
    subsecao("ITENS MUITO SIMILARES (possíveis duplicados)")
    similares = []
    itens_unicos = list(set([i for i in itens_normalizados if i.strip() != '']))
    
    if len(itens_unicos) > 500:
        print(f"    ⚠️  Muitos itens ({len(itens_unicos)}). Analisando primeiros 500...")
        itens_unicos = itens_unicos[:500]
    else:
        print(f"    Comparando {len(itens_unicos)} itens únicos...")
    
    for i in range(len(itens_unicos)):
        for j in range(i + 1, len(itens_unicos)):
            if abs(len(itens_unicos[i]) - len(itens_unicos[j])) > 5:
                continue
            
            sim = similaridade(itens_unicos[i], itens_unicos[j])
            if sim >= SIMILARIDADE_DUPLICADO and sim < 1.0:
                try:
                    idx1 = itens_normalizados.index(itens_unicos[i])
                    idx2 = itens_normalizados.index(itens_unicos[j])
                    similares.append({
                        'Item 1': itens[idx1],
                        'Linha 1': idx1 + 2,
                        'Item 2': itens[idx2],
                        'Linha 2': idx2 + 2,
                        'Similaridade': f"{sim*100:.0f}%",
                        'Tipo': 'SIMILAR'
                    })
                except:
                    pass
    
    if similares:
        similares.sort(key=lambda x: x['Similaridade'], reverse=True)
        print(f"\n    ⚠️  {len(similares)} PARES SIMILARES ENCONTRADOS!\n")
        separador()
        for sim in similares[:20]:
            print(f"    [{sim['Similaridade']}] Linhas {sim['Linha 1']} e {sim['Linha 2']}:")
            print(f"      → {str(sim['Item 1'])[:45]}")
            print(f"      → {str(sim['Item 2'])[:45]}")
            print()
        if len(similares) > 20:
            print(f"    ... e mais {len(similares)-20} pares similares")
        duplicados.extend(similares)
    else:
        print("    ✅ Nenhum item similar encontrado")
    
    # 3. ESPAÇOS EXTRAS
    subsecao("ITENS COM ESPAÇOS EXTRAS")
    espacos = []
    for i, item in enumerate(itens):
        item_str = str(item)
        if item_str.strip() != '' and (item_str != item_str.strip() or '  ' in item_str):
            espacos.append({
                'Item': item,
                'Linha': i + 2,
                'Problema': 'espaço início/fim' if item_str != item_str.strip() else 'espaços duplos'
            })
    
    if espacos:
        print(f"\n    ⚠️  {len(espacos)} itens com problemas de espaço!\n")
        separador()
        for esp in espacos[:15]:
            print(f"    Linha {esp['Linha']:>4}: '{str(esp['Item'])[:40]}' ({esp['Problema']})")
        if len(espacos) > 15:
            print(f"\n    ... e mais {len(espacos)-15} itens")
    else:
        print("    ✅ Nenhum problema de espaços")
    
    return pd.DataFrame(duplicados) if duplicados else pd.DataFrame()


# ============================================================
# COMPARAR ESTOQUE vs ÍNDICE
# ============================================================

def comparar_estoque_indice(df_consolidado, df_indice):
    """Compara os itens do estoque consolidado com o índice"""
    secao("COMPARAÇÃO: ESTOQUE vs ÍNDICE", "🔗")
    
    if df_indice.empty:
        print("    Aba ÍNDICE vazia, pulando comparação")
        return
    
    col_item_indice = None
    for possivel in ['Item', 'ITEM', 'item', 'Descrição', 'Produto', 'Nome']:
        if possivel in df_indice.columns:
            col_item_indice = possivel
            break
    if col_item_indice is None:
        col_item_indice = df_indice.columns[0]
    
    col_saldo_indice = None
    for possivel in ['Saldo', 'SALDO', 'Estoque', 'ESTOQUE', 'Qtd', 'Quantidade']:
        if possivel in df_indice.columns:
            col_saldo_indice = possivel
            break
    
    itens_estoque = set(df_consolidado['Item'].astype(str).str.strip().str.lower())
    itens_indice = set(df_indice[col_item_indice].astype(str).str.strip().str.lower())
    
    so_estoque = itens_estoque - itens_indice
    so_indice = itens_indice - itens_estoque
    
    subsecao(f"ITENS NO ESTOQUE MAS NÃO NO ÍNDICE: {len(so_estoque)}")
    if so_estoque:
        for item in list(so_estoque)[:10]:
            print(f"    • {item}")
        if len(so_estoque) > 10:
            print(f"    ... e mais {len(so_estoque)-10}")
    else:
        print("    ✅ Todos os itens do estoque estão no índice")
    
    subsecao(f"ITENS NO ÍNDICE MAS SEM MOVIMENTAÇÃO: {len(so_indice)}")
    if so_indice:
        for item in list(so_indice)[:10]:
            print(f"    • {item}")
        if len(so_indice) > 10:
            print(f"    ... e mais {len(so_indice)-10}")
    else:
        print("    ✅ Todos os itens do índice têm movimentação")
    
    if col_saldo_indice:
        subsecao("DIVERGÊNCIA DE SALDOS (Estoque vs Índice)")
        
        df_est = df_consolidado[['Item', 'Saldo']].copy()
        df_est['Item_Norm'] = df_est['Item'].astype(str).str.strip().str.lower()
        
        df_idx = df_indice[[col_item_indice, col_saldo_indice]].copy()
        df_idx.columns = ['Item_Indice', 'Saldo_Indice']
        df_idx['Item_Norm'] = df_idx['Item_Indice'].astype(str).str.strip().str.lower()
        
        df_idx['Saldo_Indice'] = df_idx['Saldo_Indice'].astype(str).str.replace('.', '', regex=False)
        df_idx['Saldo_Indice'] = df_idx['Saldo_Indice'].str.replace(',', '.', regex=False)
        df_idx['Saldo_Indice'] = pd.to_numeric(df_idx['Saldo_Indice'], errors='coerce').fillna(0)
        
        df_comp = df_est.merge(df_idx, on='Item_Norm', how='inner')
        df_comp['Diferenca'] = df_comp['Saldo'] - df_comp['Saldo_Indice']
        
        divergentes = df_comp[abs(df_comp['Diferenca']) > 0.01]
        
        if not divergentes.empty:
            print(f"    ⚠️  {len(divergentes)} itens com saldo diferente!\n")
            tabela_header("Item", "Estoque", "Índice → Dif")
            for _, row in divergentes.head(15).iterrows():
                linha_item(row['Item'], f"{row['Saldo']:.0f}", f"{row['Saldo_Indice']:.0f} → {row['Diferenca']:+.0f}")
        else:
            print("    ✅ Saldos conferem!")


# ============================================================
# ANÁLISES DE ESTOQUE
# ============================================================

def analisar_niveis_estoque(df):
    """Análise de níveis: negativo, zerado, baixo"""
    secao("NÍVEIS DE ESTOQUE (Saldo Atual)", "📊")
    
    # NEGATIVOS
    subsecao("🚨 SALDO NEGATIVO - REPOSIÇÃO URGENTE")
    negativos = df[df['Saldo'] < 0].sort_values('Saldo')
    if not negativos.empty:
        print(f"    {len(negativos)} itens com saldo negativo!\n")
        tabela_header("Item", "Saldo", "Consumo 3M")
        for _, row in negativos.head(20).iterrows():
            consumo = f"{row['Consumo_3M']:.0f}" if row['Consumo_3M'] > 0 else "0"
            linha_item(row['Item'], f"{row['Saldo']:.0f}", consumo)
        if len(negativos) > 20:
            print(f"\n    ... e mais {len(negativos)-20} itens")
    else:
        print("    ✅ Nenhum item negativo!")
    
    # ZERADOS
    subsecao("⚠️  SALDO ZERADO")
    zerados = df[df['Saldo'] == 0]
    if not zerados.empty:
        print(f"    {len(zerados)} itens zerados!\n")
        tabela_header("Item", "Consumo 3M", "Movimentações")
        for _, row in zerados.head(15).iterrows():
            linha_item(row['Item'], f"{row['Consumo_3M']:.0f}", f"{row['Qtd_Movimentacoes']:.0f} movs")
        if len(zerados) > 15:
            print(f"\n    ... e mais {len(zerados)-15} itens")
    else:
        print("    ✅ Nenhum item zerado!")
    
    # ABAIXO DO LIMITE
    subsecao(f"📉 ESTOQUE BAIXO (< {LIMITE_ESTOQUE_BAIXO} unidades)")
    baixo = df[(df['Saldo'] > 0) & (df['Saldo'] < LIMITE_ESTOQUE_BAIXO)].sort_values('Saldo')
    if not baixo.empty:
        print(f"    {len(baixo)} itens com estoque baixo!\n")
        tabela_header("Item", "Saldo", "Cobertura")
        for _, row in baixo.head(20).iterrows():
            cob = f"{row['Cobertura_Meses']:.1f}m" if row['Cobertura_Meses'] < 999 else "N/A"
            linha_item(row['Item'], f"{row['Saldo']:.1f}", cob)
        if len(baixo) > 20:
            print(f"\n    ... e mais {len(baixo)-20} itens")
    else:
        print("    ✅ Todos acima do limite!")
    
    return negativos, zerados, baixo


def analisar_movimentacao_temporal(df):
    """Análise de itens parados baseado na última movimentação"""
    secao("ANÁLISE TEMPORAL - ITENS PARADOS", "📅")
    
    df_valido = df[(df['Saldo'] > 0) & (df['Dias_Sem_Mov'] < 9999)].copy()
    
    # Parados há mais de 30 dias
    subsecao(f"PARADOS HÁ MAIS DE {DIAS_SEM_MOVIMENTO} DIAS")
    parados_30 = df_valido[df_valido['Dias_Sem_Mov'] > DIAS_SEM_MOVIMENTO].sort_values('Dias_Sem_Mov', ascending=False)
    
    if not parados_30.empty:
        valor_parado = parados_30['Saldo'].sum()
        print(f"    ⚠️  {len(parados_30)} itens parados = {valor_parado:,.0f} unidades\n")
        tabela_header("Item", "Dias Parado", "Saldo")
        for _, row in parados_30.head(15).iterrows():
            linha_item(row['Item'], f"{row['Dias_Sem_Mov']:.0f} dias", f"{row['Saldo']:.0f}")
        if len(parados_30) > 15:
            print(f"\n    ... e mais {len(parados_30)-15} itens")
    else:
        print("    ✅ Todos os itens tiveram movimentação recente!")
    
    # Parados há mais de 60 dias
    subsecao(f"⚠️  ATENÇÃO: PARADOS HÁ MAIS DE {DIAS_ATENCAO} DIAS")
    parados_60 = df_valido[df_valido['Dias_Sem_Mov'] > DIAS_ATENCAO].sort_values('Dias_Sem_Mov', ascending=False)
    if not parados_60.empty:
        print(f"    {len(parados_60)} itens precisam de atenção!")
        tabela_header("Item", "Dias Parado", "Saldo")
        for _, row in parados_60.head(10).iterrows():
            linha_item(row['Item'], f"{row['Dias_Sem_Mov']:.0f} dias", f"{row['Saldo']:.0f}")
    else:
        print("    ✅ OK!")
    
    # Obsoletos
    subsecao(f"🚨 POSSÍVEL OBSOLESCÊNCIA (> {DIAS_OBSOLETO} DIAS)")
    obsoletos = df_valido[df_valido['Dias_Sem_Mov'] > DIAS_OBSOLETO].sort_values('Dias_Sem_Mov', ascending=False)
    if not obsoletos.empty:
        valor_obsoleto = obsoletos['Saldo'].sum()
        print(f"    🚨 {len(obsoletos)} itens possivelmente obsoletos!")
        print(f"    💰 Total parado: {valor_obsoleto:,.0f} unidades\n")
        tabela_header("Item", "Dias Parado", "Saldo")
        for _, row in obsoletos.head(10).iterrows():
            linha_item(row['Item'], f"{row['Dias_Sem_Mov']:.0f} dias", f"{row['Saldo']:.0f}")
    else:
        print("    ✅ Nenhum item obsoleto!")
    
    return parados_30, obsoletos


def analisar_movimentacao_entrada_saida(df):
    """Análise de padrões de entrada e saída"""
    secao("PADRÕES DE MOVIMENTAÇÃO", "🔄")
    
    # Sem nenhuma movimentação
    subsecao("ITENS SEM MOVIMENTAÇÃO NO PERÍODO")
    parados_total = df[(df['Total_Entradas'] == 0) & (df['Total_Saidas'] == 0) & (df['Saldo'] > 0)]
    if not parados_total.empty:
        parados_total = parados_total.sort_values('Saldo', ascending=False)
        print(f"    {len(parados_total)} itens sem movimentação!\n")
        tabela_header("Item", "Saldo Parado", "Dias")
        for _, row in parados_total.head(15).iterrows():
            dias = f"{row['Dias_Sem_Mov']:.0f}d" if row['Dias_Sem_Mov'] < 9999 else "N/A"
            linha_item(row['Item'], f"{row['Saldo']:.0f}", dias)
    else:
        print("    ✅ Todos tiveram alguma movimentação!")
    
    # Só entrada
    subsecao("SÓ ENTRADA (recebeu mas não consumiu)")
    so_entrada = df[(df['Total_Entradas'] > 0) & (df['Total_Saidas'] == 0) & (df['Saldo'] > 0)]
    if not so_entrada.empty:
        so_entrada = so_entrada.sort_values('Total_Entradas', ascending=False)
        print(f"    {len(so_entrada)} itens!\n")
        tabela_header("Item", "Total Entrada", "Saldo Atual")
        for _, row in so_entrada.head(10).iterrows():
            linha_item(row['Item'], f"+{row['Total_Entradas']:.0f}", f"{row['Saldo']:.0f}")
    else:
        print("    ✅ OK!")
    
    # Só saída
    subsecao("SÓ SAÍDA (consumindo sem reposição)")
    so_saida = df[(df['Total_Entradas'] == 0) & (df['Total_Saidas'] > 0)]
    if not so_saida.empty:
        so_saida = so_saida.sort_values('Saldo')
        criticos = so_saida[so_saida['Saldo'] < LIMITE_ESTOQUE_BAIXO]
        print(f"    {len(so_saida)} itens só com saída")
        if not criticos.empty:
            print(f"    🚨 {len(criticos)} com saldo crítico!\n")
            tabela_header("Item", "Total Saída", "Saldo Atual")
            for _, row in criticos.head(10).iterrows():
                linha_item(row['Item'], f"-{row['Total_Saidas']:.0f}", f"{row['Saldo']:.0f}")
    else:
        print("    ✅ OK!")
    
    return parados_total, so_entrada, so_saida


def analisar_por_grupo(df):
    """Análise por grupo"""
    secao("ANÁLISE POR GRUPO", "📁")
    
    if 'Grupo' not in df.columns:
        print("    Coluna 'Grupo' não disponível")
        return
    
    df['Grupo'] = df['Grupo'].astype(str).replace('', 'SEM GRUPO').replace('nan', 'SEM GRUPO')
    
    grupos = df.groupby('Grupo').agg({
        'Item': 'count',
        'Saldo': 'sum',
        'Consumo_3M': 'sum'
    }).rename(columns={'Item': 'Qtd_Itens'})
    
    grupos = grupos.sort_values('Consumo_3M', ascending=False)
    
    print(f"    {len(grupos)} grupos encontrados\n")
    tabela_header("Grupo", "Itens", "Consumo 3M")
    for grupo, row in grupos.head(15).iterrows():
        linha_item(grupo, f"{row['Qtd_Itens']:.0f}", f"{row['Consumo_3M']:,.0f}")
    
    # Grupos com problemas
    subsecao("GRUPOS COM ITENS NEGATIVOS")
    tem_problema = False
    for grupo in df['Grupo'].unique():
        negativos_grupo = df[(df['Grupo'] == grupo) & (df['Saldo'] < 0)]
        if not negativos_grupo.empty:
            print(f"    {grupo}: {len(negativos_grupo)} itens negativos")
            tem_problema = True
    
    if not tem_problema:
        print("    ✅ Nenhum grupo com itens negativos")


def analisar_divergencias(df):
    """Auditoria: divergências"""
    secao("AUDITORIA - DIVERGÊNCIAS MATEMÁTICAS", "🔍")
    
    df['Calculado'] = df['Saldo Anterior'] + df['Entrada'] - df['Saída']
    df['Diferenca'] = df['Saldo'] - df['Calculado']
    
    furos = df[abs(df['Diferenca']) > 0.01].copy()
    
    if furos.empty:
        print("    ✅ ESTOQUE ÍNTEGRO!")
        return furos
    
    furos = furos.sort_values('Diferenca', key=abs, ascending=False)
    furos_pos = furos[furos['Diferenca'] > 0]
    furos_neg = furos[furos['Diferenca'] < 0]
    
    print(f"    ⚠️  {len(furos)} DIVERGÊNCIAS!")
    print(f"    📈 {len(furos_pos)} com SOBRA")
    print(f"    📉 {len(furos_neg)} com FALTA")
    print(f"    💰 Impacto: {furos['Diferenca'].sum():+,.0f} un\n")
    
    if not furos_neg.empty:
        subsecao("FALTAS")
        tabela_header("Item", "Esperado", "Real → Dif")
        for _, row in furos_neg.head(10).iterrows():
            linha_item(row['Item'], f"{row['Calculado']:.0f}", f"{row['Saldo']:.0f} → {row['Diferenca']:+.0f}")
    
    if not furos_pos.empty:
        subsecao("SOBRAS")
        tabela_header("Item", "Esperado", "Real → Dif")
        for _, row in furos_pos.head(10).iterrows():
            linha_item(row['Item'], f"{row['Calculado']:.0f}", f"{row['Saldo']:.0f} → {row['Diferenca']:+.0f}")
    
    return furos


def analisar_curva_abc(df):
    """Curva ABC"""
    secao("CURVA ABC (POR CONSUMO 3 MESES)", "📊")
    
    df_abc = df[df['Consumo_3M'] > 0].copy()
    if df_abc.empty:
        print("    Sem dados de consumo")
        return None
    
    df_abc = df_abc.sort_values('Consumo_3M', ascending=False)
    total = df_abc['Consumo_3M'].sum()
    df_abc['%'] = df_abc['Consumo_3M'] / total * 100
    df_abc['%_Acum'] = df_abc['%'].cumsum()
    
    df_abc['Curva'] = df_abc['%_Acum'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )
    
    for curva in ['A', 'B', 'C']:
        itens = df_abc[df_abc['Curva'] == curva]
        print(f"    Curva {curva}: {len(itens):>4} itens ({len(itens)/len(df_abc)*100:>5.1f}%) = {itens['%'].sum():>5.1f}% consumo")
    
    subsecao("TOP 10 CURVA A")
    separador()
    for _, row in df_abc[df_abc['Curva'] == 'A'].head(10).iterrows():
        linha_item(row['Item'], f"{row['Consumo_3M']:.0f}", f"({row['%']:.1f}%)")
    
    return df_abc


def analisar_giro(df):
    """Giro de estoque"""
    secao("GIRO DE ESTOQUE", "🔃")
    
    df_giro = df[df['Saldo'] > 0].copy()
    df_giro['Giro'] = df_giro['Consumo_3M'] / df_giro['Saldo']
    
    # Alto giro
    alto = df_giro[df_giro['Giro'] > 1].sort_values('Giro', ascending=False)
    subsecao(f"ALTO GIRO (> 1x) - {len(alto)} itens")
    if not alto.empty:
        tabela_header("Item", "Giro", "Saldo")
        for _, row in alto.head(10).iterrows():
            linha_item(row['Item'], f"{row['Giro']:.2f}x", f"{row['Saldo']:.0f}")
    else:
        print("    Nenhum")
    
    # Baixo giro
    baixo = df_giro[(df_giro['Giro'] < 0.1) & (df_giro['Giro'] >= 0)].sort_values('Saldo', ascending=False)
    subsecao(f"BAIXÍSSIMO GIRO (< 0.1x) - {len(baixo)} itens")
    if not baixo.empty:
        tabela_header("Item", "Giro", "Saldo Parado")
        for _, row in baixo.head(10).iterrows():
            linha_item(row['Item'], f"{row['Giro']:.3f}x", f"{row['Saldo']:.0f}")
    else:
        print("    ✅ OK")
    
    return df_giro


def gerar_resumo_executivo(df, negativos, zerados, baixo, furos, parados, duplicados):
    """Resumo executivo"""
    titulo("RESUMO EXECUTIVO")
    
    total = len(df)
    
    qtd_negativos = len(negativos) if not negativos.empty else 0
    qtd_zerados = len(zerados) if not zerados.empty else 0
    qtd_baixo = len(baixo) if not baixo.empty else 0
    qtd_furos = len(furos) if not furos.empty else 0
    qtd_parados = len(parados) if not parados.empty else 0
    qtd_duplicados = len(duplicados) if not duplicados.empty else 0
    
    # Cobertura crítica
    qtd_cobertura_critica = len(df[(df['Cobertura_Meses'] < 1) & (df['Saldo'] > 0) & (df['Consumo_3M'] > 0)])
    
    print(f"""
    📦 VISÃO GERAL (CONSOLIDADO)
    {'─'*55}
    Total de ITENS ÚNICOS...........: {total:>10}
    Total em estoque................: {df['Saldo'].sum():>10,.0f} un
    Consumo últimos {MESES_ANALISE_CONSUMO} meses........: {df['Consumo_3M'].sum():>10,.0f} un
    Entradas últimos {MESES_ANALISE_CONSUMO} meses.......: {df['Entrada_3M'].sum():>10,.0f} un
    
    🚨 INDICADORES CRÍTICOS
    {'─'*55}
    Itens NEGATIVOS.................: {qtd_negativos:>10} {'🔴' if qtd_negativos > 0 else '🟢'}
    Itens ZERADOS...................: {qtd_zerados:>10} {'🟡' if qtd_zerados > 0 else '🟢'}
    Estoque BAIXO (< {LIMITE_ESTOQUE_BAIXO})............: {qtd_baixo:>10} {'🟡' if qtd_baixo > 0 else '🟢'}
    COBERTURA < 1 mês...............: {qtd_cobertura_critica:>10} {'🔴' if qtd_cobertura_critica > 0 else '🟢'}
    DIVERGÊNCIAS matemáticas........: {qtd_furos:>10} {'🔴' if qtd_furos > 0 else '🟢'}
    Itens PARADOS (> {DIAS_SEM_MOVIMENTO} dias)........: {qtd_parados:>10} {'🟡' if qtd_parados > 0 else '🟢'}
    DUPLICADOS no índice............: {qtd_duplicados:>10} {'🟡' if qtd_duplicados > 0 else '🟢'}
    
    📊 SAÚDE DO ESTOQUE
    {'─'*55}
    % Problemáticos.................: {100*(qtd_negativos+qtd_zerados)/total:>9.1f}%
    % Saudável......................: {100*(total-qtd_negativos-qtd_zerados)/total:>9.1f}%
    Acuracidade.....................: {100*(total-qtd_furos)/total:>9.1f}%
    """)
    
    # Ações
    secao("PLANO DE AÇÃO RECOMENDADO", "✅")
    
    acoes = []
    if qtd_negativos > 0:
        acoes.append(("URGENTE", f"Repor {qtd_negativos} itens com saldo negativo"))
    if qtd_cobertura_critica > 0:
        acoes.append(("URGENTE", f"Avaliar {qtd_cobertura_critica} itens com cobertura < 1 mês"))
    if qtd_furos > 0:
        acoes.append(("URGENTE", f"Auditar {qtd_furos} divergências matemáticas"))
    if qtd_duplicados > 0:
        acoes.append(("IMPORTANTE", f"Corrigir {qtd_duplicados} possíveis duplicados"))
    if qtd_zerados > 0:
        acoes.append(("ATENÇÃO", f"Avaliar {qtd_zerados} itens zerados"))
    if qtd_parados > 0:
        acoes.append(("AVALIAR", f"Verificar {qtd_parados} itens sem movimentação"))
    if qtd_baixo > 0:
        acoes.append(("MONITORAR", f"Acompanhar {qtd_baixo} itens com estoque baixo"))
    
    if acoes:
        for i, (prioridade, acao) in enumerate(acoes, 1):
            print(f"    {i}. [{prioridade}] {acao}")
    else:
        print("    ✅ Estoque saudável!")


def exportar_relatorios(df, negativos, zerados, furos, parados, duplicados):
    """Exporta relatórios"""
    secao("EXPORTANDO RELATÓRIOS", "💾")
    
    try:
        arquivo = f"analise_estoque_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        # Selecionar colunas principais para exportação
        colunas_export = ['Item', 'Grupo', 'Saldo', 'Consumo_3M', 'Media_Mensal', 
                         'Cobertura_Meses', 'Dias_Sem_Mov', 'Total_Entradas', 'Total_Saidas',
                         'Qtd_Movimentacoes', 'Entrada_3M']
        colunas_export = [c for c in colunas_export if c in df.columns]
        
        with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
            df[colunas_export].to_excel(writer, sheet_name='Estoque Consolidado', index=False)
            
            if not negativos.empty:
                negativos[colunas_export].to_excel(writer, sheet_name='Negativos', index=False)
            if not zerados.empty:
                zerados[colunas_export].to_excel(writer, sheet_name='Zerados', index=False)
            if not furos.empty:
                cols_furos = colunas_export + ['Calculado', 'Diferenca']
                cols_furos = [c for c in cols_furos if c in furos.columns]
                furos[cols_furos].to_excel(writer, sheet_name='Divergencias', index=False)
            if not parados.empty:
                parados[colunas_export].to_excel(writer, sheet_name='Sem Movimento', index=False)
            if not duplicados.empty:
                duplicados.to_excel(writer, sheet_name='Duplicados', index=False)
            
            # Aba de cobertura crítica
            cobertura_critica = df[(df['Cobertura_Meses'] < 2) & (df['Saldo'] > 0) & (df['Consumo_3M'] > 0)]
            if not cobertura_critica.empty:
                cobertura_critica[colunas_export].sort_values('Cobertura_Meses').to_excel(
                    writer, sheet_name='Cobertura Critica', index=False
                )
        
        print(f"    ✅ Salvo: {arquivo}")
        
    except Exception as e:
        print(f"    ❌ Erro: {e}")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def rodar_gestao():
    try:
        titulo(f"ANÁLISE COMPLETA DE ESTOQUE - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # CONEXÃO
        print("\n⏳ Conectando ao Google Sheets...")
        ss = client.open(NOME_PLANILHA)
        
        # LER ABA ESTOQUE
        print("⏳ Carregando histórico de movimentações...")
        sheet_estoque = ss.worksheet(ABA_ESTOQUE)
        valores = sheet_estoque.get_values()
        
        if not valores:
            print("❌ Aba ESTOQUE vazia!")
            return
        
        headers = [h.strip() for h in valores[0]]
        headers = [h if h != "" else f"Col_{i}" for i, h in enumerate(headers)]
        df_historico = pd.DataFrame(valores[1:], columns=headers)
        print(f"✅ HISTÓRICO: {len(df_historico)} movimentações")
        
        # LER ABA ÍNDICE
        try:
            sheet_indice = ss.worksheet(ABA_INDICE)
            valores_indice = sheet_indice.get_values()
            if valores_indice:
                headers_indice = [h.strip() for h in valores_indice[0]]
                headers_indice = [h if h != "" else f"Col_{i}" for i, h in enumerate(headers_indice)]
                df_indice = pd.DataFrame(valores_indice[1:], columns=headers_indice)
            else:
                df_indice = pd.DataFrame()
            print(f"✅ ÍNDICE: {len(df_indice)} itens")
        except Exception as e:
            df_indice = pd.DataFrame()
            print(f"⚠️  Aba ÍNDICE não encontrada: {e}")
        
        # LIMPEZA NUMÉRICA
        cols_num = ['Saldo Anterior', 'Entrada', 'Saída', 'Saldo', 'Valor']
        for col in cols_num:
            if col in df_historico.columns:
                df_historico[col] = df_historico[col].astype(str).str.replace('.', '', regex=False)
                df_historico[col] = df_historico[col].str.replace(',', '.', regex=False).str.strip()
                df_historico[col] = pd.to_numeric(df_historico[col], errors='coerce').fillna(0)
        
        # ========== CONSOLIDAR ==========
        df, consumo_3m = consolidar_estoque(df_historico)
        
        if df.empty:
            print("❌ Erro ao consolidar!")
            return
        
        # ========== ANÁLISES ==========
        
        # 1. Duplicados
        duplicados = analisar_duplicados_indice(df_indice)
        
        # 2. Comparar Estoque vs Índice
        comparar_estoque_indice(df, df_indice)
        
        # 3. Níveis de Estoque
        negativos, zerados, baixo = analisar_niveis_estoque(df)
        
        # 4. ⭐ ANÁLISE DE CONSUMO 3 MESES (NOVO!)
        analisar_consumo_3_meses(df)
        
        # 5. Movimentação Temporal
        parados, obsoletos = analisar_movimentacao_temporal(df)
        
        # 6. Padrões Entrada/Saída
        analisar_movimentacao_entrada_saida(df)
        
        # 7. Por Grupo
        analisar_por_grupo(df)
        
        # 8. Divergências
        furos = analisar_divergencias(df)
        
        # 9. Curva ABC
        analisar_curva_abc(df)
        
        # 10. Giro
        analisar_giro(df)
        
        # RESUMO
        gerar_resumo_executivo(df, negativos, zerados, baixo, furos, parados, duplicados)
        
        # EXPORTAR
        exportar_relatorios(df, negativos, zerados, furos, parados, duplicados)
        
        titulo("ANÁLISE CONCLUÍDA!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    rodar_gestao()