# 🤖 Sistema de IA Avançada - Marfim Estoque

> **Inteligência que prevê e protege!** Validação, predição e recomendações automáticas.

---

## 🎯 O QUE É?

Sistema inteligente que **valida, prevê e recomenda** automaticamente:

- 🤖 **Validação avançada** com score e confiança
- 🔮 **Predição de saldo** futuro (7-30 dias)
- 🔍 **Detecção de anomalias** em tempo real
- 💡 **Recomendações automáticas** priorizadas
- 📊 **Análise completa** de itens

---

## ✨ FUNCIONALIDADES

### **1. Validação Inteligente**

**5 Regras de Validação:**

| Regra | O que valida | Impacto |
|-------|--------------|---------|
| Quantidade | > 0, não absurda (>10k) | Score -50 se zero |
| Saldo para SAÍDA | Não pode ser > saldo atual | Score -30 |
| Histórico | Compara com média ± desvio padrão | Score -15 se anormal |
| Padrões | Detecta entrada com saldo alto | Aviso |
| Horário | Movimentação fora do horário comercial | Score -5 |

**Sistema de Score:**
- **100-80:** ✅ Excelente, pode confirmar
- **79-60:** ⚠️ Bom, mas verifique avisos
- **59-40:** 🟡 Questionável, revise
- **<40:** 🔴 Problemático, não recomendado

**Níveis de Confiança:**
- **Muito Alta:** >90% (histórico extenso, padrão claro)
- **Alta:** 70-90% (bom histórico)
- **Média:** 50-70% (histórico limitado)
- **Baixa:** <50% (sem histórico ou inconsistente)

### **2. Predição de Saldo Futuro**

**Como funciona:**
1. Analisa últimas 30 movimentações
2. Calcula média diária de consumo
3. Projeta saldo para N dias no futuro
4. Calcula dias para zerar
5. Determina tendência (crescente/decrescente/estável)

**Exemplo:**
```
Saldo atual: 250
Média diária: 10 (SAÍDA)
Dias para prever: 7

→ Saldo previsto: 250 - (10 × 7) = 180
→ Dias para zerar: 250 ÷ 10 = 25 dias
→ Tendência: decrescente
→ Recomendação: "✅ Saldo previsto OK"
```

### **3. Detecção de Anomalias**

**5 Tipos de Anomalia:**

| Tipo | Detecção | Quando Alerta |
|------|----------|---------------|
| Quantidade anormal | Z-score > 2.5 | 1000 quando média é 100 |
| Frequência anormal | 4+ saídas sem entrada | SAÍDA, SAÍDA, SAÍDA, SAÍDA |
| Horário incomum | <6h ou >22h | 02:30 da manhã |
| Saldo inesperado | Negativo inesperado | - |
| Padrão diferente | Mudança súbita | - |

**Z-Score:**
```
z = (valor - média) / desvio_padrão

Se z > 2.5 → Anomalia!
```

### **4. Recomendações Automáticas**

**Prioridades:**
- **P5 (Crítico):** 🔴 Ação urgente necessária
- **P4 (Alta):** 🟠 Resolver hoje
- **P3 (Média):** 🟡 Resolver esta semana
- **P2 (Baixa):** 🔵 Quando possível
- **P1 (Info):** ℹ️ Informativo

**Tipos:**
- Repor estoque
- Verificar quantidade
- Ajustar tipo de movimentação
- Conferir saldo
- Atenção a padrão

---

## 📂 ARQUIVOS CRIADOS

```
ia_avancada.py                # Lógica de IA (600 linhas)
ia_integration.py             # Endpoints Flask (320 linhas)
frontend_ia.html              # Interface visual (450 linhas)
IA_README.md                  # Esta documentação
```

**Total:** ~1.370 linhas! 🎉

---

## 🚀 COMO USAR

### **1. Integrar no Flask**

```python
# Em app_final.py
from ia_integration import register_ia_routes

register_ia_routes(app)
```

### **2. Validar Movimentação**

```python
from ia_avancada import sistema_ia

# Valida
validacao = sistema_ia.validar_movimentacao(
    item='AMARELO 1234',
    tipo_movimentacao='SAIDA',
    quantidade=100,
    saldo_atual=250,
    historico=[...]  # Opcional, busca automaticamente
)

print(f"Válido: {validacao.valido}")
print(f"Score: {validacao.score}/100")
print(f"Confiança: {validacao.confianca}%")

if validacao.problemas:
    for problema in validacao.problemas:
        print(f"❌ {problema}")

if validacao.avisos:
    for aviso in validacao.avisos:
        print(f"⚠️ {aviso}")

if validacao.sugestoes:
    for sugestao in validacao.sugestoes:
        print(f"💡 {sugestao}")
```

