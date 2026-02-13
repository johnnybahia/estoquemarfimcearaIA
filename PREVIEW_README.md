# 👁️ Sistema de Preview de Saldos - Marfim Estoque

> **Veja antes de confirmar!** Zero inserções erradas.

---

## 🎯 O QUE É?

Sistema que mostra **preview do saldo ANTES** de confirmar movimentação:

- 👁️ **Saldo atual** (busca instantânea do índice)
- 🔢 **Novo saldo** (calculado automaticamente)
- ⚠️ **Alertas** se ficará negativo
- ✅ **Validação** antes de inserir

---

## ✨ FUNCIONALIDADES

### **1. Cálculo Automático**
- ✅ Busca saldo atual do índice (O(1))
- ✅ Calcula novo saldo baseado no tipo
- ✅ Detecta se ficará negativo
- ✅ Alertas configuráveis

### **2. 4 Status Possíveis**

| Status | Situação | Pode Confirmar? |
|--------|----------|-----------------|
| ✅ **OK** | Saldo normal | Sim |
| ⚠️ **ATENÇÃO** | Saldo baixo (<10) | Sim |
| 🔴 **CRÍTICO** | Saldo negativo | Não* |
| 🆕 **ITEM_NOVO** | Item não existe | Sim |

*Configurável via `PERMITIR_SALDO_NEGATIVO`

### **3. API Completa**
- 5 endpoints RESTful
- Preview individual e em lote
- Validação pré-inserção

### **4. Interface Visual**
- Modal bonito com animações
- Comparação visual (antes → depois)
- Cores intuitivas

---

## 📂 ARQUIVOS CRIADOS

```
preview_saldos.py            # Lógica de cálculo (350 linhas)
preview_integration.py       # Endpoints Flask (200 linhas)
frontend_preview.html        # Interface visual (300 linhas)
PREVIEW_README.md            # Esta documentação
```

**Total:** ~850 linhas! 🎉

---

## 🚀 COMO USAR

### **1. Integrar no Flask**

```python
# Em app_final.py
from preview_integration import register_preview_routes

register_preview_routes(app)
```

### **2. Usar Programaticamente**

```python
from preview_saldos import gerenciador_preview

# Calcula preview
preview = gerenciador_preview.calcular_preview(
    item='AMARELO 1234',
    tipo_movimentacao='SAIDA',
    quantidade=100
)

print(f"Saldo atual: {preview.saldo_atual}")
print(f"Novo saldo: {preview.novo_saldo}")
print(f"Pode confirmar: {preview.pode_confirmar}")

if preview.alerta:
    print(f"⚠️ {preview.alerta}")
```

### **3. Validar Antes de Inserir**

```python
from preview_saldos import validar_antes_inserir

if validar_antes_inserir('ITEM', 'SAIDA', 999):
    # OK, pode inserir
    inserir_movimentacao(...)
else:
    # Mostra alerta
    print("⚠️ Movimentação não permitida!")
```

---

## 📡 API ENDPOINTS

### **1. Calcular Preview**
```http
POST /api/preview/calcular
Content-Type: application/json

{
  "item": "AMARELO 1234",
  "tipo_movimentacao": "SAIDA",
  "quantidade": 100
}

Response:
{
  "preview": {
    "saldo_atual": 250.0,
    "novo_saldo": 150.0,
    "diferenca": -100.0,
    "status": "ok",
    "mensagem": "✅ Saída de estoque: 250.0 → 150.0 (-100.0)",
    "pode_confirmar": true,
    "recomendacao": "✅ Tudo certo! Pode confirmar."
  }
}
```

### **2. Validar Movimentação**
```http
POST /api/preview/validar

{
  "item": "AMARELO 1234",
  "tipo_movimentacao": "SAIDA",
  "quantidade": 300
}

Response (se saldo insuficiente):
{
  "valido": false,
  "motivo": "⚠️ SALDO FICARÁ NEGATIVO (-50)!",
  "preview": {...}
}
```

