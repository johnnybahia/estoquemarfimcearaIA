# 📊 Sistema de Relatórios Inteligentes - Marfim Estoque

> **Veja tudo em um clique!** Curva ABC, gráficos e export Excel/PDF.

---

## 🎯 O QUE É?

Sistema completo de relatórios com:

- 📊 **Curva ABC** automática (classificação por volume)
- 📈 **Gráficos interativos** (Chart.js)
- 📦 **Resumo por grupos**
- ⏸️ **Itens parados** (sem movimento há 30+ dias)
- 📥 **Export Excel** (5 abas: resumo, ABC, grupos, parados, top)
- 📄 **Export PDF** (relatório formatado)
- 🏆 **Top 10 mais movimentados**

---

## ✨ FUNCIONALIDADES

### **1. Curva ABC**

**Classificação por volume de movimentações:**

| Classe | % do Volume | Prioridade | Ação |
|--------|------------|------------|------|
| **A** | 80% | Máxima | Monitorar diariamente |
| **B** | 15% | Média | Monitorar semanalmente |
| **C** | 5% | Baixa | Monitorar mensalmente |

**Como funciona:**
1. Soma entradas + saídas de cada item
2. Ordena do maior para o menor volume
3. Calcula percentual acumulado
4. Classifica: A (até 80%), B (até 95%), C (restante)

### **2. Períodos Disponíveis**

| Período | Intervalo |
|---------|-----------|
| Hoje | Data atual |
| Semana | Últimos 7 dias |
| Mês | Últimos 30 dias |
| Trimestre | Últimos 90 dias |
| Personalizado | Data início/fim |

### **3. Export Excel (5 abas)**

| Aba | Conteúdo |
|----|----------|
| 📊 Resumo | KPIs gerais |
| 🔤 Curva ABC | Todos os itens classificados |
| 📦 Por Grupos | Resumo por grupo |
| ⏸️ Itens Parados | Sem movimento 30+ dias |
| 🏆 Top Movimentados | Top 10 por volume |

### **4. Export PDF**

- Título + data de geração
- Resumo geral em tabela
- Curva ABC resumida
- Top 10 mais movimentados
- Lista de itens parados

---

## 📂 ARQUIVOS CRIADOS

```
relatorios.py                  # Lógica de relatórios (600 linhas)
relatorios_integration.py      # Endpoints Flask (200 linhas)
frontend_relatorios.html       # Interface com gráficos (350 linhas)
RELATORIOS_README.md           # Esta documentação
```

**Total:** ~1.150 linhas!

---

## 🚀 COMO USAR

### **1. Integrar no Flask**

```python
from relatorios_integration import register_relatorios_routes
register_relatorios_routes(app)
```

### **2. Instalar Dependências**

```bash
pip install openpyxl fpdf2
```

### **3. Gerar Relatório**

```python
from relatorios import gerenciador_relatorios

# Relatório mensal
relatorio = gerenciador_relatorios.gerar_relatorio_completo('mes')

print(f"Total itens: {relatorio.total_itens}")
print(f"Classe A: {len(relatorio.curva_abc['A'])} itens")
print(f"Parados: {relatorio.itens_sem_movimento}")
```

### **4. Curva ABC**

```python
curva = gerenciador_relatorios.calcular_curva_abc()

for classe in ['A', 'B', 'C']:
    itens = curva[classe]
    print(f"Classe {classe}: {len(itens)} itens")
    for item in itens[:3]:
        print(f"  - {item.item}: {item.volume_total:.0f} vol ({item.percentual_volume:.1f}%)")
```

### **5. Exportar Excel**

```python
relatorio = gerenciador_relatorios.gerar_relatorio_completo('mes')
excel_bytes = gerenciador_relatorios.exportar_excel(relatorio)

with open('relatorio.xlsx', 'wb') as f:
    f.write(excel_bytes)
```

### **6. Exportar PDF**

```python
pdf_bytes = gerenciador_relatorios.exportar_pdf(relatorio)

with open('relatorio.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

---

## 📡 API ENDPOINTS (8 novos!)

### **1. Relatório Completo**
```http
GET /api/relatorios/completo?periodo=mes

Response: objeto completo com curva ABC, gráficos, grupos, parados
```

### **2. Curva ABC**
```http
GET /api/relatorios/curva-abc?classe=A

Response:
{
  "curva_abc": { "A": [...] },
  "resumo": { "total_itens": 150, "classe_a": 10, "classe_b": 30, "classe_c": 110 }
}
```

### **3. Resumo por Grupos**
```http
GET /api/relatorios/grupos

Response:
{
  "grupos": [ { "grupo": "FIOS", "total_itens": 25, "saldo_total": 8500, ... } ],
  "total": 12
}
```

### **4. Itens Parados**
```http
GET /api/relatorios/itens-parados?dias=30

Response:
{
  "itens_parados": [...],
  "total": 18,
  "dias_referencia": 30
}
```

### **5. Export Excel**
```http
GET /api/relatorios/exportar/excel?periodo=mes
→ Download relatorio_marfim_mes_2026-02-13.xlsx
```

### **6. Export PDF**
```http
GET /api/relatorios/exportar/pdf?periodo=mes
→ Download relatorio_marfim_mes_2026-02-13.pdf
```

### **7. Dados de Gráficos**
```http
GET /api/relatorios/graficos?periodo=mes

Response:
{
  "grafico_abc": { "type": "doughnut", "labels": [...], "data": [...] },
  "grafico_grupos": { "type": "bar", "labels": [...], "datasets": [...] },
  "grafico_movimentacoes": { "type": "line", "labels": [...], "datasets": [...] }
}
```

### **8. Configurações**
```http
GET /api/relatorios/configuracoes

Response:
{
  "limite_classe_a": 80.0,
  "limite_classe_b": 95.0,
  "dias_sem_movimento_parado": 30,
  "top_n_movimentados": 10
}
```

---

## 💡 INTEGRAÇÃO COMPLETA (6 FASES)

```python
# Em app_final.py — uma linha por fase
from app_cache_integration      import register_cache_routes       # F1
from alertas_integration        import register_alertas_routes     # F2
from preview_integration        import register_preview_routes     # F3
from historico_integration      import register_historico_routes   # F4
from ia_integration             import register_ia_routes          # F5
from relatorios_integration     import register_relatorios_routes  # F6 ⭐

register_cache_routes(app)
register_alertas_routes(app)
register_preview_routes(app)
register_historico_routes(app)
register_ia_routes(app)
register_relatorios_routes(app)  # ⭐
```

**41 endpoints disponíveis!**

---

## ⚙️ CONFIGURAÇÕES

```python
class ConfigRelatorios:
    LIMITE_CLASSE_A = 80.0          # % para classe A
    LIMITE_CLASSE_B = 95.0          # % para classe B
    DIAS_SEM_MOVIMENTO_PARADO = 30  # Dias = parado
    TOP_N_MOVIMENTADOS = 10         # Top N itens
```

---

## 📊 BENEFÍCIOS

| Antes | Agora |
|-------|-------|
| ❌ Análise manual em planilha | ✅ Relatório automático em 1 clique |
| ❌ Sem classificação ABC | ✅ Curva ABC calculada automaticamente |
| ❌ Sem gráficos | ✅ 3 gráficos interativos |
| ❌ Export manual | ✅ Excel + PDF em 1 clique |
| ❌ Itens parados invisíveis | ✅ Lista de parados com dias |

---

**Criado com ❤️ por Johnny - 2026-02-13**
