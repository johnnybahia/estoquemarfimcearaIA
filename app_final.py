"""
Marfim IA - Sistema Inteligente de Estoque
API Flask completa com todas as funcionalidades
"""
from flask import Flask, request, jsonify, send_from_directory
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from groq import Groq
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# --- CONFIGURAÇÕES ---
CHAVE_GROQ = os.getenv("GROQ_API_KEY", "")  # Configure aqui ou via variável de ambiente
ARQUIVO_JSON = "credentials.json"
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"

# Cliente Groq (inicializa se tiver chave)
client_groq = None
if CHAVE_GROQ:
    client_groq = Groq(api_key=CHAVE_GROQ)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def conectar_google():
    """Conecta ao Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON, scope)
    return gspread.authorize(creds).open(NOME_PLANILHA)

def converter_para_numero(valor):
    """Converte valor brasileiro para float"""
    if valor is None or str(valor).strip() == "":
        return 0.0
    try:
        s = str(valor).strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

def encontrar_coluna(df, nomes_possiveis):
    """Encontra coluna por nomes possíveis (case insensitive)"""
    colunas_lower = {c.lower().strip(): c for c in df.columns}
    for nome in nomes_possiveis:
        if nome.lower() in colunas_lower:
            return colunas_lower[nome.lower()]
    return None

def carregar_dados_completos():
    """Carrega índice e histórico com métricas calculadas"""
    ss = conectar_google()

    # Índice de itens
    sheet_idx = ss.worksheet("ÍNDICE_ITENS")
    dados_idx = sheet_idx.get_all_values()

    if len(dados_idx) < 2:
        raise Exception("Planilha ÍNDICE_ITENS está vazia ou sem dados")

    df_idx = pd.DataFrame(dados_idx[1:], columns=dados_idx[0])
    print(f"[DEBUG] ÍNDICE_ITENS: {len(df_idx)} linhas, colunas: {list(df_idx.columns)}")

    # Encontrar coluna de Item
    col_item = encontrar_coluna(df_idx, ['Item', 'ITEM', 'item', 'Nome', 'NOME', 'Produto', 'PRODUTO'])
    if col_item and col_item != 'Item':
        df_idx['Item'] = df_idx[col_item]

    # Encontrar coluna de Saldo
    col_saldo = encontrar_coluna(df_idx, ['Saldo Atual', 'SALDO ATUAL', 'Saldo', 'SALDO', 'Estoque', 'ESTOQUE', 'Qtd', 'QTD', 'Quantidade'])
    if col_saldo:
        df_idx['Saldo'] = df_idx[col_saldo].apply(converter_para_numero)
    else:
        df_idx['Saldo'] = 0
        print(f"[AVISO] Coluna de saldo não encontrada. Colunas disponíveis: {list(df_idx.columns)}")

    # Histórico de movimentações
    sheet_hist = ss.worksheet("ESTOQUE")
    dados_hist = sheet_hist.get_all_values()

    if len(dados_hist) < 2:
        print("[AVISO] Planilha ESTOQUE está vazia, usando apenas índice")
        df_hist = pd.DataFrame(columns=['Item', 'Data', 'Entrada', 'Saída', 'Saldo'])
    else:
        df_hist = pd.DataFrame(dados_hist[1:], columns=dados_hist[0])
        print(f"[DEBUG] ESTOQUE: {len(df_hist)} linhas, colunas: {list(df_hist.columns)}")

    # Encontrar colunas no histórico
    col_hist_item = encontrar_coluna(df_hist, ['Item', 'ITEM', 'item', 'Nome', 'NOME', 'Produto', 'PRODUTO'])
    if col_hist_item and col_hist_item != 'Item':
        df_hist['Item'] = df_hist[col_hist_item]

    col_data = encontrar_coluna(df_hist, ['Data', 'DATA', 'data', 'Date', 'DATE'])
    col_entrada = encontrar_coluna(df_hist, ['Entrada', 'ENTRADA', 'entrada', 'Entradas', 'ENTRADAS', 'In', 'IN'])
    col_saida = encontrar_coluna(df_hist, ['Saída', 'SAÍDA', 'saida', 'SAIDA', 'Saídas', 'SAÍDAS', 'Out', 'OUT'])

    # Converter colunas numéricas
    for col_nome, col_real in [('Entrada', col_entrada), ('Saída', col_saida)]:
        if col_real:
            df_hist[col_nome] = df_hist[col_real].apply(converter_para_numero)
        elif col_nome not in df_hist.columns:
            df_hist[col_nome] = 0

    # Converter Data - usar método mais flexível
    if col_data and col_data in df_hist.columns:
        df_hist['Data_Original'] = df_hist[col_data]

        # Primeiro: tentar inferência automática com dayfirst=True (mais flexível)
        df_hist['Data'] = pd.to_datetime(df_hist[col_data], dayfirst=True, errors='coerce')
        datas_inferidas = df_hist['Data'].notna().sum()

        if datas_inferidas > 0:
            print(f"[DEBUG] Datas parseadas automaticamente: {datas_inferidas}")
        else:
            # Fallback: tentar formatos específicos
            formatos = [
                '%d/%m/%Y %H:%M:%S',  # 03/01/2022 00:00:00
                '%d/%m/%Y',           # 03/01/2022
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d-%m-%Y %H:%M:%S',
                '%d-%m-%Y',
            ]
            for fmt in formatos:
                df_hist['Data'] = pd.to_datetime(df_hist[col_data], format=fmt, errors='coerce')
                if df_hist['Data'].notna().sum() > 0:
                    print(f"[DEBUG] Formato de data detectado: {fmt}")
                    break

        # Debug: mostrar exemplo de data original vs parseada
        amostra = df_hist[df_hist['Data'].notna()].head(1)
        if not amostra.empty:
            print(f"[DEBUG] Exemplo: '{amostra['Data_Original'].iloc[0]}' -> {amostra['Data'].iloc[0]}")
    else:
        df_hist['Data'] = pd.NaT
        print(f"[AVISO] Coluna de data não encontrada")

    datas_validas = df_hist['Data'].notna().sum()
    print(f"[DEBUG] Datas válidas: {datas_validas} de {len(df_hist)}")

    # Calcular métricas
    hoje = datetime.now()
    data_30d = hoje - timedelta(days=30)
    data_60d = hoje - timedelta(days=60)
    data_90d = hoje - timedelta(days=90)

    # Normalizar nomes de itens para matching (remover espaços extras, uppercase)
    df_idx['Item_Norm'] = df_idx['Item'].str.strip().str.upper()
    df_hist['Item_Norm'] = df_hist['Item'].str.strip().str.upper()

    # Debug: verificar sobreposição de itens
    itens_idx = set(df_idx['Item_Norm'].unique())
    itens_hist = set(df_hist['Item_Norm'].unique())
    itens_comuns = itens_idx.intersection(itens_hist)
    print(f"[DEBUG] Itens únicos ÍNDICE: {len(itens_idx)}, ESTOQUE: {len(itens_hist)}, Comuns: {len(itens_comuns)}")

    # Consumo por período (apenas se houver datas válidas)
    if datas_validas > 0:
        consumo_30d = df_hist[df_hist['Data'] >= data_30d].groupby('Item_Norm')['Saída'].sum()
        consumo_60d = df_hist[df_hist['Data'] >= data_60d].groupby('Item_Norm')['Saída'].sum()
        consumo_90d = df_hist[df_hist['Data'] >= data_90d].groupby('Item_Norm')['Saída'].sum()
        print(f"[DEBUG] Registros últimos 30d: {(df_hist['Data'] >= data_30d).sum()}")
    else:
        # Se não há datas, usar todo o histórico
        print("[AVISO] Usando todo histórico (sem filtro de data)")
        consumo_30d = df_hist.groupby('Item_Norm')['Saída'].sum()
        consumo_60d = consumo_30d
        consumo_90d = consumo_30d

    df_idx['Consumo_30d'] = df_idx['Item_Norm'].map(consumo_30d).fillna(0)
    df_idx['Consumo_60d'] = df_idx['Item_Norm'].map(consumo_60d).fillna(0)
    df_idx['Consumo_90d'] = df_idx['Item_Norm'].map(consumo_90d).fillna(0)
    df_idx['Media_Diaria'] = df_idx['Consumo_30d'] / 30
    df_idx['Dias_Cobertura'] = df_idx.apply(
        lambda r: round(r['Saldo'] / r['Media_Diaria'], 1) if r['Media_Diaria'] > 0 else 999,
        axis=1
    )

    print(f"[DEBUG] Consumo total 30d: {df_idx['Consumo_30d'].sum():.0f}")
    print(f"[DEBUG] Itens com consumo: {(df_idx['Consumo_30d'] > 0).sum()}")

    return df_idx, df_hist

def consultar_ia(prompt, sistema="Você é um analista de estoque da Marfim Indústria Têxtil."):
    """Consulta a IA"""
    if not client_groq:
        return "⚠️ IA não configurada. Adicione CHAVE_GROQ no app_final.py"

    try:
        chat = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"Erro IA: {str(e)}"

# ============================================================
# ROTAS
# ============================================================

@app.route('/')
def index():
    """Página principal"""
    return send_from_directory('.', 'index.html')

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    """Retorna dados do dashboard"""
    try:
        df_idx, df_hist = carregar_dados_completos()

        total_itens = len(df_idx)
        itens_criticos = len(df_idx[df_idx['Dias_Cobertura'] < 15])
        itens_zerados = len(df_idx[df_idx['Saldo'] == 0])
        itens_negativos = len(df_idx[df_idx['Saldo'] < 0])
        consumo_total = df_idx['Consumo_30d'].sum()
        estoque_total = df_idx['Saldo'].sum()

        # Top consumo
        top_consumo = df_idx.nlargest(10, 'Consumo_30d')[['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']].to_dict('records')

        # Mais críticos
        criticos = df_idx[df_idx['Dias_Cobertura'] < 999].nsmallest(10, 'Dias_Cobertura')[['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']].to_dict('records')

        # Distribuição cobertura
        dist_cobertura = {
            'critico': len(df_idx[df_idx['Dias_Cobertura'] < 7]),
            'urgente': len(df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)]),
            'atencao': len(df_idx[(df_idx['Dias_Cobertura'] >= 15) & (df_idx['Dias_Cobertura'] < 30)]),
            'normal': len(df_idx[(df_idx['Dias_Cobertura'] >= 30) & (df_idx['Dias_Cobertura'] < 999)]),
        }

        return jsonify({
            'success': True,
            'kpis': {
                'total_itens': total_itens,
                'itens_criticos': itens_criticos,
                'itens_zerados': itens_zerados,
                'itens_negativos': itens_negativos,
                'consumo_30d': round(consumo_total, 0),
                'estoque_total': round(estoque_total, 0)
            },
            'top_consumo': top_consumo,
            'criticos': criticos,
            'distribuicao': dist_cobertura
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    """Busca itens por nome"""
    try:
        termo = request.json.get('item', '').upper()
        df_idx, _ = carregar_dados_completos()

        resultado = df_idx[df_idx['Item'].str.upper().str.contains(termo, na=False)]

        itens = resultado[['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']].head(50).to_dict('records')

        return jsonify({'success': True, 'itens': itens, 'total': len(resultado)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/item/<item_nome>', methods=['GET'])
def api_item_detalhe(item_nome):
    """Retorna detalhes de um item específico"""
    try:
        df_idx, df_hist = carregar_dados_completos()

        # Dados do item
        item_data = df_idx[df_idx['Item'].str.upper() == item_nome.upper()]
        if item_data.empty:
            return jsonify({'success': False, 'error': 'Item não encontrado'})

        item = item_data.iloc[0].to_dict()

        # Histórico
        historico = df_hist[df_hist['Item'].str.upper() == item_nome.upper()].tail(20)
        historico_list = historico[['Data', 'Entrada', 'Saída', 'Saldo', 'Obs']].copy()
        historico_list['Data'] = historico_list['Data'].dt.strftime('%d/%m/%Y')

        return jsonify({
            'success': True,
            'item': item,
            'historico': historico_list.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analisar', methods=['POST'])
def api_analisar():
    """Análise IA de um item"""
    try:
        item_nome = request.json.get('item', '').upper()
        df_idx, df_hist = carregar_dados_completos()

        # Dados do item
        item_data = df_idx[df_idx['Item'].str.upper() == item_nome]
        if item_data.empty:
            return jsonify({'success': False, 'error': 'Item não encontrado'})

        item = item_data.iloc[0]

        # Histórico recente
        hist = df_hist[df_hist['Item'].str.upper() == item_nome].tail(15)
        hist_texto = hist[['Data', 'Entrada', 'Saída', 'Saldo']].to_string(index=False)

        prompt = f"""
