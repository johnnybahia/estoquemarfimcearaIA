"""
Validador Inteligente de Inputs - Marfim IA
Previne erros de digitação, inputs sem sentido, normaliza textos
e usa IA para validar entradas em português brasileiro.
"""
import re
import unicodedata


# ============================================================
# 1. DETECÇÃO DE INPUTS SEM SENTIDO (GIBBERISH)
# ============================================================

def detectar_gibberish(texto):
    """
    Detecta se o texto é gibberish/sem sentido.
    Retorna: (bool é_gibberish, str motivo)

    Exemplos de gibberish:
    - ",,,,,,,,,,,,"
    - "!!!!!!"
    - "asdfghjkl"
    - "123456789" (quando esperado texto)
    - "     " (só espaços)
    - "aaa bbb ccc" (caracteres repetidos)
    """
    if not texto or not isinstance(texto, str):
        return True, "Entrada vazia"

    texto_limpo = texto.strip()

    if not texto_limpo:
        return True, "Entrada contém apenas espaços"

    # Apenas caracteres especiais/pontuação
    sem_alfanum = re.sub(r'[a-zA-ZÀ-ÿ0-9\s]', '', texto_limpo)
    apenas_alfanum = re.sub(r'[^a-zA-ZÀ-ÿ0-9]', '', texto_limpo)

    if not apenas_alfanum:
        return True, "Entrada não contém letras ou números válidos"

    # Proporção de caracteres especiais muito alta (mais de 50% do texto)
    if len(sem_alfanum) > len(texto_limpo) * 0.5 and len(texto_limpo) > 3:
        return True, "Entrada contém muitos caracteres especiais"

    # Mesmo caractere repetido excessivamente (ex: "aaaaaaa", ",,,,,,")
    for char in set(texto_limpo.replace(' ', '')):
        contagem = texto_limpo.count(char)
        if contagem > len(texto_limpo) * 0.6 and len(texto_limpo) > 3:
            return True, f"Caractere '{char}' repetido excessivamente"

    # Padrão de teclado (sequências comuns de mash de teclado)
    padroes_teclado = [
        'asdf', 'qwer', 'zxcv', 'hjkl', 'uiop',
        'asdfjkl', 'qwertyuiop', 'zxcvbnm',
        'aaaa', 'bbbb', 'cccc', 'dddd',
        'abcdef', '12345', '09876',
    ]
    texto_lower = texto_limpo.lower().replace(' ', '')
    for padrao in padroes_teclado:
        if padrao in texto_lower and len(texto_lower) <= len(padrao) + 4:
            return True, "Entrada parece ser digitação aleatória do teclado"

    # Texto muito curto sem sentido (1-2 caracteres que não são abreviações comuns)
    abreviacoes_validas = {'kg', 'mt', 'un', 'cx', 'pc', 'pç', 'lt', 'ml', 'cm', 'mm', 'gr', 'nf', 'op'}
    if len(texto_limpo) < 2 and texto_limpo.lower() not in abreviacoes_validas:
        return True, "Entrada muito curta"

    # Sequência alternada sem sentido (ex: "ababab", "xyzxyz")
    if len(texto_limpo) >= 6:
        metade = len(texto_limpo) // 2
        if texto_limpo[:metade] == texto_limpo[metade:2*metade]:
            # Verificar se não é uma palavra real repetida
            palavras = texto_limpo.split()
            if len(palavras) < 2:
                return True, "Padrão repetitivo detectado"

    # Proporção de vogais muito baixa (texto normal em português tem ~45% vogais)
    vogais = len(re.findall(r'[aeiouáéíóúâêîôûãõàè]', texto_lower))
    letras = len(re.findall(r'[a-záéíóúâêîôûãõàè]', texto_lower))
    if letras > 5 and vogais / letras < 0.15:
        return True, "Texto não parece conter palavras válidas em português"

    return False, "OK"


