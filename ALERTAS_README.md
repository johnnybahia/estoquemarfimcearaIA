# 🚨 Sistema de Alertas Automáticos - Marfim Estoque

> **Monitoramento inteligente** com classificação automática por cores

---

## 📋 O QUE É?

Sistema que **detecta automaticamente** situações que precisam de atenção no estoque e **classifica por cores**:

- 🔴 **CRÍTICO**: Itens parados há >20 dias
- 🟡 **ATENÇÃO**: Entradas de estoque (ganhos)
- 🟢 **NORMAL**: Movimentação regular (<7 dias)
- ⚪ **INFO**: Itens com 7-10 dias

---

## ✨ FUNCIONALIDADES

### **1. Classificação Automática**
- ✅ Analisa TODOS os itens do estoque
- ✅ Calcula dias desde última movimentação
- ✅ Classifica por severidade (ALTA/MÉDIA/BAIXA)
- ✅ Gera mensagens e sugestões de ação

### **2. Dashboard Visual**
- 📊 Contadores por tipo de alerta
- 📈 Estatísticas completas
- 🔝 Top 10 críticos e atenção
- 🎨 Interface bonita com Material Design

### **3. Cache Otimizado**
- ⚡ TTL de 5 minutos (configurável)
- 💾 Redis + memória
- 🔄 Invalidação inteligente

### **4. API Completa**
- 10 endpoints RESTful
- 📖 Documentação inline
- ✅ Validação de dados

---

## 📂 ARQUIVOS CRIADOS

```
estoquemarfimcearaIA/
├── alertas_config.py           # Lógica de classificação (600 linhas)
├── alertas_integration.py      # Endpoints Flask (400 linhas)
├── frontend_alertas.html       # Interface visual (500 linhas)
├── test_alertas.py             # Testes automatizados (350 linhas)
└── ALERTAS_README.md           # Esta documentação
```

**Total:** ~1.850 linhas de código! 🎉

---

## 🚀 COMO USAR

### **1. Instalar (já está tudo criado!)**

Os arquivos já foram criados. Apenas certifique-se que a FASE 1 (cache) está instalada:

```bash
pip install -r requirements.txt
```

### **2. Integrar no Flask**

Adicione em `app_final.py`:

```python
# No topo do arquivo
from alertas_integration import register_alertas_routes

# Depois de criar app
app = Flask(__name__)
# ... outras configurações ...

# Registra endpoints de alertas
register_alertas_routes(app)
```

Pronto! 🎉

### **3. Testar**

```bash
# Roda testes automatizados
python test_alertas.py

# Deve mostrar:
# ✅ Todos os testes passaram!
```

### **4. Acessar Interface**

```bash
# Inicia Flask
python app_final.py

# Em outro terminal, abre o navegador:
# Linux/Mac
xdg-open frontend_alertas.html  # Linux
open frontend_alertas.html       # Mac

# Windows
start frontend_alertas.html
```

---

## 📡 API ENDPOINTS

### **1. Dashboard Completo**
```http
GET /api/alertas/dashboard

Response:
{
  "contadores": {
    "critico": 15,
    "atencao": 32,
    "normal": 180,
    "info": 78,
    "total": 305
  },
  "top_criticos": [...],
  "top_atencao": [...],
  "estatisticas": {
    "total_itens": 305,
    "media_dias_parado": 12.5,
    "max_dias_parado": 45,
    "porcentagem_critico": 4.9,
    "porcentagem_atencao": 10.5
  }
}
```

### **2. Listar Todos**
```http
GET /api/alertas/todos?limit=50&forcar_recarga=false

Response:
{
  "alertas": [
    {
      "tipo": "critico",
      "severidade": 3,
      "item": "AMARELO 1234",
      "grupo": "FIOS",
      "mensagem": "🔴 CRÍTICO: Item parado há 35 dias!",
      "dias_parado": 35,
      "ultima_data": "09/01/2026",
      "saldo_atual": 150.0,
      "sugestao": "⚠️ Item parado há 35 dias...",
      "cor_hex": "#F44336",
      "icone": "🔴"
    }
  ],
  "total": 305
}
```

### **3. Apenas Críticos**
```http
GET /api/alertas/criticos?limit=10

Response:
{
  "alertas": [...],  // Apenas alertas críticos
  "total": 15
}
```