### **3. Preview em Lote**
```http
POST /api/preview/lote

{
  "movimentacoes": [
    {"item": "ITEM1", "tipo_movimentacao": "SAIDA", "quantidade": 50},
    {"item": "ITEM2", "tipo_movimentacao": "ENTRADA", "quantidade": 100}
  ]
}

Response:
{
  "previews": [...],
  "total": 2,
  "validos": 2,
  "invalidos": 0
}
```

### **4. Obter Saldo**
```http
GET /api/preview/saldo/AMARELO%201234

Response:
{
  "item": "AMARELO 1234",
  "saldo_atual": 250.0,
  "grupo": "FIOS",
  "existe": true
}
```

### **5. Configurações**
```http
GET /api/preview/configuracoes

Response:
{
  "saldo_minimo_atencao": 10,
  "permitir_saldo_negativo": false,
  "cache_ttl": 60
}
```

---

## ⚙️ CONFIGURAÇÕES

Em `preview_saldos.py`:

```python
class ConfigPreview:
    SALDO_MINIMO_ATENCAO = 10        # Abaixo disso = ⚠️
    PERMITIR_SALDO_NEGATIVO = False  # Se False, bloqueia negativo
    CACHE_TTL = 60                   # 1 minuto
```

**Personalize conforme necessário!**

---

## 🎨 INTEGRAÇÃO NO FRONTEND EXISTENTE

### **Opção 1: Modal de Confirmação**

```javascript
async function inserirComPreview(item, tipo, quantidade) {
    // 1. Calcula preview
    const response = await fetch('/api/preview/calcular', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({item, tipo_movimentacao: tipo, quantidade})
    });

    const {preview} = await response.json();

    // 2. Mostra modal de confirmação
    if (confirm(`${preview.mensagem}\n\nConfirmar?`)) {
        // 3. Insere
        inserirMovimentacao(item, tipo, quantidade);
    }
}
```

### **Opção 2: Preview Automático ao Digitar**

```javascript
// Ao mudar quantidade, mostra preview em tempo real
document.getElementById('quantidade').addEventListener('input', async (e) => {
    const item = document.getElementById('item').value;
    const tipo = document.getElementById('tipo').value;
    const quantidade = e.target.value;

    if (item && quantidade) {
        const preview = await calcularPreview(item, tipo, quantidade);

        // Atualiza UI
        document.getElementById('preview-saldo-novo').textContent = preview.novo_saldo;

        if (!preview.pode_confirmar) {
            mostrarAlerta(preview.alerta);
        }
    }
});
```

### **Opção 3: Badge de Status**

```html
<div class="saldo-preview" style="margin-top: 10px;">
    <span id="status-badge" class="badge"></span>
    <span id="saldo-info"></span>
</div>

<script>
function atualizarPreview(preview) {
    const badge = document.getElementById('status-badge');
    const info = document.getElementById('saldo-info');

    // Cor do badge
    badge.className = `badge ${preview.status}`;
    badge.textContent = preview.status.toUpperCase();

    // Mensagem
    info.textContent = `${preview.saldo_atual} → ${preview.novo_saldo}`;
}
</script>
```

---

## 💡 EXEMPLOS DE USO

### **Exemplo 1: Validação Pré-Inserção**

```python
# Antes de inserir na planilha
preview = gerenciador_preview.calcular_preview(
    item=nome_item,
    tipo_movimentacao=tipo,
    quantidade=qtd
)

if not preview.pode_confirmar:
    return jsonify({
        'success': False,
        'error': preview.alerta,
        'preview': preview.to_dict()
    }), 400

# Se passou, insere normalmente
inserir_na_planilha(...)
```

### **Exemplo 2: Lote com Validação**

