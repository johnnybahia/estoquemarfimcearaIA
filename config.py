"""
Configuração centralizada do Sistema de Estoque Marfim
Todas as credenciais e parâmetros ficam aqui
"""
import os
from datetime import datetime

# =============================================================================
# CREDENCIAIS (Use variáveis de ambiente em produção)
# =============================================================================
CHAVE_GROQ = os.getenv("GROQ_API_KEY", "")  # Coloque sua chave aqui ou use variável de ambiente
ARQUIVO_CREDENTIALS = "credentials.json"

# =============================================================================
# GOOGLE SHEETS
# =============================================================================
NOME_PLANILHA = "CEARÁ ESTOQUE ONLINE teste"
NOME_PLANILHA_PROD = "CEARÁ ESTOQUE ONLINE"
ABA_ESTOQUE = "ESTOQUE"
ABA_INDICE = "ÍNDICE_ITENS"

# =============================================================================
# PARÂMETROS DE ANÁLISE
# =============================================================================
LIMITE_ESTOQUE_BAIXO = 21
DIAS_SEM_MOVIMENTO = 30
DIAS_ATENCAO = 60
DIAS_OBSOLETO = 90
SIMILARIDADE_DUPLICADO = 0.85
MESES_ANALISE_CONSUMO = 3

# =============================================================================
# PARÂMETROS DE PREVISÃO E IA
# =============================================================================
DIAS_PREVISAO = [15, 30, 60, 90]  # Períodos de previsão em dias
COBERTURA_MINIMA_DIAS = 15  # Cobertura mínima recomendada
COBERTURA_IDEAL_DIAS = 30   # Cobertura ideal
MARGEM_SEGURANCA = 1.2      # 20% de margem de segurança nas compras

# Configurações do modelo de IA
MODELO_GROQ = "llama-3.3-70b-versatile"
TEMPERATURA_ANALISE = 0.3    # Mais preciso para análises técnicas
TEMPERATURA_CHAT = 0.5       # Mais criativo para conversação

# =============================================================================
# ALERTAS
# =============================================================================
NIVEIS_ALERTA = {
    "CRITICO": {"cor": "🔴", "prioridade": 1, "dias_cobertura": 7},
    "URGENTE": {"cor": "🟠", "prioridade": 2, "dias_cobertura": 15},
    "ATENCAO": {"cor": "🟡", "prioridade": 3, "dias_cobertura": 30},
    "NORMAL": {"cor": "🟢", "prioridade": 4, "dias_cobertura": 999}
}

# =============================================================================
# CLASSIFICAÇÃO DE ITENS
# =============================================================================
CATEGORIAS_ITEM = [
    "TECIDO", "LINHA", "AVIAMENTO", "QUIMICO", "EMBALAGEM",
    "ETIQUETA", "BOTAO", "ZIPER", "ELASTICO", "FITA",
    "ENTRETELA", "PAPEL", "AGULHA", "FORRO", "OUTROS"
]

# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================
def converter_para_numero(valor):
    """Converte valor brasileiro (1.200,50) para float"""
    if valor is None or valor == "":
        return 0.0
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        s = str(valor).strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

def formatar_numero_br(valor, decimais=2):
    """Formata número para padrão brasileiro"""
    try:
        return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def formatar_data_br(data):
    """Formata data para padrão brasileiro"""
    if isinstance(data, datetime):
        return data.strftime('%d/%m/%Y %H:%M')
    return str(data)

def get_conexao_sheets():
    """Retorna conexão com Google Sheets"""
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(NOME_PLANILHA)

def get_client_groq():
    """Retorna cliente Groq configurado"""
    from groq import Groq
    return Groq(api_key=CHAVE_GROQ)

# =============================================================================
# VERSÃO DO SISTEMA
# =============================================================================
VERSAO = "2.0.0"
NOME_SISTEMA = "Marfim IA - Sistema Inteligente de Estoque"
ANO = datetime.now().year