### **4. Apenas Atenção**
```http
GET /api/alertas/atencao?limit=10

Response:
{
  "alertas": [...],  // Apenas alertas de atenção
  "total": 32
}
```

### **5. Por Tipo**
```http
GET /api/alertas/por-tipo/critico
GET /api/alertas/por-tipo/atencao
GET /api/alertas/por-tipo/normal
GET /api/alertas/por-tipo/info

Response:
{
  "alertas": [...],
  "total": 15,
  "tipo": "critico"
}
```

### **6. Classificar Movimentação**
```http
POST /api/alertas/classificar
Content-Type: application/json

Body:
{
  "item": "AMARELO 1234",
  "tipo_movimentacao": "ENTRADA",
  "quantidade": 100
}

Response:
{
  "alerta": {
    "tipo": "atencao",
    "severidade": 2,
    "mensagem": "✨ Entrada de estoque detectada!",
    "sugestao": "📝 Verifique se o registro está correto...",
    "cor_hex": "#FFC107",
    "icone": "🟡"
  }
}
```

### **7. Alerta de Item Específico**
```http
GET /api/alertas/item/AMARELO%201234

Response:
{
  "alerta": {...},
  "existe": true
}
```

### **8. Estatísticas**
```http
GET /api/alertas/estatisticas

Response:
{
  "total_itens": 305,
  "media_dias_parado": 12.5,
  "max_dias_parado": 45,
  "porcentagem_critico": 4.9,
  "itens_criticos_top_10": [...],
  "grupos_mais_criticos": {
    "FIOS": 5,
    "TECIDOS": 3
  }
}
```

### **9. Invalidar Cache**
```http
POST /api/alertas/invalidar-cache

Response:
{
  "success": true,
  "message": "Cache de alertas invalidado"
}
```

### **10. Configurações**
```http
GET /api/alertas/configuracoes

Response:
{
  "thresholds": {
    "dias_critico": 20,
    "dias_atencao": 10,
    "dias_normal": 7
  },
  "cores": {
    "critico": "#F44336",
    "atencao": "#FFC107",
    "normal": "#4CAF50",
    "info": "#2196F3"
  },
  "icones": {...},
  "cache_ttl": 300
}
```

---

## 💻 USO PROGRAMÁTICO

### **Exemplo 1: Obter Dashboard**

```python
from alertas_config import gerenciador_alertas

# Obtém dashboard completo
dashboard = gerenciador_alertas.obter_dashboard()

print(f"Críticos: {dashboard['contadores']['critico']}")
print(f"Atenção: {dashboard['contadores']['atencao']}")
print(f"Total: {dashboard['contadores']['total']}")
```

### **Exemplo 2: Listar Críticos**

```python
from alertas_config import gerenciador_alertas

# Obtém apenas críticos
criticos = gerenciador_alertas.obter_alertas_criticos()

for alerta in criticos[:10]:
    print(f"{alerta.icone} {alerta.item}: {alerta.dias_parado} dias")
    print(f"   Sugestão: {alerta.sugestao}")
```

### **Exemplo 3: Classificar Movimentação**

```python
from alertas_config import gerenciador_alertas

# Classifica uma movimentação em tempo real
alerta = gerenciador_alertas.classificar_movimentacao(
    item='AMARELO 1234',
    tipo_movimentacao='ENTRADA',
    quantidade=100
)

print(f"{alerta.icone} {alerta.mensagem}")
print(f"Tipo: {alerta.tipo.value}")
print(f"Sugestão: {alerta.sugestao}")
```

### **Exemplo 4: Análise Completa**

```python
from alertas_config import gerenciador_alertas

# Analisa todos os itens
alertas = gerenciador_alertas.analisar_todos_itens()

# Separa por tipo
criticos = [a for a in alertas if a.tipo.value == 'critico']
atencao = [a for a in alertas if a.tipo.value == 'atencao']

print(f"Total: {len(alertas)}")
print(f"Críticos: {len(criticos)}")
print(f"Atenção: {len(atencao)}")

# Mostra top 5 críticos
for i, alerta in enumerate(criticos[:5], 1):
    print(f"\n{i}. {alerta.item} ({alerta.grupo})")
    print(f"   {alerta.dias_parado} dias sem movimentação")
    print(f"   Saldo: {alerta.saldo_atual}")
```

