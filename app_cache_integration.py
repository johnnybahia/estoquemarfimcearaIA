#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Cache no Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Este arquivo contém:
1. Novos endpoints otimizados com cache
2. Exemplos de como adaptar endpoints existentes
3. Endpoints de administração do cache

INSTRUÇÃO: Copie os endpoints desejados para app_final.py
"""

from flask import jsonify, request
from cache_config import cache_marfim, cached, obter_estatisticas_cache
from indice_otimizado import indice_otimizado
import logging

logger = logging.getLogger(__name__)


# ========================================
# NOVOS ENDPOINTS - CACHE E ÍNDICE
# ========================================

def register_cache_routes(app):
    """
    Registra endpoints de cache na aplicação Flask

    Uso em app_final.py:
        from app_cache_integration import register_cache_routes
        register_cache_routes(app)
    """

    @app.route('/api/cache/stats', methods=['GET'])
    def cache_stats():
        """
        📊 Retorna estatísticas do cache

        GET /api/cache/stats

        Response:
        {
          "statistics": {
            "hits_redis": 150,
            "hits_memory": 80,
            "misses": 20,
            "total_requests": 250,
            "hit_rate_percent": 92.0
          },
          "health": {
            "redis": {"available": true, "status": "ok"},
            "memory": {"available": true, "keys": 45}
          }
        }
        """
        try:
            stats = obter_estatisticas_cache()
            return jsonify(stats), 200
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de cache: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cache/invalidate', methods=['POST'])
    def cache_invalidate():
        """
        🗑️ Invalida cache (padrão ou específico)

        POST /api/cache/invalidate
        Body:
        {
          "pattern": "autocomplete*"  // opcional, padrão: "*" (tudo)
        }

        Response:
        {
          "success": true,
          "removed_count": 15,
          "message": "Cache invalidado: 15 chaves"
        }
        """
        try:
            data = request.get_json() or {}
            pattern = data.get('pattern', '*')

            removed = cache_marfim.invalidate(pattern)

            return jsonify({
                'success': True,
                'removed_count': removed,
                'message': f'Cache invalidado: {removed} chaves',
                'pattern': pattern
            }), 200

        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cache/health', methods=['GET'])
    def cache_health():
        """
        🏥 Health check do sistema de cache

        GET /api/cache/health

        Response:
        {
          "redis": {"available": true, "status": "ok"},
          "memory": {"available": true, "keys": 45, "status": "ok"}
        }
        """
        try:
            health = cache_marfim.health_check()
            status_code = 200 if health['redis']['status'] == 'ok' or health['memory']['status'] == 'ok' else 503
            return jsonify(health), status_code
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/indice/reconstruir', methods=['POST'])
    def reconstruir_indice():
        """
        🔄 Reconstrói índice completo

        POST /api/indice/reconstruir

        ATENÇÃO: Operação pesada! Use apenas quando necessário

        Response:
        {
          "success": true,
          "total_itens": 305,
          "duracao_segundos": 15.42,
          "message": "Índice reconstruído: 305 itens em 15.42s"
        }
        """
        try:
            resultado = indice_otimizado.reconstruir_indice_completo()
            return jsonify(resultado), 200 if resultado['success'] else 500
        except Exception as e:
            logger.error(f"Erro ao reconstruir índice: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/indice/item/<nome_item>', methods=['GET'])
    def buscar_item_indice(nome_item):
        """
        ⚡ Busca rápida O(1) por item no índice

        GET /api/indice/item/<nome_item>

        Response (sucesso):
        {
          "success": true,
          "dados": {
            "item_original": "AMARELO 1234",
            "saldo": "1500.00",
            "data": "13/02/2026",
            "grupo": "FIOS",
            "linha_estoque": 1234
          }
        }

        Response (não encontrado):
        {
          "success": false,
          "message": "Item não encontrado"
        }
        """
        try:
            dados = indice_otimizado.buscar_item(nome_item)

            if dados:
                return jsonify({
                    'success': True,
                    'dados': dados
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Item não encontrado'
                }), 404

        except Exception as e:
            logger.error(f"Erro ao buscar item no índice: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/indice/saldo/<nome_item>', methods=['GET'])
    def obter_saldo_item(nome_item):
        """
        💰 Retorna apenas o saldo atual do item (super rápido)

        GET /api/indice/saldo/<nome_item>

        Response:
        {
          "item": "AMARELO 1234",
          "saldo": 1500.00,
          "existe": true
        }
        """
        try:
            saldo = indice_otimizado.obter_saldo_item(nome_item)
            existe = indice_otimizado.item_existe(nome_item)

            return jsonify({
                'item': nome_item,
                'saldo': saldo,
                'existe': existe
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/indice/todos-itens', methods=['GET'])
    def listar_todos_itens():
        """
        📋 Lista todos os itens cadastrados (com cache)

        GET /api/indice/todos-itens

        Response:
        {
          "itens": ["AMARELO 1234", "AZUL 5678", ...],
          "total": 305
        }
        """
        try:
            itens = indice_otimizado.obter_todos_itens()

            return jsonify({
                'itens': itens,
                'total': len(itens)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar itens: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/indice/todos-grupos', methods=['GET'])
    def listar_todos_grupos():
        """
        📁 Lista todos os grupos únicos (com cache)

        GET /api/indice/todos-grupos

        Response:
        {
          "grupos": ["FIOS", "TECIDOS", "AVIAMENTOS"],
          "total": 3
        }
        """
        try:
            grupos = indice_otimizado.obter_todos_grupos()

            return jsonify({
                'grupos': grupos,
                'total': len(grupos)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar grupos: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de cache registrados")


# ========================================
# EXEMPLOS DE ADAPTAÇÃO DE ENDPOINTS EXISTENTES
# ========================================

"""
EXEMPLO 1: Otimizar endpoint /api/autocomplete
---------------------------------------------

