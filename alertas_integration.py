#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Alertas com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para sistema de alertas automáticos:
- Dashboard de alertas
- Listagem por tipo
- Classificação em tempo real
- Invalidação de cache
- Estatísticas

INSTRUÇÃO: Adicione ao app_final.py com:
    from alertas_integration import register_alertas_routes
    register_alertas_routes(app)
"""

from flask import jsonify, request
from alertas_config import gerenciador_alertas, TipoAlerta, ConfigAlerta
import logging

logger = logging.getLogger(__name__)


def register_alertas_routes(app):
    """
    Registra endpoints de alertas na aplicação Flask

    Uso em app_final.py:
        from alertas_integration import register_alertas_routes
        register_alertas_routes(app)
    """

    @app.route('/api/alertas/dashboard', methods=['GET'])
    def dashboard_alertas():
        """
        📊 Dashboard completo de alertas

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
        """
        try:
            dashboard = gerenciador_alertas.obter_dashboard()
            return jsonify(dashboard), 200
        except Exception as e:
            logger.error(f"Erro ao obter dashboard de alertas: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/todos', methods=['GET'])
    def listar_todos_alertas():
        """
        📋 Lista todos os alertas

        GET /api/alertas/todos
        Query params:
          - forcar_recarga: true/false (opcional)
          - limit: número máximo de resultados (opcional)

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
            },
            ...
          ],
          "total": 305
        }
        """
        try:
            forcar_recarga = request.args.get('forcar_recarga', 'false').lower() == 'true'
            limit = request.args.get('limit', type=int)

            alertas = gerenciador_alertas.analisar_todos_itens(forcar_recarga=forcar_recarga)

            # Limita resultados se solicitado
            if limit and limit > 0:
                alertas = alertas[:limit]

            # Converte para dict
            alertas_dict = [a.to_dict() for a in alertas]

            return jsonify({
                'alertas': alertas_dict,
                'total': len(alertas_dict)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar alertas: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/criticos', methods=['GET'])
    def listar_alertas_criticos():
        """
        🔴 Lista apenas alertas CRÍTICOS

        GET /api/alertas/criticos
        Query params:
          - limit: número máximo de resultados (opcional, padrão: 50)

        Response:
        {
          "alertas": [...],
          "total": 15
        }
        """
        try:
            limit = request.args.get('limit', 50, type=int)

            criticos = gerenciador_alertas.obter_alertas_criticos()

            # Limita resultados
            if limit > 0:
                criticos = criticos[:limit]

            return jsonify({
                'alertas': [a.to_dict() for a in criticos],
                'total': len(criticos)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar alertas críticos: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/atencao', methods=['GET'])
    def listar_alertas_atencao():
        """
        🟡 Lista apenas alertas de ATENÇÃO

        GET /api/alertas/atencao
        Query params:
          - limit: número máximo de resultados (opcional, padrão: 50)

        Response:
        {
          "alertas": [...],
          "total": 32
        }
        """
        try:
            limit = request.args.get('limit', 50, type=int)

            atencao = gerenciador_alertas.obter_alertas_atencao()

            # Limita resultados
            if limit > 0:
                atencao = atencao[:limit]

            return jsonify({
                'alertas': [a.to_dict() for a in atencao],
                'total': len(atencao)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar alertas de atenção: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/por-tipo/<tipo>', methods=['GET'])
    def listar_alertas_por_tipo(tipo):
        """
        📌 Lista alertas de um tipo específico

        GET /api/alertas/por-tipo/<tipo>
        Tipos válidos: critico, atencao, normal, info

        Response:
        {
          "alertas": [...],
          "total": 180,
          "tipo": "normal"
        }
        """
        try:
            # Valida tipo
            tipos_validos = ['critico', 'atencao', 'normal', 'info']
            if tipo not in tipos_validos:
                return jsonify({
                    'error': f'Tipo inválido. Use: {", ".join(tipos_validos)}'
                }), 400

            # Obtém todos e filtra
            todos_alertas = gerenciador_alertas.analisar_todos_itens()
            alertas_filtrados = [a for a in todos_alertas if a.tipo.value == tipo]

            return jsonify({
                'alertas': [a.to_dict() for a in alertas_filtrados],
                'total': len(alertas_filtrados),
                'tipo': tipo
            }), 200

        except Exception as e:
            logger.error(f"Erro ao listar alertas por tipo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/classificar', methods=['POST'])
    def classificar_movimentacao():
        """
        🎯 Classifica uma movimentação em tempo real

        POST /api/alertas/classificar
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
            "item": "AMARELO 1234",
            "mensagem": "✨ Entrada de estoque detectada!",
            "sugestao": "📝 Verifique se o registro está correto...",
            "cor_hex": "#FFC107",
            "icone": "🟡"
          }
        }
        """
        try:
            data = request.get_json()

            # Valida campos obrigatórios
            if not all(k in data for k in ['item', 'tipo_movimentacao', 'quantidade']):
                return jsonify({
                    'error': 'Campos obrigatórios: item, tipo_movimentacao, quantidade'
                }), 400

            # Classifica
            alerta = gerenciador_alertas.classificar_movimentacao(
                item=data['item'],
                tipo_movimentacao=data['tipo_movimentacao'],
                quantidade=float(data['quantidade'])
            )

            return jsonify({
                'alerta': alerta.to_dict()
            }), 200

        except Exception as e:
            logger.error(f"Erro ao classificar movimentação: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/item/<item_nome>', methods=['GET'])
    def alerta_item_especifico(item_nome):
        """
        🔍 Obtém alerta de um item específico

        GET /api/alertas/item/<item_nome>

        Response:
        {
          "alerta": {...},
          "existe": true
        }
        """
        try:
            # Obtém todos os alertas
            todos_alertas = gerenciador_alertas.analisar_todos_itens()

            # Busca por item (case-insensitive)
            item_upper = item_nome.upper().strip()
            alerta_item = None

            for alerta in todos_alertas:
                if alerta.item.upper() == item_upper:
                    alerta_item = alerta
                    break

            if alerta_item:
                return jsonify({
                    'alerta': alerta_item.to_dict(),
                    'existe': True
                }), 200
            else:
                return jsonify({
                    'alerta': None,
                    'existe': False,
                    'message': f'Item "{item_nome}" não encontrado'
                }), 404

        except Exception as e:
            logger.error(f"Erro ao buscar alerta do item: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/estatisticas', methods=['GET'])
    def estatisticas_alertas():
        """
        📈 Estatísticas detalhadas de alertas

        GET /api/alertas/estatisticas

        Response:
        {
          "total_itens": 305,
          "media_dias_parado": 12.5,
          "max_dias_parado": 45,
          "min_dias_parado": 0,
          "porcentagem_critico": 4.9,
          "porcentagem_atencao": 10.5,
          "porcentagem_normal": 59.0,
          "itens_criticos_top_10": [...],
          "grupos_mais_criticos": {...}
        }
        """
        try:
            # Obtém dashboard que já tem estatísticas
            dashboard = gerenciador_alertas.obter_dashboard()

            # Adiciona estatísticas extras
            todos_alertas = gerenciador_alertas.analisar_todos_itens()

            # Grupos mais críticos
            grupos_criticos = {}
            for alerta in todos_alertas:
                if alerta.tipo == TipoAlerta.CRITICO:
                    grupo = alerta.grupo or 'SEM_GRUPO'
                    grupos_criticos[grupo] = grupos_criticos.get(grupo, 0) + 1

            # Ordena grupos
            grupos_ordenados = sorted(
                grupos_criticos.items(),
                key=lambda x: x[1],
                reverse=True
            )

            stats = {
                **dashboard['estatisticas'],
                'itens_criticos_top_10': dashboard['top_criticos'],
                'grupos_mais_criticos': dict(grupos_ordenados[:10])
            }

            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/invalidar-cache', methods=['POST'])
    def invalidar_cache_alertas():
        """
        🗑️ Invalida cache de alertas

        POST /api/alertas/invalidar-cache

        Response:
        {
          "success": true,
          "message": "Cache de alertas invalidado"
        }
        """
        try:
            gerenciador_alertas.invalidar_cache()

            return jsonify({
                'success': True,
                'message': 'Cache de alertas invalidado com sucesso'
            }), 200

        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alertas/configuracoes', methods=['GET'])
    def obter_configuracoes_alertas():
        """
        ⚙️ Retorna configurações de alertas

        GET /api/alertas/configuracoes

        Response:
        {
          "thresholds": {
            "dias_critico": 20,
            "dias_atencao": 10,
            "dias_normal": 7
          },
          "cores": {...},
          "icones": {...}
        }
        """
        try:
            config = {
                'thresholds': {
                    'dias_critico': ConfigAlerta.DIAS_CRITICO,
                    'dias_atencao': ConfigAlerta.DIAS_ATENCAO,
                    'dias_normal': ConfigAlerta.DIAS_NORMAL
                },
                'cores': {
                    'critico': ConfigAlerta.CORES[TipoAlerta.CRITICO],
                    'atencao': ConfigAlerta.CORES[TipoAlerta.ATENCAO],
                    'normal': ConfigAlerta.CORES[TipoAlerta.NORMAL],
                    'info': ConfigAlerta.CORES[TipoAlerta.INFO]
                },
                'icones': {
                    'critico': ConfigAlerta.ICONES[TipoAlerta.CRITICO],
                    'atencao': ConfigAlerta.ICONES[TipoAlerta.ATENCAO],
                    'normal': ConfigAlerta.ICONES[TipoAlerta.NORMAL],
                    'info': ConfigAlerta.ICONES[TipoAlerta.INFO]
                },
                'cache_ttl': ConfigAlerta.CACHE_TTL
            }

            return jsonify(config), 200

        except Exception as e:
            logger.error(f"Erro ao obter configurações: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de alertas registrados")


if __name__ == '__main__':
    print("📚 Este arquivo contém endpoints de alertas para Flask")
    print("✅ Use register_alertas_routes(app) em app_final.py")
    print("")
    print("Endpoints disponíveis:")
    print("  - GET  /api/alertas/dashboard")
    print("  - GET  /api/alertas/todos")
    print("  - GET  /api/alertas/criticos")
    print("  - GET  /api/alertas/atencao")
    print("  - GET  /api/alertas/por-tipo/<tipo>")
    print("  - POST /api/alertas/classificar")
    print("  - GET  /api/alertas/item/<nome>")
    print("  - GET  /api/alertas/estatisticas")
    print("  - POST /api/alertas/invalidar-cache")
    print("  - GET  /api/alertas/configuracoes")