---

## ⚙️ CONFIGURAÇÕES

### **Thresholds (Limites)**

Em `alertas_config.py`:

```python
class ConfigAlerta:
    DIAS_CRITICO = 20   # >20 dias = crítico 🔴
    DIAS_ATENCAO = 10   # 10-20 dias = atenção 🟡
    DIAS_NORMAL = 7     # <7 dias = normal 🟢
```

**Personalize** esses valores conforme sua necessidade!

### **Cores**

```python
CORES = {
    TipoAlerta.CRITICO: '#F44336',  # Vermelho
    TipoAlerta.ATENCAO: '#FFC107',  # Amarelo
    TipoAlerta.NORMAL: '#4CAF50',   # Verde
    TipoAlerta.INFO: '#2196F3'      # Azul
}
```

### **Cache TTL**

```python
CACHE_TTL = 300  # 5 minutos
```

Altere para:
- `60` = 1 minuto (mais atualizado)
- `600` = 10 minutos (menos requisições)

---

## 🧪 TESTES

Execute os testes para validar:

```bash
python test_alertas.py
```

**8 testes incluídos:**
1. ✅ Cálculo de dias parados
2. ✅ Classificação por dias
3. ✅ Detecção de entrada de estoque
4. ✅ Criação de alerta completo
5. ✅ Dashboard
6. ✅ Alertas críticos
7. ✅ Classificação em tempo real
8. ✅ Configurações

**Resultado esperado:**
```
✅ Testes passados: 8/8
📊 Taxa de sucesso: 100.0%
✅ TODOS OS TESTES PASSARAM!
```

---

## 🎨 INTERFACE VISUAL

O arquivo `frontend_alertas.html` fornece:

- 📊 **Dashboard** com 4 cards coloridos
- 📋 **Tabela** de alertas com filtros
- 🔄 **Auto-refresh** a cada 5 minutos
- 🎨 **Material Design** responsivo
- 📱 **Mobile-friendly**

**Recursos:**
- Filtros por tipo (Todos, Críticos, Atenção, Normal)
- Tooltip com sugestões ao passar o mouse
- Badges coloridos por severidade
- Loading states
- Empty states bonitos

---

## 🔗 INTEGRAÇÃO COM SISTEMA EXISTENTE

### **Opção 1: Adicionar ao Dashboard Atual**

Em `app_final.py`, no endpoint `/api/dashboard`:

```python
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    # ... código existente ...

    # ADICIONA: Contadores de alertas
    from alertas_config import gerenciador_alertas
    dashboard_alertas = gerenciador_alertas.obter_dashboard()

    return jsonify({
        # ... dados existentes ...
        'alertas': dashboard_alertas['contadores'],
        'alertas_criticos': dashboard_alertas['top_criticos'][:5]
    })
```

### **Opção 2: Mostrar Alerta ao Inserir**

Em `app_final.py`, após inserir movimentação:

```python
from alertas_config import gerenciador_alertas

# Após inserir com sucesso
alerta = gerenciador_alertas.classificar_movimentacao(
    item=nome_item,
    tipo_movimentacao=tipo_movimentacao,
    quantidade=quantidade
)

# Retorna com alerta
return jsonify({
    'success': True,
    'message': 'Inserido com sucesso',
    'alerta': alerta.to_dict()  # NOVO!
})
```

### **Opção 3: Badge no Frontend**

Adicione no HTML do dashboard:

```html
<div class="alertas-badge">
    <span class="badge critico">🔴 <span id="count-critico">0</span></span>
    <span class="badge atencao">🟡 <span id="count-atencao">0</span></span>
</div>

<script>
fetch('/api/alertas/dashboard')
    .then(r => r.json())
    .then(data => {
        document.getElementById('count-critico').textContent = data.contadores.critico;
        document.getElementById('count-atencao').textContent = data.contadores.atencao;
    });
</script>
```

---

## 📊 BENEFÍCIOS

### **Para o Usuário**
- ✅ **Zero itens esquecidos** - Alerta automático
- ✅ **Decisões informadas** - Sugestões de ação
- ✅ **Visual claro** - Cores intuitivas
- ✅ **Priorização** - Foco no que importa