### **3. Prever Saldo Futuro**

```python
# Predição para 7 dias
predicao = sistema_ia.prever_saldo_futuro(
    item='AMARELO 1234',
    dias=7
)

print(f"Saldo atual: {predicao.saldo_atual}")
print(f"Saldo previsto: {predicao.saldo_previsto}")
print(f"Dias para zerar: {predicao.dias_para_zerar}")
print(f"Tendência: {predicao.tendencia}")
print(f"Recomendação: {predicao.recomendacao}")
```

### **4. Detectar Anomalias**

```python
# Detecta anomalias
anomalias = sistema_ia.detectar_anomalias(
    item='AMARELO 1234',
    quantidade=1000,  # Muito acima do normal
    tipo_movimentacao='SAIDA',
    historico=[...]
)

for anomalia in anomalias:
    print(f"🔍 {anomalia.tipo.value}")
    print(f"   Gravidade: {anomalia.gravidade}")
    print(f"   {anomalia.descricao}")
    print(f"   💡 {anomalia.recomendacao}")
```

### **5. Gerar Recomendações**

```python
# Recomendações automáticas
recomendacoes = sistema_ia.gerar_recomendacoes(limite=5)

for rec in recomendacoes:
    print(f"[P{rec.prioridade}] {rec.titulo}")
    print(f"    {rec.descricao}")
    print(f"    👉 {rec.acao_sugerida}")
```

---

## 📡 API ENDPOINTS (8 novos!)

### **1. Validar com IA**
```http
POST /api/ia/validar
Content-Type: application/json

{
  "item": "AMARELO 1234",
  "tipo_movimentacao": "SAIDA",
  "quantidade": 100,
  "saldo_atual": 250
}

Response:
{
  "validacao": {
    "valido": true,
    "confianca": 85.0,
    "nivel_confianca": "alta",
    "problemas": [],
    "avisos": ["⚠️ Quantidade acima da média"],
    "sugestoes": ["💡 Confirme se 100 está correto"],
    "score": 75.0,
    "timestamp": "2026-02-13T10:30:00"
  }
}
```

### **2. Prever Saldo Futuro**
```http
POST /api/ia/prever-saldo
Content-Type: application/json

{
  "item": "AMARELO 1234",
  "dias": 7
}

Response:
{
  "predicao": {
    "item": "AMARELO 1234",
    "saldo_atual": 250.0,
    "saldo_previsto": 180.0,
    "dias_para_zerar": 25,
    "confianca": 75.0,
    "tendencia": "decrescente",
    "media_diaria": 10.0,
    "recomendacao": "✅ Saldo previsto OK"
  }
}
```

### **3. Detectar Anomalias**
```http
POST /api/ia/detectar-anomalias

{
  "item": "AMARELO 1234",
  "quantidade": 1000,
  "tipo_movimentacao": "SAIDA"
}

Response:
{
  "anomalias": [
    {
      "tipo": "quantidade_anormal",
      "gravidade": "alta",
      "descricao": "Quantidade 1000 está 5.2 desvios acima",
      "valor_atual": 1000,
      "valor_esperado": 100,
      "confianca": 95.0,
      "recomendacao": "Verifique se está correto"
    }
  ],
  "total": 1
}
```

### **4. Recomendações**
```http
GET /api/ia/recomendacoes?limite=5

Response:
{
  "recomendacoes": [
    {
      "tipo": "repor_estoque",
      "titulo": "⚠️ Repor estoque: AMARELO 1234",
      "descricao": "Sem movimentação há 25 dias",
      "prioridade": 5,
      "item": "AMARELO 1234",
      "acao_sugerida": "Realizar entrada de estoque",
      "impacto_estimado": "Evita parada de produção"
    }
  ],
  "total": 1
}
```

### **5. Analisar Item Completo**
```http
GET /api/ia/analisar-item/AMARELO%201234

Response:
{
  "item": "AMARELO 1234",
  "saldo_atual": 250.0,
  "predicao": {...},
  "alerta": {...},
  "total_movimentacoes": 45,
  "analise_ia": {
    "status": "✅ OK",
    "recomendacao_principal": "Saldo previsto OK"
  }
}
```

### **6. Validar Lote**
```http
POST /api/ia/validar-lote

{
  "movimentacoes": [
    {"item": "ITEM1", "tipo_movimentacao": "SAIDA", "quantidade": 100, "saldo_atual": 250},
    {"item": "ITEM2", "tipo_movimentacao": "ENTRADA", "quantidade": 50, "saldo_atual": 100}
  ]
}

Response:
{
  "validacoes": [
    {"item": "ITEM1", "validacao": {...}},
    {"item": "ITEM2", "validacao": {...}}
  ],
  "total": 2,
  "validos": 2,
  "invalidos": 0
}
```

