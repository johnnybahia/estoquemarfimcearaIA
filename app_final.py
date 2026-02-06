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

    # Converter Data - tentar múltiplos formatos (incluindo com hora)
    if col_data and col_data in df_hist.columns:
        df_hist['Data_Original'] = df_hist[col_data]
        # Tentar diferentes formatos (com e sem hora)
        formatos = [
            '%d/%m/%Y %H:%M:%S',  # 03/01/2022 00:00:00
            '%d/%m/%Y',           # 03/01/2022
            '%Y-%m-%d %H:%M:%S',  # 2022-01-03 00:00:00
            '%Y-%m-%d',           # 2022-01-03
            '%d-%m-%Y %H:%M:%S',
            '%d-%m-%Y',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y'
        ]
        for fmt in formatos:
            df_hist['Data'] = pd.to_datetime(df_hist[col_data], format=fmt, errors='coerce')
            if df_hist['Data'].notna().sum() > 0:
                print(f"[DEBUG] Formato de data detectado: {fmt}")
                break
        # Fallback: tentar inferir automaticamente
        if df_hist['Data'].isna().all():
            df_hist['Data'] = pd.to_datetime(df_hist[col_data], dayfirst=True, errors='coerce')
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

    # Consumo por período (apenas se houver datas válidas)
    if datas_validas > 0:
        consumo_30d = df_hist[df_hist['Data'] >= data_30d].groupby('Item')['Saída'].sum()
        consumo_60d = df_hist[df_hist['Data'] >= data_60d].groupby('Item')['Saída'].sum()
        consumo_90d = df_hist[df_hist['Data'] >= data_90d].groupby('Item')['Saída'].sum()
    else:
        # Se não há datas, usar todo o histórico
        print("[AVISO] Usando todo histórico (sem filtro de data)")
        consumo_30d = df_hist.groupby('Item')['Saída'].sum()
        consumo_60d = consumo_30d
        consumo_90d = consumo_30d

    df_idx['Consumo_30d'] = df_idx['Item'].map(consumo_30d).fillna(0)
    df_idx['Consumo_60d'] = df_idx['Item'].map(consumo_60d).fillna(0)
    df_idx['Consumo_90d'] = df_idx['Item'].map(consumo_90d).fillna(0)
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
        except Exception as e:
            carregamento_ok = False
            itens_total = 0
            itens_com_saldo = 0
            itens_com_consumo = 0
            consumo_total = 0
            datas_validas = 0

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
                'datas_validas_historico': datas_validas
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