### **Para o Sistema**
- ⚡ **Performance** - Cache agressivo (5min TTL)
- 📊 **Escalável** - Suporta milhares de itens
- 🔧 **Configurável** - Thresholds personalizáveis
- 📈 **Métricas** - Estatísticas detalhadas

---

## 🎯 CASOS DE USO

### **1. Monitoramento Diário**

```python
# Script que roda todo dia às 9h (cron)
from alertas_config import gerenciador_alertas

dashboard = gerenciador_alertas.obter_dashboard()
criticos = dashboard['contadores']['critico']

if criticos > 0:
    # Envia email/notificação
    send_notification(f"⚠️ {criticos} itens críticos!")
```

### **2. Validação Pré-Inserção**

```python
# Antes de confirmar inserção
alerta = gerenciador_alertas.classificar_movimentacao(
    item=item,
    tipo_movimentacao='SAÍDA',
    quantidade=100
)

if alerta.tipo == TipoAlerta.CRITICO:
    # Mostra warning
    print(f"⚠️ {alerta.mensagem}")
    print(f"Sugestão: {alerta.sugestao}")
```

### **3. Relatório Semanal**

```python
# Gera relatório semanal
alertas = gerenciador_alertas.analisar_todos_itens()

relatorio = {
    'criticos': [a for a in alertas if a.tipo.value == 'critico'],
    'atencao': [a for a in alertas if a.tipo.value == 'atencao'],
    'total': len(alertas)
}

# Gera PDF, envia por email, etc.
```

---

## 🚨 TROUBLESHOOTING

### **Problema 1: "Nenhum alerta encontrado"**

**Causa:** Índice não foi construído ainda

**Solução:**
```python
from indice_otimizado import indice_otimizado
indice_otimizado.reconstruir_indice_completo()
```

### **Problema 2: Alertas desatualizados**

**Causa:** Cache antigo

**Solução:**
```python
from alertas_config import gerenciador_alertas
gerenciador_alertas.invalidar_cache()
```

Ou via API:
```bash
curl -X POST http://localhost:5000/api/alertas/invalidar-cache
```

### **Problema 3: Contadores errados**

**Causa:** Cache ou índice desatualizado

**Solução:**
```bash
# Invalida tudo
python -c "from cache_config import cache_marfim; cache_marfim.invalidate('*')"

# Reconstrói índice
python -c "from indice_otimizado import indice_otimizado; indice_otimizado.reconstruir_indice_completo()"

# Força recarga
curl "http://localhost:5000/api/alertas/dashboard?forcar_recarga=true"
```

---

## 📚 PRÓXIMOS PASSOS

### **Melhorias Futuras (Opcionais)**

1. **Notificações Push**
   - Email automático para críticos
   - SMS para alertas graves
   - Telegram/Slack integration

2. **Machine Learning**
   - Predição de itens que ficarão críticos
   - Clustering de padrões de consumo

3. **Histórico de Alertas**
   - Rastrear quando item entrou/saiu de crítico
   - Gráficos de evolução

4. **Ações Automatizadas**
   - Criar lista de compras automática
   - Sugerir promoções para parados

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [x] `alertas_config.py` criado
- [x] `alertas_integration.py` criado
- [x] `frontend_alertas.html` criado
- [x] `test_alertas.py` criado
- [x] Documentação completa
- [ ] Integrado em `app_final.py`
- [ ] Testes executados com sucesso
- [ ] Interface visual testada
- [ ] Usuário treinado

---

## 🎉 CONCLUSÃO

Você agora tem um **sistema profissional de alertas** que:

- 🔴 **Nunca** deixa itens críticos passarem despercebidos
- 🟡 **Detecta** entradas de estoque automaticamente
- 🟢 **Monitora** todo o estoque 24/7
- ⚡ **Funciona** super rápido (cache agressivo)
- 📊 **Mostra** métricas e estatísticas
- 🎨 **Interface** bonita e profissional

**Próximo passo:** Testar tudo! 🚀

```bash
python test_alertas.py
```

**Dúvidas?** Leia esta documentação ou explore os exemplos de código! 📖

---

**Criado com ❤️ por Johnny - 2026-02-13**