### **7. Dashboard IA**
```http
GET /api/ia/dashboard

Response:
{
  "recomendacoes_prioritarias": [...],
  "itens_criticos": [...],
  "predicoes_criticas": [...],
  "estatisticas": {
    "total_recomendacoes": 5,
    "itens_atencao": 3,
    "score_medio": 85.0
  }
}
```

### **8. Configurações**
```http
GET /api/ia/configuracoes

Response:
{
  "score_minimo_valido": 60,
  "confianca_minima": 50,
  "desvio_padrao_max": 2.5,
  "quantidade_min_historico": 5,
  "dias_historico": 30,
  "dias_predicao": 7,
  "dias_critico_estoque": 3,
  "dias_atencao_estoque": 7
}
```

---

## ⚙️ CONFIGURAÇÕES

Em `ia_avancada.py`:

```python
class ConfigIA:
    # Validação
    SCORE_MINIMO_VALIDO = 60      # Score mínimo
    CONFIANCA_MINIMA = 50         # Confiança mínima %

    # Anomalias
    DESVIO_PADRAO_MAX = 2.5       # Z-score máximo
    QUANTIDADE_MIN_HISTORICO = 5  # Mínimo para análise

    # Predição
    DIAS_HISTORICO = 30           # Dias de histórico
    DIAS_PREDICAO = 7             # Dias no futuro

    # Recomendações
    DIAS_CRITICO_ESTOQUE = 3      # Crítico se zerar em <= 3 dias
    DIAS_ATENCAO_ESTOQUE = 7      # Atenção se zerar em <= 7 dias
```

---

## 🎨 INTEGRAÇÃO COMPLETA

### **Fluxo com 5 FASES:**

```python
@app.route('/api/inserir-ultra-completo', methods=['POST'])
def inserir_ultra_completo():
    data = request.get_json()

    # 1. FASE 5: Validação com IA ⭐ NOVO!
    validacao_ia = sistema_ia.validar_movimentacao(
        item=data['item'],
        tipo_movimentacao=data['tipo'],
        quantidade=data['quantidade'],
        saldo_atual=data['saldo_atual']
    )

    if not validacao_ia.valido:
        return jsonify({
            'success': False,
            'validacao_ia': validacao_ia.to_dict()
        }), 400

    # 2. FASE 3: Preview
    preview = gerenciador_preview.calcular_preview(...)

    if not preview.pode_confirmar:
        return jsonify({'error': preview.alerta}), 400

    # 3. Insere na planilha
    resultado = inserir_movimentacao(...)

    # 4. FASE 1: Atualiza índice
    indice_otimizado.atualizar_item(...)

    # 5. FASE 4: Adiciona ao histórico
    gerenciador_historico.adicionar_registro(...)

    # 6. FASE 2: Classifica alerta
    alerta = gerenciador_alertas.classificar_movimentacao(...)

    # 7. FASE 5: Detecta anomalias ⭐ NOVO!
    anomalias = sistema_ia.detectar_anomalias(
        item=data['item'],
        quantidade=data['quantidade'],
        tipo_movimentacao=data['tipo']
    )

    # 8. FASE 5: Predição ⭐ NOVO!
    predicao = sistema_ia.prever_saldo_futuro(
        item=data['item'],
        dias=7,
        saldo_atual=preview.novo_saldo
    )

    return jsonify({
        'success': True,
        'validacao_ia': validacao_ia.to_dict(),
        'preview': preview.to_dict(),
        'alerta': alerta.to_dict(),
        'anomalias': [a.to_dict() for a in anomalias],
        'predicao': predicao.to_dict(),
        'resultado': resultado
    })
```

---

## 💡 EXEMPLOS AVANÇADOS

### **Exemplo 1: Validação Antes de Inserir**

```python
# Intercepta ANTES de inserir
validacao = sistema_ia.validar_movimentacao(
    item=item,
    tipo_movimentacao=tipo,
    quantidade=quantidade,
    saldo_atual=saldo_atual
)

if validacao.score < 70:
    # Mostra modal de confirmação
    return {
        'confirmacao_necessaria': True,
        'validacao': validacao.to_dict(),
        'mensagem': 'Score baixo. Deseja continuar?'
    }

# Se score >= 70, insere normalmente
```

### **Exemplo 2: Dashboard com Predições**