```python
movimentacoes = [
    {'item': 'ITEM1', 'tipo_movimentacao': 'SAIDA', 'quantidade': 50},
    {'item': 'ITEM2', 'tipo_movimentacao': 'ENTRADA', 'quantidade': 100}
]

previews = gerenciador_preview.calcular_preview_lote(movimentacoes)

# Filtra apenas válidos
validos = [p for p in previews if p.pode_confirmar]

if len(validos) < len(previews):
    print(f"⚠️ {len(previews) - len(validos)} movimentações inválidas!")

# Insere apenas válidos
for preview in validos:
    inserir_movimentacao(...)
```

### **Exemplo 3: Alerta em Tempo Real**

```python
@app.route('/api/inserir-com-preview', methods=['POST'])
def inserir_com_preview():
    data = request.get_json()

    # Calcula preview primeiro
    preview = gerenciador_preview.calcular_preview(
        item=data['item'],
        tipo_movimentacao=data['tipo'],
        quantidade=data['quantidade']
    )

    # Se crítico, retorna preview sem inserir
    if preview.status == StatusPreview.CRITICO:
        return jsonify({
            'success': False,
            'preview_required': True,
            'preview': preview.to_dict()
        }), 400

    # Se OK ou ATENÇÃO, insere normalmente
    resultado = inserir_movimentacao(...)

    return jsonify({
        'success': True,
        'preview': preview.to_dict(),
        'resultado': resultado
    })
```

---

## 🔗 INTEGRAÇÃO COMPLETA

### **Fluxo Recomendado:**

1. **Usuário preenche formulário** → Item, Tipo, Quantidade
2. **Sistema calcula preview** → Mostra saldo antes/depois
3. **Usuário confirma** → Se OK, insere; se não, corrige
4. **Sistema insere** → Atualiza planilha e índice
5. **Feedback visual** → Mostra sucesso com novo saldo

### **Código Exemplo:**

```javascript
async function inserirMovimentacaoComPreview() {
    // 1. Coleta dados
    const dados = {
        item: document.getElementById('item').value,
        tipo_movimentacao: document.getElementById('tipo').value,
        quantidade: parseFloat(document.getElementById('quantidade').value)
    };

    // 2. Calcula preview
    const previewResp = await fetch('/api/preview/calcular', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    });

    const {preview} = await previewResp.json();

    // 3. Mostra modal de confirmação
    if (!await mostrarModalPreview(preview)) {
        return; // Usuário cancelou
    }

    // 4. Insere (seu endpoint existente)
    const insertResp = await fetch('/api/inserir', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    });

    const resultado = await insertResp.json();

    // 5. Feedback
    if (resultado.success) {
        alert(`✅ Inserido! Novo saldo: ${preview.novo_saldo}`);
    }
}
```

---

## 📊 BENEFÍCIOS

### **Antes (sem preview):**
- ❌ Inserções erradas (ENTRADA ↔ SAÍDA trocados)
- ❌ Saldos negativos acidentais
- ❌ Descoberta após inserir
- ❌ Necessário deletar e reinserir

### **Agora (com preview):**
- ✅ **Zero inserções erradas**
- ✅ **Validação visual** antes de confirmar
- ✅ **Alertas automáticos** para problemas
- ✅ **Confiança** ao inserir
- ✅ **Economia de tempo** (sem correções)

---

## 🎯 CASOS DE USO

1. **Entrada vs Saída** - Usuário vê na hora se trocou
2. **Saldo insuficiente** - Sistema bloqueia antes de inserir
3. **Item novo** - Alerta que está criando item
4. **Validação de lote** - Valida 10+ movimentações de uma vez

---

## ✅ RESUMO

**3 arquivos criados** + documentação = Sistema completo de preview!

**Para usar:**
1. Integre em Flask: `register_preview_routes(app)`
2. Use nos endpoints de inserção
3. Opcionalmente, adicione frontend visual

**Resultado:** Zero erros de inserção! 🎯

---

**Criado com ❤️ por Johnny - 2026-02-13**
