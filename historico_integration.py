#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Histórico com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para histórico otimizado com cache.

INSTRUÇÃO: Adicione ao app_final.py com:
    from historico_integration import register_historico_routes
    register_historico_routes(app)
"""

from flask import jsonify, request
from historico_otimizado import gerenciador_historico, ConfigHistorico
import logging

logger = logging.getLogger(__name__)


def register_historico_routes(app):
    """
    Registra endpoints de histórico na aplicação Flask

    Uso em app_final.py:
        from historico_integration import register_historico_routes
        register_historico_routes(app)
    """

    @app.route('/api/historico/ultimos', methods=['GET'])
    def obter_ultimos():
        """
        📚 Obtém últimos N registros do histórico

        GET /api/historico/ultimos?limite=20

        Query Params:
        - limite: int (opcional, padrão: 20, max: 100)

        Response:
        {
          "registros": [
            {
              "item": "AMARELO 1234",
              "grupo": "FIOS",
              "tipo_movimentacao": "SAIDA",
              "quantidade": 100,
              "saldo_anterior": 250.0,
              "saldo_novo": 150.0,
              "data": "13/02/2026",
              "hora": "10:30:00",
              "linha_planilha": 45,
              "usuario": "Johnny",
              "timestamp": "2026-02-13T10:30:00"
            }
          ],
          "total": 1
        }
        """
        try:
            # Obtém limite
            limite = request.args.get('limite', 20, type=int)
            limite = min(limite, 100)  # Max 100

            # Busca registros
            registros = gerenciador_historico.obter_ultimos(limite)

            return jsonify({
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter últimos: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/item/<item_nome>', methods=['GET'])
    def obter_por_item(item_nome):
        """
        🔍 Busca histórico de um item específico

        GET /api/historico/item/<item_nome>?limite=20

        Query Params:
        - limite: int (opcional, None = todos)

        Response:
        {
          "item": "AMARELO 1234",
          "registros": [...],
          "total": 5
        }
        """
        try:
            limite = request.args.get('limite', type=int)

            registros = gerenciador_historico.buscar_por_item(item_nome, limite)

            return jsonify({
                'item': item_nome,
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao buscar item: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/grupo/<grupo_nome>', methods=['GET'])
    def obter_por_grupo(grupo_nome):
        """
        📦 Busca histórico de um grupo

        GET /api/historico/grupo/<grupo_nome>?limite=20

        Response:
        {
          "grupo": "FIOS",
          "registros": [...],
          "total": 10
        }
        """
        try:
            limite = request.args.get('limite', type=int)

            registros = gerenciador_historico.buscar_por_grupo(grupo_nome, limite)

            return jsonify({
                'grupo': grupo_nome,
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao buscar grupo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/tipo/<tipo_movimentacao>', methods=['GET'])
    def obter_por_tipo(tipo_movimentacao):
        """
        ⬆️⬇️ Busca por tipo de movimentação (ENTRADA/SAIDA)

        GET /api/historico/tipo/<tipo_movimentacao>?limite=20

        Tipos válidos: entrada, saida, ENTRADA, SAIDA

        Response:
        {
          "tipo": "SAIDA",
          "registros": [...],
          "total": 8
        }
        """
        try:
            limite = request.args.get('limite', type=int)

            registros = gerenciador_historico.buscar_por_tipo(tipo_movimentacao, limite)

            return jsonify({
                'tipo': tipo_movimentacao.upper(),
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao buscar tipo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/periodo', methods=['GET'])
    def obter_por_periodo():
        """
        📅 Busca histórico por período de datas

        GET /api/historico/periodo?data_inicio=01/02/2026&data_fim=13/02/2026&limite=50

        Query Params:
        - data_inicio: str (DD/MM/YYYY) - obrigatório
        - data_fim: str (DD/MM/YYYY) - obrigatório
        - limite: int (opcional)

        Response:
        {
          "data_inicio": "01/02/2026",
          "data_fim": "13/02/2026",
          "registros": [...],
          "total": 15
        }
        """
        try:
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            limite = request.args.get('limite', type=int)

            if not data_inicio or not data_fim:
                return jsonify({
                    'error': 'Parâmetros obrigatórios: data_inicio, data_fim (DD/MM/YYYY)'
                }), 400

            registros = gerenciador_historico.buscar_por_periodo(
                data_inicio, data_fim, limite
            )

            return jsonify({
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao buscar período: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/hoje', methods=['GET'])
    def obter_hoje():
        """
        📆 Busca registros de hoje

        GET /api/historico/hoje

        Response:
        {
          "data": "13/02/2026",
          "registros": [...],
          "total": 3
        }
        """
        try:
            from datetime import datetime

            registros = gerenciador_historico.buscar_hoje()

            return jsonify({
                'data': datetime.now().strftime('%d/%m/%Y'),
                'registros': [r.to_dict() for r in registros],
                'total': len(registros)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao buscar hoje: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/paginado', methods=['GET'])
    def obter_paginado():
        """
        📄 Obtém histórico com paginação e filtros

        GET /api/historico/paginado?pagina=1&por_pagina=20&item=AMARELO&grupo=FIOS&tipo=SAIDA

        Query Params:
        - pagina: int (padrão: 1)
        - por_pagina: int (padrão: 20, max: 100)
        - item: str (opcional) - filtro parcial
        - grupo: str (opcional) - filtro parcial
        - tipo: str (opcional) - ENTRADA ou SAIDA
        - data_inicio: str (opcional, DD/MM/YYYY)
        - data_fim: str (opcional, DD/MM/YYYY)

        Response:
        {
          "registros": [...],
          "total": 45,
          "pagina": 1,
          "total_paginas": 3,
          "tem_proxima": true,
          "tem_anterior": false,
          "filtros_aplicados": {
            "item": "AMARELO",
            "grupo": "FIOS"
          }
        }
        """
        try:
            # Parâmetros de paginação
            pagina = request.args.get('pagina', 1, type=int)
            por_pagina = request.args.get('por_pagina', 20, type=int)
            por_pagina = min(por_pagina, 100)  # Max 100

            # Filtros
            filtros = {}
            if request.args.get('item'):
                filtros['item'] = request.args.get('item')
            if request.args.get('grupo'):
                filtros['grupo'] = request.args.get('grupo')
            if request.args.get('tipo'):
                filtros['tipo'] = request.args.get('tipo')
            if request.args.get('data_inicio') and request.args.get('data_fim'):
                filtros['data_inicio'] = request.args.get('data_inicio')
                filtros['data_fim'] = request.args.get('data_fim')

            # Busca paginada
            resultado = gerenciador_historico.obter_paginado(
                pagina=pagina,
                por_pagina=por_pagina,
                filtros=filtros if filtros else None
            )

            # Adiciona filtros ao response
            response = resultado.to_dict()
            if filtros:
                response['filtros_aplicados'] = filtros

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Erro ao obter paginado: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/adicionar', methods=['POST'])
    def adicionar_registro():
        """
        ➕ Adiciona novo registro ao histórico

        POST /api/historico/adicionar
        Body:
        {
          "item": "AMARELO 1234",
          "tipo_movimentacao": "SAIDA",
          "quantidade": 100,
          "saldo_anterior": 250,
          "saldo_novo": 150,
          "grupo": "FIOS",
          "linha_planilha": 45,
          "usuario": "Johnny",
          "observacao": "Venda"
        }

        Campos obrigatórios: item, tipo_movimentacao, quantidade, saldo_anterior, saldo_novo

        Response:
        {
          "success": true,
          "registro": {...}
        }
        """
        try:
            data = request.get_json()

            # Valida campos obrigatórios
            required = ['item', 'tipo_movimentacao', 'quantidade', 'saldo_anterior', 'saldo_novo']
            if not all(k in data for k in required):
                return jsonify({
                    'error': f'Campos obrigatórios: {", ".join(required)}'
                }), 400

            # Adiciona registro
            registro = gerenciador_historico.adicionar_registro(
                item=data['item'],
                tipo_movimentacao=data['tipo_movimentacao'],
                quantidade=float(data['quantidade']),
                saldo_anterior=float(data['saldo_anterior']),
                saldo_novo=float(data['saldo_novo']),
                grupo=data.get('grupo', ''),
                linha_planilha=data.get('linha_planilha'),
                usuario=data.get('usuario'),
                observacao=data.get('observacao')
            )

            return jsonify({
                'success': True,
                'registro': registro.to_dict()
            }), 201

        except ValueError as e:
            return jsonify({'error': f'Valor inválido: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Erro ao adicionar registro: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/estatisticas', methods=['GET'])
    def obter_estatisticas():
        """
        📊 Obtém estatísticas do cache de histórico

        GET /api/historico/estatisticas

        Response:
        {
          "tamanho_cache": 45,
          "tamanho_max": 100,
          "total_adicionado": 120,
          "total_buscas": 50,
          "cache_hits": 40,
          "cache_misses": 10,
          "hit_rate": "80.00%",
          "indices": {
            "itens": 15,
            "grupos": 5
          }
        }
        """
        try:
            stats = gerenciador_historico.obter_estatisticas()
            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/limpar', methods=['POST'])
    def limpar_cache():
        """
        🗑️ Limpa todo o cache de histórico

        POST /api/historico/limpar

        Response:
        {
          "success": true,
          "message": "Cache de histórico limpo"
        }
        """
        try:
            gerenciador_historico.limpar_cache()

            return jsonify({
                'success': True,
                'message': 'Cache de histórico limpo'
            }), 200

        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/carregar-redis', methods=['POST'])
    def carregar_redis():
        """
        💾 Carrega cache do Redis (backup)

        POST /api/historico/carregar-redis

        Response:
        {
          "success": true,
          "registros_carregados": 45
        }
        """
        try:
            count = gerenciador_historico.carregar_do_redis()

            return jsonify({
                'success': True,
                'registros_carregados': count
            }), 200

        except Exception as e:
            logger.error(f"Erro ao carregar do Redis: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/historico/configuracoes', methods=['GET'])
    def obter_configuracoes():
        """
        ⚙️ Retorna configurações do histórico

        GET /api/historico/configuracoes

        Response:
        {
          "tamanho_max_cache": 100,
          "tamanho_padrao_cache": 50,
          "registros_por_pagina": 20,
          "cache_ttl": 300,
          "usar_indice_memoria": true,
          "thread_safe": true
        }
        """
        try:
            config = {
                'tamanho_max_cache': ConfigHistorico.TAMANHO_MAX_CACHE,
                'tamanho_padrao_cache': ConfigHistorico.TAMANHO_PADRAO_CACHE,
                'registros_por_pagina': ConfigHistorico.REGISTROS_POR_PAGINA,
                'cache_ttl': ConfigHistorico.CACHE_TTL,
                'usar_indice_memoria': ConfigHistorico.USAR_INDICE_MEMORIA,
                'thread_safe': ConfigHistorico.THREAD_SAFE
            }

            return jsonify(config), 200

        except Exception as e:
            logger.error(f"Erro ao obter configurações: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de histórico registrados")


if __name__ == '__main__':
    print("📚 Este arquivo contém endpoints de histórico para Flask")
    print("✅ Use register_historico_routes(app) em app_final.py")
    print("")
    print("Endpoints disponíveis:")
    print("  - GET  /api/historico/ultimos")
    print("  - GET  /api/historico/item/<nome>")
    print("  - GET  /api/historico/grupo/<nome>")
    print("  - GET  /api/historico/tipo/<tipo>")
    print("  - GET  /api/historico/periodo")
    print("  - GET  /api/historico/hoje")
    print("  - GET  /api/historico/paginado")
    print("  - POST /api/historico/adicionar")
    print("  - GET  /api/historico/estatisticas")
    print("  - POST /api/historico/limpar")
    print("  - POST /api/historico/carregar-redis")
    print("  - GET  /api/historico/configuracoes")