Analise este item de estoque:

ITEM: {item_nome}
SALDO ATUAL: {item['Saldo']:.0f} unidades
CONSUMO 30 DIAS: {item['Consumo_30d']:.0f} unidades
MÉDIA DIÁRIA: {item['Media_Diaria']:.1f} unidades
COBERTURA: {item['Dias_Cobertura']:.0f} dias

HISTÓRICO RECENTE:
{hist_texto}

Forneça:
1. Análise do padrão de consumo
2. Situação atual (crítico/adequado/excesso)
3. Recomendação de compra (Sim/Não e quantidade)
4. Previsão para os próximos 30 dias

Use português brasileiro e seja direto.
"""

        resposta = consultar_ia(prompt)

        return jsonify({'success': True, 'analise': resposta})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/alertas', methods=['GET'])
def api_alertas():
    """Retorna lista de alertas"""
    try:
        tipo = request.args.get('tipo', 'todos')
        df_idx, _ = carregar_dados_completos()

        if tipo == 'criticos':
            df_filtrado = df_idx[df_idx['Dias_Cobertura'] < 7]
        elif tipo == 'urgentes':
            df_filtrado = df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)]
        elif tipo == 'atencao':
            df_filtrado = df_idx[(df_idx['Dias_Cobertura'] >= 15) & (df_idx['Dias_Cobertura'] < 30)]
        elif tipo == 'zerados':
            df_filtrado = df_idx[df_idx['Saldo'] == 0]
        elif tipo == 'negativos':
            df_filtrado = df_idx[df_idx['Saldo'] < 0]
        else:
            df_filtrado = df_idx[df_idx['Dias_Cobertura'] < 30]

        df_filtrado = df_filtrado.sort_values('Dias_Cobertura')
        alertas = df_filtrado[['Item', 'Saldo', 'Consumo_30d', 'Dias_Cobertura']].head(100).to_dict('records')

        resumo = {
            'criticos': len(df_idx[df_idx['Dias_Cobertura'] < 7]),
            'urgentes': len(df_idx[(df_idx['Dias_Cobertura'] >= 7) & (df_idx['Dias_Cobertura'] < 15)]),
            'atencao': len(df_idx[(df_idx['Dias_Cobertura'] >= 15) & (df_idx['Dias_Cobertura'] < 30)]),
            'zerados': len(df_idx[df_idx['Saldo'] == 0]),
            'negativos': len(df_idx[df_idx['Saldo'] < 0])
        }

        return jsonify({'success': True, 'alertas': alertas, 'resumo': resumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/lista-compras', methods=['POST'])
def api_lista_compras():
    """Gera lista de compras inteligente"""
    try:
        dias_cobertura = request.json.get('dias_cobertura', 45)
        margem = request.json.get('margem', 20) / 100

        df_idx, _ = carregar_dados_completos()

        # Filtrar itens que precisam de reposição
        df_compras = df_idx[
            (df_idx['Dias_Cobertura'] < dias_cobertura) &
            (df_idx['Media_Diaria'] > 0)
        ].copy()

        # Calcular quantidade sugerida
        df_compras['Qtd_Sugerida'] = (
            df_compras['Media_Diaria'] * dias_cobertura * (1 + margem) - df_compras['Saldo']
        ).clip(lower=0).round(0)

        df_compras = df_compras[df_compras['Qtd_Sugerida'] > 0].sort_values('Dias_Cobertura')

        # Classificar urgência
        def classificar(dias):
            if dias < 0: return 'CRITICO'
            if dias < 7: return 'CRITICO'
            if dias < 15: return 'URGENTE'
            if dias < 30: return 'ALTO'
            return 'MEDIO'

        df_compras['Urgencia'] = df_compras['Dias_Cobertura'].apply(classificar)

        lista = df_compras[['Item', 'Saldo', 'Media_Diaria', 'Dias_Cobertura', 'Qtd_Sugerida', 'Urgencia']].head(100).to_dict('records')

        resumo = {
            'total_itens': len(df_compras),
            'total_unidades': df_compras['Qtd_Sugerida'].sum(),
            'criticos': len(df_compras[df_compras['Urgencia'] == 'CRITICO']),
            'urgentes': len(df_compras[df_compras['Urgencia'] == 'URGENTE'])
        }

        return jsonify({'success': True, 'lista': lista, 'resumo': resumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chatbot de estoque"""
    try:
        pergunta = request.json.get('pergunta', '')

        if not pergunta:
            return jsonify({'success': False, 'error': 'Pergunta vazia'})

        df_idx, _ = carregar_dados_completos()

        # Contexto
        stats = f"""
Dados do estoque Marfim:
- Total itens: {len(df_idx)}
- Críticos (<15 dias): {len(df_idx[df_idx['Dias_Cobertura'] < 15])}
- Zerados: {len(df_idx[df_idx['Saldo'] == 0])}
- Negativos: {len(df_idx[df_idx['Saldo'] < 0])}
- Consumo 30d: {df_idx['Consumo_30d'].sum():,.0f} unidades

Top 5 maior consumo: {', '.join(df_idx.nlargest(5, 'Consumo_30d')['Item'].tolist())}
Top 5 mais críticos: {', '.join(df_idx[df_idx['Dias_Cobertura'] < 999].nsmallest(5, 'Dias_Cobertura')['Item'].tolist())}
"""

        prompt = f"""
{stats}

Pergunta do usuário: {pergunta}

Responda de forma direta e útil em português brasileiro.
"""

        resposta = consultar_ia(prompt, "Você é o assistente de estoque da Marfim Têxtil. Responda de forma clara e direta.")

        return jsonify({'success': True, 'resposta': resposta})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/previsao/<item_nome>', methods=['GET'])