# ============================================================
# 2. NORMALIZAÇÃO DE TEXTO
# ============================================================

def normalizar_texto_input(texto, uppercase=True):
    """
    Normaliza texto de input do usuário:
    - Remove espaços extras (início, fim e entre palavras)
    - Corrige capitalização
    - Remove caracteres invisíveis/de controle
    - Normaliza unicode

    Args:
        texto: string a normalizar
        uppercase: se True, converte para maiúsculo (padrão para nomes de itens)

    Retorna: texto normalizado
    """
    if not texto or not isinstance(texto, str):
        return ""

    # Normalizar unicode (NFC - forma canônica composta)
    texto = unicodedata.normalize('NFC', texto)

    # Remover caracteres de controle e invisíveis (exceto espaço normal)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)

    # Remover zero-width spaces e outros invisíveis unicode
    texto = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', texto)

    # Substituir tabs e múltiplos espaços por espaço único
    texto = re.sub(r'[\t\r\n]+', ' ', texto)
    texto = re.sub(r' {2,}', ' ', texto)

    # Trim
    texto = texto.strip()

    # Capitalização
    if uppercase:
        texto = texto.upper()

    return texto


def normalizar_nome_item(nome):
    """
    Normalização específica para nomes de itens de estoque.
    Além da normalização padrão:
    - Remove pontuação desnecessária no início/fim
    - Corrige padrões comuns de digitação
    """
    nome = normalizar_texto_input(nome, uppercase=True)

    if not nome:
        return ""

    # Remover pontuação no início e fim
    nome = re.sub(r'^[^\w]+', '', nome)
    nome = re.sub(r'[^\w]+$', '', nome)

    # Remover pontos isolados entre palavras (ex: "TECIDO . ALGODAO" -> "TECIDO ALGODAO")
    nome = re.sub(r'\s*\.\s*', ' ', nome)

    # Normalizar hífens (ex: "TECIDO  -  ALGODAO" -> "TECIDO - ALGODAO")
    nome = re.sub(r'\s*-\s*', ' - ', nome)
    nome = re.sub(r' {2,}', ' ', nome)

    # Remover aspas
    nome = nome.replace('"', '').replace("'", '')

    return nome.strip()


def normalizar_observacao(obs):
    """
    Normaliza campo de observação.
    Mantém case original mas corrige espaços e caracteres.
    """
    return normalizar_texto_input(obs, uppercase=False)


def normalizar_numero_documento(nf):
    """
    Normaliza número de NF/pedido.
    Remove espaços extras, mantém pontuação válida.
    """
    if not nf or not isinstance(nf, str):
        return ""

    nf = nf.strip()
    # Remover espaços internos em números de documento
    nf = re.sub(r'\s+', '', nf)
    return nf.upper()


# ============================================================
# 3. VALIDAÇÃO DE CAMPOS ESPECÍFICOS
# ============================================================

def validar_nome_item(nome):
    """
    Valida nome de item de estoque.
    Retorna: (bool válido, str nome_normalizado, str mensagem_erro)
    """
    nome_norm = normalizar_nome_item(nome)

    if not nome_norm:
        return False, "", "Nome do item é obrigatório"

    # Verificar gibberish
    eh_gibberish, motivo = detectar_gibberish(nome_norm)
    if eh_gibberish:
        return False, nome_norm, f"Nome do item inválido: {motivo}"

    # Mínimo 2 caracteres
    if len(nome_norm) < 2:
        return False, nome_norm, "Nome do item deve ter pelo menos 2 caracteres"

    # Máximo 100 caracteres
    if len(nome_norm) > 100:
        return False, nome_norm, "Nome do item muito longo (máximo 100 caracteres)"

    # Deve conter pelo menos uma letra
    if not re.search(r'[A-ZÀ-Ÿ]', nome_norm):
        return False, nome_norm, "Nome do item deve conter letras"

    return True, nome_norm, "OK"