```python
@app.route('/api/dashboard-predicoes', methods=['GET'])
def dashboard_predicoes():
    # Busca itens com movimento recente
    from indice_otimizado import indice_otimizado
    todos_itens = indice_otimizado.obter_todos_itens()

    predicoes_criticas = []

    for item_nome in todos_itens[:50]:  # Top 50
        predicao = sistema_ia.prever_saldo_futuro(item_nome, dias=7)

        # Filtra críticos
        if predicao.dias_para_zerar and predicao.dias_para_zerar <= 7:
            predicoes_criticas.append(predicao.to_dict())

    # Ordena por urgência
    predicoes_criticas.sort(key=lambda x: x['dias_para_zerar'] or 999)

    return jsonify({
        'predicoes_criticas': predicoes_criticas[:10],
        'total_analisado': len(todos_itens)
    })
```

### **Exemplo 3: Relatório de Anomalias do Dia**

```python
@app.route('/api/relatorio-anomalias-hoje', methods=['GET'])
def relatorio_anomalias():
    from historico_otimizado import gerenciador_historico

    # Movimentações de hoje
    hoje = gerenciador_historico.buscar_hoje()

    anomalias_encontradas = []

    for registro in hoje:
        anomalias = sistema_ia.detectar_anomalias(
            item=registro.item,
            quantidade=registro.quantidade,
            tipo_movimentacao=registro.tipo_movimentacao
        )

        if anomalias:
            anomalias_encontradas.append({
                'registro': registro.to_dict(),
                'anomalias': [a.to_dict() for a in anomalias]
            })

    return jsonify({
        'data': datetime.now().strftime('%d/%m/%Y'),
        'total_movimentacoes': len(hoje),
        'com_anomalias': len(anomalias_encontradas),
        'anomalias': anomalias_encontradas
    })
```

---

## 📊 BENEFÍCIOS

### **Antes (sem IA):**
- ❌ Erros de digitação passam
- ❌ Quantidades anormais não detectadas
- ❌ Sem previsão de falta
- ❌ Decisões reativas

### **Agora (com IA):**
- ✅ **Validação automática** antes de inserir
- ✅ **Detecta anomalias** em tempo real
- ✅ **Prevê falta** com 7+ dias de antecedência
- ✅ **Recomendações proativas**
- ✅ **Score de confiança** para cada operação
- ✅ **Decisões baseadas em dados**

---

## 🎯 CASOS DE USO

1. **Validação Pré-Inserção** - Bloqueia erros antes de acontecer
2. **Dashboard Preditivo** - Mostra itens que zerarão em breve
3. **Alertas Inteligentes** - Notifica anomalias automaticamente
4. **Relatório de Qualidade** - Score médio das movimentações
5. **Auditoria Automática** - Detecta padrões suspeitos

---

## 📈 PERFORMANCE

| Operação | Tempo | Complexidade |
|----------|-------|--------------|
| Validação | 1-5ms | O(N) histórico |
| Predição | 2-10ms | O(N) histórico |
| Anomalias | 1-5ms | O(N) histórico |
| Recomendações | 5-20ms | O(N) alertas |

**N = tamanho do histórico (tipicamente 20-50)**

---

## 🔗 INTEGRAÇÃO COM OUTRAS FASES

### **Com FASE 1 (Cache):**
```python
# Busca saldo do índice para validar
dados = indice_otimizado.buscar_item(item)
saldo = dados['saldo']
sistema_ia.validar_movimentacao(..., saldo_atual=saldo)
```

### **Com FASE 2 (Alertas):**
```python
# Recomendações incluem alertas críticos
alertas = gerenciador_alertas.obter_alertas_criticos()
# IA usa para gerar recomendações priorizadas
```

### **Com FASE 3 (Preview):**
```python
# Preview + Validação IA juntos
preview = gerenciador_preview.calcular_preview(...)
validacao = sistema_ia.validar_movimentacao(...)

# Se ambos OK, confirma
if preview.pode_confirmar and validacao.valido:
    inserir()
```

### **Com FASE 4 (Histórico):**
```python
# IA usa histórico para análise
historico = gerenciador_historico.buscar_por_item(item)
validacao = sistema_ia.validar_movimentacao(..., historico=historico)
```

---

## ✅ RESUMO

**4 arquivos criados** = Sistema completo de IA!

**Funcionalidades:**
- 🤖 Validação com 5 regras
- 🔮 Predição 7-30 dias
- 🔍 5 tipos de anomalias
- 💡 Recomendações priorizadas
- 📊 8 endpoints RESTful

**Inteligência:**
- Score 0-100
- Confiança 0-100%
- Z-score estatístico
- Análise de tendências
- Sistema de prioridades

**Integração:**
- 1 linha no Flask
- Frontend completo
- API documentada

---

**Criado com ❤️ por Johnny - 2026-02-13**