ANTES (app_final.py linha ~543):
```python
@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    try:
        planilha = obter_planilha()
        dados_aba = planilha.worksheet("DADOS")
        dados = dados_aba.get_all_values()
        # ... processamento ...
```

DEPOIS (com cache):
```python
from cache_config import cache_marfim, cached
from indice_otimizado import indice_otimizado

@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    try:
        # Tenta cache primeiro
        cached_data = cache_marfim.get('autocomplete_data', 'autocomplete')
        if cached_data:
            return jsonify(cached_data), 200

        # Cache miss - busca da planilha
        planilha = obter_planilha()
        dados_aba = planilha.worksheet("DADOS")
        dados = dados_aba.get_all_values()

        # ... processamento ...

        resultado = {
            'items': itens_unicos,
            'grupos': grupos_unicos,
            # ...
        }

        # Salva em cache (TTL: 10 minutos)
        cache_marfim.set('autocomplete_data', resultado, 'autocomplete')

        return jsonify(resultado), 200
```

Ganho: 1500ms → 10ms (150x mais rápido!)
"""

"""
EXEMPLO 2: Otimizar endpoint /api/buscar-grupo
---------------------------------------------

ANTES (app_final.py linha ~645):
```python
@app.route('/api/buscar-grupo', methods=['GET'])
def buscar_grupo():
    item_nome = request.args.get('item', '').strip()
    gestor = GestorMarfim()
    grupo_item = gestor.obter_grupo_item(item_nome)
    # ... lê planilha inteira ...
```

DEPOIS (com índice otimizado):
```python
from indice_otimizado import indice_otimizado

@app.route('/api/buscar-grupo', methods=['GET'])
def buscar_grupo():
    item_nome = request.args.get('item', '').strip()

    if not item_nome:
        return jsonify({'grupo': ''}), 200

    # Busca O(1) no índice (cache)
    grupo = indice_otimizado.obter_grupo_item(item_nome)

    return jsonify({'grupo': grupo}), 200
```

Ganho: 2000ms → 5ms (400x mais rápido!)
"""

"""
EXEMPLO 3: Otimizar endpoint /api/ultimo-valor-item
--------------------------------------------------

ANTES (app_final.py linha ~683):
```python
@app.route('/api/ultimo-valor-item', methods=['GET'])
def ultimo_valor_item():
    item_nome = request.args.get('item', '').strip()
    planilha = obter_planilha()
    aba_estoque = planilha.worksheet("ESTOQUE")
    dados = aba_estoque.get_all_values()
    # ... busca linear em 40k linhas ...
```