def validar_quantidade(valor):
    """
    Valida campo de quantidade.
    Retorna: (bool válido, float valor_convertido, str mensagem_erro)
    """
    if valor is None:
        return False, 0, "Quantidade é obrigatória"

    try:
        if isinstance(valor, str):
            valor = valor.strip()
            if not valor:
                return False, 0, "Quantidade é obrigatória"
            # Converter formato brasileiro
            if ',' in valor and '.' in valor:
                valor = valor.replace('.', '').replace(',', '.')
            elif ',' in valor:
                valor = valor.replace(',', '.')

        num = float(valor)

        if num <= 0:
            return False, 0, "Quantidade deve ser maior que zero"

        if num > 999999:
            return False, 0, "Quantidade muito alta. Verifique o valor digitado"

        return True, num, "OK"
    except (ValueError, TypeError):
        return False, 0, "Quantidade inválida. Use apenas números"


def validar_observacao(obs):
    """
    Valida campo de observação.
    Retorna: (bool válido, str obs_normalizada, str mensagem_erro)
    """
    if not obs or not isinstance(obs, str) or not obs.strip():
        return False, "", "Observação é obrigatória"

    obs_norm = normalizar_observacao(obs)

    # Verificar gibberish
    eh_gibberish, motivo = detectar_gibberish(obs_norm)
    if eh_gibberish:
        return False, obs_norm, f"Observação inválida: {motivo}"

    # Mínimo 2 caracteres
    if len(obs_norm) < 2:
        return False, obs_norm, "Observação muito curta"

    return True, obs_norm, "OK"


def validar_numero_documento(nf):
    """
    Valida número de NF/Pedido.
    Retorna: (bool válido, str nf_normalizada, str mensagem_erro)
    """
    if not nf or not isinstance(nf, str) or not nf.strip():
        return False, "", "Número NF/Pedido é obrigatório"

    nf_norm = normalizar_numero_documento(nf)

    # Verificar gibberish
    eh_gibberish, motivo = detectar_gibberish(nf_norm)
    if eh_gibberish:
        return False, nf_norm, f"NF/Pedido inválido: {motivo}"

    # Deve conter pelo menos um número ou letra
    if not re.search(r'[A-Z0-9]', nf_norm):
        return False, nf_norm, "NF/Pedido deve conter números ou letras"

    return True, nf_norm, "OK"


def validar_grupo(grupo):
    """
    Valida nome de grupo.
    Retorna: (bool válido, str grupo_normalizado, str mensagem_erro)
    """
    if not grupo or not isinstance(grupo, str) or not grupo.strip():
        return False, "", "Grupo é obrigatório"

    grupo_norm = normalizar_texto_input(grupo, uppercase=True)

    eh_gibberish, motivo = detectar_gibberish(grupo_norm)
    if eh_gibberish:
        return False, grupo_norm, f"Nome de grupo inválido: {motivo}"

    if len(grupo_norm) < 2:
        return False, grupo_norm, "Nome de grupo muito curto"

    if not re.search(r'[A-ZÀ-Ÿ]', grupo_norm):
        return False, grupo_norm, "Nome de grupo deve conter letras"

    return True, grupo_norm, "OK"


def validar_pergunta_chat(pergunta):
    """
    Valida pergunta do chat.
    Retorna: (bool válido, str pergunta_normalizada, str mensagem_erro)
    """
    if not pergunta or not isinstance(pergunta, str) or not pergunta.strip():
        return False, "", "Pergunta não pode ser vazia"

    pergunta_norm = normalizar_texto_input(pergunta, uppercase=False)

    eh_gibberish, motivo = detectar_gibberish(pergunta_norm)
    if eh_gibberish:
        return False, pergunta_norm, f"Pergunta inválida: {motivo}"

    if len(pergunta_norm) < 3:
        return False, pergunta_norm, "Pergunta muito curta"

    return True, pergunta_norm, "OK"