def api_previsao(item_nome):
    """Previsão de demanda para um item"""
    try:
        df_idx, df_hist = carregar_dados_completos()

        item_data = df_idx[df_idx['Item'].str.upper() == item_nome.upper()]
        if item_data.empty:
            return jsonify({'success': False, 'error': 'Item não encontrado'})

        item = item_data.iloc[0]
        media_diaria = item['Media_Diaria']
        saldo = item['Saldo']

        previsoes = []
        for dias in [15, 30, 45, 60, 90]:
            consumo_prev = media_diaria * dias
            saldo_prev = saldo - consumo_prev
            previsoes.append({
                'dias': dias,
                'consumo_previsto': round(consumo_prev, 0),
                'saldo_previsto': round(saldo_prev, 0),
                'status': 'CRITICO' if saldo_prev < 0 else ('ATENCAO' if saldo_prev < media_diaria * 15 else 'OK')
            })

        return jsonify({
            'success': True,
            'item': item_nome,
            'saldo_atual': saldo,
            'media_diaria': round(media_diaria, 2),
            'previsoes': previsoes
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/relatorio/curva-abc', methods=['GET'])
def api_curva_abc():
    """Retorna dados da curva ABC"""
    try:
        df_idx, _ = carregar_dados_completos()

        df_abc = df_idx[df_idx['Consumo_30d'] > 0].sort_values('Consumo_30d', ascending=False).copy()
        total = df_abc['Consumo_30d'].sum()
        if total > 0:
            df_abc['Percentual'] = df_abc['Consumo_30d'] / total * 100
            df_abc['Acumulado'] = df_abc['Percentual'].cumsum()
            df_abc['Classe'] = df_abc['Acumulado'].apply(
                lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
            )
        else:
            df_abc['Percentual'] = 0
            df_abc['Acumulado'] = 0
            df_abc['Classe'] = 'C'

        resumo = {
            'A': {'itens': len(df_abc[df_abc['Classe'] == 'A']), 'percentual': 80},
            'B': {'itens': len(df_abc[df_abc['Classe'] == 'B']), 'percentual': 15},
            'C': {'itens': len(df_abc[df_abc['Classe'] == 'C']), 'percentual': 5}
        }

        dados = df_abc[['Item', 'Consumo_30d', 'Percentual', 'Acumulado', 'Classe']].head(50).to_dict('records')

        return jsonify({'success': True, 'dados': dados, 'resumo': resumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================================
# NOVOS ENDPOINTS - MOVIMENTAÇÃO E AUTOCOMPLETE
# ============================================================

@app.route('/api/autocomplete', methods=['GET'])
def api_autocomplete():
    """Retorna lista de itens para autocomplete"""
    try:
        termo = request.args.get('q', '').upper().strip()
        limite = int(request.args.get('limite', 20))

        df_idx, _ = carregar_dados_completos()

        if termo:
            # Filtrar itens que começam com o termo (prioridade) ou contêm o termo
            df_inicio = df_idx[df_idx['Item'].str.upper().str.startswith(termo, na=False)]
            df_contem = df_idx[
                (df_idx['Item'].str.upper().str.contains(termo, na=False)) &
                (~df_idx['Item'].str.upper().str.startswith(termo, na=False))
            ]
            df_filtrado = pd.concat([df_inicio, df_contem])
        else:
            df_filtrado = df_idx

        # Encontrar coluna de grupo
        col_grupo = encontrar_coluna(df_idx, ['Grupo', 'GRUPO', 'grupo', 'Categoria', 'CATEGORIA'])

        itens = []
        for _, row in df_filtrado.head(limite).iterrows():
            item = {
                'nome': row['Item'],
                'saldo': float(row['Saldo']),
                'grupo': row[col_grupo] if col_grupo and col_grupo in row else ''
            }
            itens.append(item)

        return jsonify({
            'success': True,
            'itens': itens,
            'total': len(df_filtrado)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/itens-parados', methods=['GET'])
def api_itens_parados():
    """Retorna itens sem movimentação há X dias"""
    try:
        dias = int(request.args.get('dias', 20))

        df_idx, df_hist = carregar_dados_completos()

        hoje = datetime.now()
        data_limite = hoje - timedelta(days=dias)

        # Encontrar última movimentação de cada item
        if 'Data' in df_hist.columns and df_hist['Data'].notna().any():
            ultima_mov = df_hist.groupby('Item_Norm')['Data'].max()

            # Itens com última movimentação antiga ou sem movimentação
            df_idx['Ultima_Mov'] = df_idx['Item_Norm'].map(ultima_mov)

            # Itens parados: última mov < data_limite OU nunca tiveram movimento
            df_parados = df_idx[
                (df_idx['Ultima_Mov'].isna()) |
                (df_idx['Ultima_Mov'] < data_limite)
            ].copy()

            df_parados['Dias_Parado'] = df_parados['Ultima_Mov'].apply(
                lambda x: (hoje - x).days if pd.notna(x) else 999
            )
        else:
            # Sem dados de data, considerar todos como parados
            df_parados = df_idx.copy()
            df_parados['Ultima_Mov'] = None
            df_parados['Dias_Parado'] = 999

        # Ordenar por dias parado (descendente)
        df_parados = df_parados.sort_values('Dias_Parado', ascending=False)

        # Encontrar coluna de grupo
        col_grupo = encontrar_coluna(df_idx, ['Grupo', 'GRUPO', 'grupo', 'Categoria', 'CATEGORIA'])

        itens = []
        for _, row in df_parados.head(200).iterrows():
            item = {
                'nome': row['Item'],
                'saldo': float(row['Saldo']),
                'grupo': row[col_grupo] if col_grupo and col_grupo in row else '',
                'dias_parado': int(row['Dias_Parado']) if row['Dias_Parado'] != 999 else 'Nunca movimentado',
                'ultima_mov': row['Ultima_Mov'].strftime('%d/%m/%Y') if pd.notna(row['Ultima_Mov']) else 'Sem registro'
            }
            itens.append(item)

        return jsonify({
            'success': True,
            'itens': itens,
            'total': len(df_parados),
            'dias_filtro': dias
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()})


@app.route('/api/buscar-grupo', methods=['GET'])
def api_buscar_grupo():
    """Busca o grupo de um item existente"""
    try:
        item_nome = request.args.get('item', '').strip()

        if not item_nome:
            return jsonify({'success': False, 'error': 'Nome do item não informado'})

        df_idx, _ = carregar_dados_completos()

        # Buscar item
        item_data = df_idx[df_idx['Item'].str.upper() == item_nome.upper()]

        if item_data.empty:
            return jsonify({
                'success': True,
                'encontrado': False,
                'item_novo': True
            })

        # Encontrar coluna de grupo
        col_grupo = encontrar_coluna(df_idx, ['Grupo', 'GRUPO', 'grupo', 'Categoria', 'CATEGORIA'])

        item = item_data.iloc[0]
        grupo = item[col_grupo] if col_grupo and col_grupo in item else ''

        return jsonify({
            'success': True,
            'encontrado': True,
            'item_novo': False,
            'grupo': grupo,
            'saldo_atual': float(item['Saldo'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/grupos', methods=['GET'])
def api_grupos():
    """Retorna lista de grupos disponíveis"""
    try:
        df_idx, _ = carregar_dados_completos()

        col_grupo = encontrar_coluna(df_idx, ['Grupo', 'GRUPO', 'grupo', 'Categoria', 'CATEGORIA'])

        if col_grupo:
            grupos = df_idx[col_grupo].dropna().unique().tolist()
            grupos = [g for g in grupos if str(g).strip()]
            grupos.sort()
        else:
            grupos = []

        return jsonify({
            'success': True,
            'grupos': grupos
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/validar-movimentacao', methods=['POST'])
def api_validar_movimentacao():
    """IA valida a movimentação antes de confirmar"""
    try:
        dados = request.json
        tipo = dados.get('tipo', '')
        itens = dados.get('itens', [])

        if not client_groq:
            return jsonify({'success': True, 'validacao': None, 'mensagem': 'IA não configurada'})

        df_idx, df_hist = carregar_dados_completos()

        # Preparar contexto para IA
        itens_info = []
        alertas = []

        for item_info in itens:
            item_nome = item_info.get('item', '').strip()
            quantidade = float(item_info.get('quantidade', 0))

            # Buscar dados do item
            item_data = df_idx[df_idx['Item'].str.upper() == item_nome.upper()]

            if not item_data.empty:
                saldo_atual = float(item_data.iloc[0]['Saldo'])
                media_diaria = float(item_data.iloc[0]['Media_Diaria'])
                consumo_30d = float(item_data.iloc[0]['Consumo_30d'])

                itens_info.append({
                    'nome': item_nome,
                    'quantidade': quantidade,
                    'saldo_atual': saldo_atual,
                    'media_diaria': media_diaria,
                    'consumo_30d': consumo_30d,
                    'existe': True
                })

                # Alertas automáticos
                if tipo == 'saida' and quantidade > saldo_atual:
                    alertas.append(f"ALERTA: Saída de {quantidade} para '{item_nome}' excede saldo atual ({saldo_atual})")
                if quantidade > consumo_30d * 3 and consumo_30d > 0:
                    alertas.append(f"ATENÇÃO: Quantidade {quantidade} para '{item_nome}' é muito alta (3x o consumo de 30 dias)")
            else:
                itens_info.append({
                    'nome': item_nome,
                    'quantidade': quantidade,
                    'existe': False
                })
                alertas.append(f"NOVO ITEM: '{item_nome}' será cadastrado como novo")

        # Consultar IA para validação
        prompt = f"""
Você é o validador de movimentações de estoque da Marfim Têxtil. Analise esta operação:

TIPO: {tipo.upper()}
ITENS:
{chr(10).join([f"- {i['nome']}: {i['quantidade']} unidades" + (f" (saldo atual: {i.get('saldo_atual', 'N/A')}, média/dia: {i.get('media_diaria', 'N/A'):.1f})" if i.get('existe') else " [ITEM NOVO]") for i in itens_info])}

ALERTAS DETECTADOS:
{chr(10).join(alertas) if alertas else 'Nenhum alerta'}

Responda de forma MUITO CURTA e DIRETA:
1. A operação parece correta? (SIM/NÃO)
2. Algum risco ou observação importante? (máximo 2 linhas)
3. Recomendação: APROVAR, REVISAR ou REJEITAR

Use português brasileiro.
"""

        resposta = consultar_ia(prompt, "Você é um validador de estoque. Seja direto e objetivo.")

        return jsonify({
            'success': True,
            'validacao': resposta,
            'alertas': alertas,
            'itens_analisados': itens_info
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/analisar-parados', methods=['POST'])
def api_analisar_parados():
    """IA analisa itens parados e sugere ações"""
    try:
        itens = request.json.get('itens', [])

        if not client_groq:
            return jsonify({'success': False, 'error': 'IA não configurada'})

        if not itens:
            return jsonify({'success': False, 'error': 'Nenhum item para analisar'})

        # Limitar a 20 itens para não sobrecarregar
        itens = itens[:20]

        prompt = f"""
Analise estes {len(itens)} itens de estoque que estão PARADOS (sem movimentação):

{chr(10).join([f"- {i['nome']}: Saldo {i['saldo']}, Grupo: {i.get('grupo', 'N/A')}, Parado há {i['dias_parado']} dias" for i in itens])}

Forneça:
1. DIAGNÓSTICO GERAL (2-3 linhas): Por que estes itens podem estar parados?
2. CLASSIFICAÇÃO:
   - Itens que parecem OBSOLETOS (podem ser descartados)
   - Itens que precisam de PROMOÇÃO (vender rápido)
   - Itens SAZONAIS (podem voltar a girar)
3. AÇÕES RECOMENDADAS (bullet points práticos)

Use português brasileiro. Seja direto.
"""

        resposta = consultar_ia(prompt, "Você é um analista de estoque especializado em gestão de inventário parado.")

        return jsonify({
            'success': True,
            'analise': resposta,
            'total_analisados': len(itens)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sugerir-item', methods=['GET'])
def api_sugerir_item():
    """IA sugere correção para nome de item digitado incorretamente"""
    try:
        termo = request.args.get('termo', '').strip()

        if not termo or len(termo) < 3:
            return jsonify({'success': False, 'error': 'Termo muito curto'})

        df_idx, _ = carregar_dados_completos()

        # Buscar itens similares
        todos_itens = df_idx['Item'].tolist()

        # Filtro básico por similaridade
        similares = []
        termo_upper = termo.upper()
        for item in todos_itens:
            item_upper = item.upper()
            # Começa igual
            if item_upper.startswith(termo_upper[:3]):
                similares.append(item)
            # Contém partes do termo
            elif any(p in item_upper for p in termo_upper.split() if len(p) >= 3):
                similares.append(item)

        similares = similares[:10]

        if not similares:
            return jsonify({'success': True, 'sugestoes': [], 'mensagem': 'Nenhum item similar encontrado'})

        if client_groq:
            prompt = f"""
O usuário digitou: "{termo}"
Itens similares encontrados no estoque:
{chr(10).join([f"- {s}" for s in similares])}

Qual item o usuário provavelmente quis digitar? Responda APENAS com o nome exato do item mais provável, sem explicações.
"""
            sugestao_ia = consultar_ia(prompt, "Responda apenas com o nome do item, sem explicações.")
            sugestao_ia = sugestao_ia.strip().strip('"').strip("'")
        else:
            sugestao_ia = similares[0] if similares else None

        return jsonify({
            'success': True,
            'sugestao_ia': sugestao_ia,
            'similares': similares
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/movimentacao', methods=['POST'])
def api_movimentacao():
    """Registra entrada ou saída de estoque"""
    try:
        dados = request.json
        tipo = dados.get('tipo', '')  # 'entrada' ou 'saida'
        itens = dados.get('itens', [])  # Lista de {item, quantidade, nf, obs, grupo}

        if tipo not in ['entrada', 'saida']:
            return jsonify({'success': False, 'error': 'Tipo deve ser "entrada" ou "saida"'})

        if not itens:
            return jsonify({'success': False, 'error': 'Nenhum item informado'})

        ss = conectar_google()
        sheet_hist = ss.worksheet("ESTOQUE")
        sheet_idx = ss.worksheet("ÍNDICE_ITENS")

        # Carregar dados atuais para validação
        df_idx, df_hist = carregar_dados_completos()

        # Identificar colunas da planilha ESTOQUE
        colunas_hist = sheet_hist.row_values(1)
        col_grupo = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Grupo', 'GRUPO'])
        col_item = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Item', 'ITEM'])
        col_data = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Data', 'DATA'])
        col_nf = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['NF', 'Nota', 'NOTA'])
        col_obs = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Obs', 'OBS', 'Observação', 'OBSERVAÇÃO'])
        col_entrada = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Entrada', 'ENTRADA'])
        col_saida = encontrar_coluna(pd.DataFrame(columns=colunas_hist), ['Saída', 'SAÍDA', 'Saida', 'SAIDA'])

        resultados = []
        data_atual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        for item_info in itens:
            item_nome = item_info.get('item', '').strip()
            quantidade = float(item_info.get('quantidade', 0))
            nf = item_info.get('nf', '')
            obs = item_info.get('obs', '')
            grupo = item_info.get('grupo', '')

            if not item_nome or quantidade <= 0:
                resultados.append({
                    'item': item_nome,
                    'sucesso': False,
                    'erro': 'Item ou quantidade inválidos'
                })
                continue

            # Verificar se item existe
            item_existe = df_idx[df_idx['Item'].str.upper() == item_nome.upper()]

            if item_existe.empty and not grupo:
                resultados.append({
                    'item': item_nome,
                    'sucesso': False,
                    'erro': 'Item novo requer grupo'
                })
                continue

            # Buscar grupo do item existente
            if not grupo and not item_existe.empty:
                col_grupo_idx = encontrar_coluna(df_idx, ['Grupo', 'GRUPO', 'grupo'])
                if col_grupo_idx:
                    grupo = item_existe.iloc[0][col_grupo_idx]

            # Preparar linha para inserir
            nova_linha = [''] * len(colunas_hist)

            for i, col in enumerate(colunas_hist):
                col_upper = col.upper()
                if 'GRUPO' in col_upper:
                    nova_linha[i] = grupo
                elif 'ITEM' in col_upper:
                    nova_linha[i] = item_nome
                elif 'DATA' in col_upper:
                    nova_linha[i] = data_atual
                elif 'NF' in col_upper or 'NOTA' in col_upper:
                    nova_linha[i] = nf
                elif 'OBS' in col_upper:
                    nova_linha[i] = obs
                elif 'ENTRADA' in col_upper:
                    nova_linha[i] = str(quantidade).replace('.', ',') if tipo == 'entrada' else ''
                elif 'SAÍDA' in col_upper or 'SAIDA' in col_upper:
                    nova_linha[i] = str(quantidade).replace('.', ',') if tipo == 'saida' else ''

            # Inserir linha na planilha
            sheet_hist.append_row(nova_linha)

            resultados.append({
                'item': item_nome,
                'sucesso': True,
                'tipo': tipo,
                'quantidade': quantidade,
                'grupo': grupo
            })

        # Resumo
        sucessos = sum(1 for r in resultados if r['sucesso'])
        erros = len(resultados) - sucessos

        return jsonify({
            'success': True,
            'resultados': resultados,
            'resumo': {
                'total': len(resultados),
                'sucessos': sucessos,
                'erros': erros
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/debug', methods=['GET'])
def api_debug():
    """Endpoint de diagnóstico - mostra informações sobre os dados carregados"""
    try:
        ss = conectar_google()

        # Info ÍNDICE_ITENS
        sheet_idx = ss.worksheet("ÍNDICE_ITENS")
        dados_idx = sheet_idx.get_all_values()
        colunas_idx = dados_idx[0] if dados_idx else []
        linhas_idx = len(dados_idx) - 1 if len(dados_idx) > 1 else 0
        amostra_idx = dados_idx[1:4] if len(dados_idx) > 1 else []

        # Info ESTOQUE
        sheet_hist = ss.worksheet("ESTOQUE")
        dados_hist = sheet_hist.get_all_values()
        colunas_hist = dados_hist[0] if dados_hist else []
        linhas_hist = len(dados_hist) - 1 if len(dados_hist) > 1 else 0
        amostra_hist = dados_hist[1:4] if len(dados_hist) > 1 else []

        # Testar carregamento completo
        try:
            df_idx, df_hist = carregar_dados_completos()
            carregamento_ok = True
            itens_total = int(len(df_idx))
            itens_com_saldo = int((df_idx['Saldo'] > 0).sum())
            itens_com_consumo = int((df_idx['Consumo_30d'] > 0).sum())
            consumo_total = float(df_idx['Consumo_30d'].sum())
            datas_validas = int(df_hist['Data'].notna().sum()) if 'Data' in df_hist.columns else 0

            # Verificar matching de itens
            itens_idx = set(df_idx['Item_Norm'].unique()) if 'Item_Norm' in df_idx.columns else set()
            itens_hist = set(df_hist['Item_Norm'].unique()) if 'Item_Norm' in df_hist.columns else set()
            itens_comuns = len(itens_idx.intersection(itens_hist))

            # Datas recentes
            from datetime import datetime, timedelta
            hoje = datetime.now()
            data_30d = hoje - timedelta(days=30)
            registros_30d = int((df_hist['Data'] >= data_30d).sum()) if 'Data' in df_hist.columns else 0

            # Exemplo de saída
            saidas_exemplo = df_hist[df_hist['Saída'] > 0].head(3)[['Item', 'Saída', 'Data']].to_dict('records') if 'Saída' in df_hist.columns else []
            for s in saidas_exemplo:
                if pd.notna(s.get('Data')):
                    s['Data'] = str(s['Data'])

        except Exception as e:
            import traceback
            carregamento_ok = False
            itens_total = 0
            itens_com_saldo = 0
            itens_com_consumo = 0
            consumo_total = 0
            datas_validas = 0
            itens_comuns = 0
            registros_30d = 0
            saidas_exemplo = []
            print(f"[ERRO] {traceback.format_exc()}")

        return jsonify({
            'success': True,
            'planilha': NOME_PLANILHA,
            'indice_itens': {
                'colunas': colunas_idx,
                'total_linhas': linhas_idx,
                'amostra': amostra_idx
            },
            'estoque': {
                'colunas': colunas_hist,
                'total_linhas': linhas_hist,
                'amostra': amostra_hist
            },
            'processamento': {
                'ok': carregamento_ok,
                'itens_total': itens_total,
                'itens_com_saldo': itens_com_saldo,
                'itens_com_consumo': itens_com_consumo,
                'consumo_30d_total': round(consumo_total, 0),
                'datas_validas_historico': datas_validas,
                'itens_comuns_idx_hist': itens_comuns,
                'registros_ultimos_30d': registros_30d,
                'exemplos_saida': saidas_exemplo
            },
            'ia_configurada': client_groq is not None
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


if __name__ == '__main__':
    print("=" * 50)
    print(" MARFIM IA - Sistema Inteligente de Estoque")
    print(" Acesse: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