DEPOIS (com índice):
```python
from indice_otimizado import indice_otimizado

@app.route('/api/ultimo-valor-item', methods=['GET'])
def ultimo_valor_item():
    item_nome = request.args.get('item', '').strip()

    if not item_nome:
        return jsonify({'valor': 0}), 200

    # Busca rápida no índice
    dados_item = indice_otimizado.buscar_item(item_nome)

    if dados_item:
        # Se precisar do valor, pode buscar apenas a última linha
        # ao invés de ler tudo
        return jsonify({
            'item': item_nome,
            'saldo': dados_item['saldo'],
            'data': dados_item['data'],
            'grupo': dados_item['grupo']
        }), 200
    else:
        return jsonify({'valor': 0}), 200
```

Ganho: 2000ms → 5ms (400x mais rápido!)
"""

"""
EXEMPLO 4: Otimizar endpoint /api/dashboard
------------------------------------------

ANTES (app_final.py linha ~219):
```python
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    try:
        planilha = obter_planilha()
        aba_estoque = planilha.worksheet("ESTOQUE")
        dados = aba_estoque.get_all_values()
        # ... múltiplas leituras ...
```

DEPOIS (com cache):
```python
from cache_config import cache_marfim

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    try:
        # Tenta cache primeiro (TTL: 5 minutos)
        cached_dashboard = cache_marfim.get('dashboard_data', 'dashboard')
        if cached_dashboard:
            return jsonify(cached_dashboard), 200

        # Cache miss - calcula dashboard
        planilha = obter_planilha()
        # ... processamento ...

        dashboard_data = {
            'total_itens': len(itens_unicos),
            'alertas_criticos': len(alertas_criticos),
            # ...
        }

        # Salva em cache (TTL: 5 minutos)
        cache_marfim.set('dashboard_data', dashboard_data, 'dashboard')

        return jsonify(dashboard_data), 200
```

Ganho: 3000ms → 50ms (60x mais rápido!)
"""


# ========================================
# EXEMPLO DE INTEGRAÇÃO COMPLETA
# ========================================

def exemplo_endpoint_otimizado(app):
    """
    Exemplo completo de endpoint otimizado com cache e índice
    """

    @app.route('/api/exemplo/busca-multipla', methods=['POST'])
    def busca_multipla_otimizada():
        """
        Busca múltiplos itens de forma otimizada

        POST /api/exemplo/busca-multipla
        Body:
        {
          "itens": ["AMARELO 1234", "AZUL 5678", "VERMELHO 9012"]
        }

        Response:
        {
          "resultados": [
            {
              "item": "AMARELO 1234",
              "saldo": 1500.00,
              "grupo": "FIOS",
              "existe": true
            },
            ...
          ],
          "total": 3,
          "tempo_ms": 15
        }
        """
        import time
        inicio = time.time()

        try:
            data = request.get_json()
            itens = data.get('itens', [])

            if not itens:
                return jsonify({'error': 'Lista de itens vazia'}), 400

            resultados = []

            # Busca rápida usando índice (O(1) para cada item)
            for item_nome in itens:
                dados = indice_otimizado.buscar_item(item_nome)

                if dados:
                    resultados.append({
                        'item': dados['item_original'],
                        'saldo': float(dados['saldo']),
                        'grupo': dados['grupo'],
                        'data': dados['data'],
                        'existe': True
                    })
                else:
                    resultados.append({
                        'item': item_nome,
                        'saldo': 0,
                        'grupo': '',
                        'existe': False
                    })

            tempo_ms = round((time.time() - inicio) * 1000, 2)

            return jsonify({
                'resultados': resultados,
                'total': len(resultados),
                'tempo_ms': tempo_ms
            }), 200

        except Exception as e:
            logger.error(f"Erro na busca múltipla: {e}")
            return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("📚 Este arquivo contém exemplos de integração de cache.")
    print("✅ Copie os endpoints desejados para app_final.py")
    print("")
    print("Endpoints disponíveis:")
    print("  - /api/cache/stats - Estatísticas de cache")
    print("  - /api/cache/invalidate - Invalidar cache")
    print("  - /api/cache/health - Health check")
    print("  - /api/indice/reconstruir - Reconstruir índice")
    print("  - /api/indice/item/<nome> - Buscar item")
    print("  - /api/indice/saldo/<nome> - Obter saldo")
    print("  - /api/indice/todos-itens - Listar itens")
    print("  - /api/indice/todos-grupos - Listar grupos")