# ============================================================
# 4. VALIDAÇÃO POR IA (GROQ)
# ============================================================

def validar_input_com_ia(client_groq, texto, tipo_campo="nome de item"):
    """
    Usa IA para validar se o input faz sentido no contexto de estoque têxtil.

    Args:
        client_groq: cliente Groq configurado
        texto: texto a validar
        tipo_campo: tipo do campo ("nome de item", "observação", "grupo")

    Retorna: (bool válido, str sugestao_correcao, str mensagem)
    """
    if not client_groq:
        return True, texto, "IA não disponível para validação"

    try:
        prompt = f"""Você é um validador de dados de estoque de uma indústria TÊXTIL (tecidos, linhas, aviamentos, químicos, embalagens).

Analise este {tipo_campo} digitado pelo usuário: "{texto}"

Responda APENAS em formato JSON (sem markdown, sem ```):
{{
    "valido": true/false,
    "corrigido": "texto corrigido se necessário",
    "motivo": "breve explicação se inválido"
}}

Regras:
- Se o texto faz sentido como {tipo_campo} de estoque têxtil, é VÁLIDO
- Se tem erros de português, corrija em "corrigido" mas marque como VÁLIDO
- Se é gibberish/sem sentido/não relacionado a estoque, marque como INVÁLIDO
- Nomes de itens têxteis incluem: tecidos, linhas, fios, aviamentos, químicos, etiquetas, embalagens, etc.
- Seja tolerante com abreviações comuns do setor (ex: ALG = algodão, PES = poliéster)
"""

        chat = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Responda APENAS com JSON válido, sem explicações extras."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )

        resposta = chat.choices[0].message.content.strip()

        # Tentar parsear JSON da resposta
        import json
        # Limpar resposta (remover markdown se houver)
        resposta = re.sub(r'```json?\s*', '', resposta)
        resposta = re.sub(r'```\s*', '', resposta)

        dados = json.loads(resposta)

        valido = dados.get('valido', True)
        corrigido = dados.get('corrigido', texto)
        motivo = dados.get('motivo', '')

        return valido, corrigido, motivo

    except Exception as e:
        # Em caso de erro na IA, não bloquear - apenas retornar como válido
        return True, texto, f"Erro na validação IA: {str(e)}"


# ============================================================
# 5. VALIDAÇÃO COMPLETA DE MOVIMENTAÇÃO
# ============================================================

def validar_movimentacao_completa(dados, client_groq=None):
    """
    Validação completa de uma movimentação de estoque.

    Args:
        dados: dict com os dados da movimentação
        client_groq: cliente Groq opcional para validação IA

    Retorna: {
        'valido': bool,
        'erros': [str],
        'avisos': [str],
        'dados_normalizados': dict
    }
    """
    erros = []
    avisos = []
    dados_norm = {}

    # Validar tipo
    tipo = dados.get('tipo', '').strip().lower()
    if tipo not in ['entrada', 'saida']:
        erros.append("Tipo de movimentação deve ser 'entrada' ou 'saida'")
    dados_norm['tipo'] = tipo

    # Validar itens
    itens = dados.get('itens', [])
    if not itens:
        erros.append("Nenhum item informado na movimentação")

    itens_normalizados = []
    for i, item in enumerate(itens):
        item_erros = []
        item_norm = {}

        # Validar nome do item
        valido, nome_norm, msg = validar_nome_item(item.get('item', ''))
        if not valido:
            item_erros.append(f"Item {i+1}: {msg}")
        item_norm['item'] = nome_norm

        # Validar quantidade
        valido, qtd, msg = validar_quantidade(item.get('quantidade'))
        if not valido:
            item_erros.append(f"Item {i+1} ({nome_norm}): {msg}")
        item_norm['quantidade'] = qtd

        # Validar grupo (se item novo)
        if item.get('item_novo', False):
            valido, grupo_norm, msg = validar_grupo(item.get('grupo', ''))
            if not valido:
                item_erros.append(f"Item {i+1} ({nome_norm}): {msg}")
            item_norm['grupo'] = grupo_norm
        else:
            item_norm['grupo'] = normalizar_texto_input(item.get('grupo', ''), uppercase=True)

        # Copiar outros campos normalizados
        item_norm['nf'] = normalizar_numero_documento(item.get('nf', ''))
        item_norm['obs'] = normalizar_observacao(item.get('obs', ''))
        item_norm['unidade'] = normalizar_texto_input(item.get('unidade', 'UN'), uppercase=True)
        item_norm['saldo_atual'] = item.get('saldo_atual', 0)
        item_norm['novo_saldo'] = item.get('novo_saldo', 0)
        item_norm['valor_unitario'] = item.get('valor_unitario', 0)
        item_norm['item_novo'] = item.get('item_novo', False)

        # Validação IA para nome de item (se disponível e se parece suspeito)
        if client_groq and nome_norm and len(nome_norm) > 2:
            # Só usar IA se o nome tem padrão suspeito
            tem_numeros_demais = len(re.findall(r'\d', nome_norm)) > len(nome_norm) * 0.5
            muito_curto = len(nome_norm) < 4
            if tem_numeros_demais or muito_curto:
                valido_ia, corrigido, motivo_ia = validar_input_com_ia(
                    client_groq, nome_norm, "nome de item de estoque têxtil"
                )
                if not valido_ia:
                    avisos.append(f"Item {i+1}: IA sugere revisão - {motivo_ia}")
                elif corrigido != nome_norm:
                    avisos.append(f"Item {i+1}: IA sugere correção '{nome_norm}' → '{corrigido}'")
                    item_norm['sugestao_ia'] = corrigido

        erros.extend(item_erros)
        itens_normalizados.append(item_norm)

    dados_norm['itens'] = itens_normalizados

    return {
        'valido': len(erros) == 0,
        'erros': erros,
        'avisos': avisos,
        'dados_normalizados': dados_norm
    }


# ============================================================
# 6. ENDPOINT DE VALIDAÇÃO (para uso via API)
# ============================================================

def validar_input_generico(texto, tipo_campo="texto"):
    """
    Validação genérica para qualquer campo de texto.

    Args:
        texto: texto a validar
        tipo_campo: "nome_item", "observacao", "nf", "grupo", "chat", "busca"

    Retorna: {
        'valido': bool,
        'texto_normalizado': str,
        'mensagem': str
    }
    """
    validadores = {
        'nome_item': validar_nome_item,
        'observacao': validar_observacao,
        'nf': validar_numero_documento,
        'grupo': validar_grupo,
        'chat': validar_pergunta_chat,
    }

    if tipo_campo == 'busca':
        # Busca é mais tolerante
        texto_norm = normalizar_texto_input(texto, uppercase=True)
        if not texto_norm:
            return {'valido': False, 'texto_normalizado': '', 'mensagem': 'Digite algo para buscar'}
        eh_gibberish, motivo = detectar_gibberish(texto_norm)
        if eh_gibberish:
            return {'valido': False, 'texto_normalizado': texto_norm, 'mensagem': f'Busca inválida: {motivo}'}
        return {'valido': True, 'texto_normalizado': texto_norm, 'mensagem': 'OK'}

    validador = validadores.get(tipo_campo)
    if validador:
        valido, normalizado, msg = validador(texto)
        return {'valido': valido, 'texto_normalizado': normalizado, 'mensagem': msg}

    # Default: normalização básica + detecção gibberish
    texto_norm = normalizar_texto_input(texto, uppercase=False)
    eh_gibberish, motivo = detectar_gibberish(texto_norm)
    return {
        'valido': not eh_gibberish,
        'texto_normalizado': texto_norm,
        'mensagem': motivo
    }
