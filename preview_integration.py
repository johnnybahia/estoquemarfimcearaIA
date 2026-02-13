#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Preview com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para preview de saldos antes de inserir.

INSTRUÇÃO: Adicione ao app_final.py com:
    from preview_integration import register_preview_routes
    register_preview_routes(app)
"""

from flask import jsonify, request
from preview_saldos import gerenciador_preview, validar_antes_inserir
import logging

logger = logging.getLogger(__name__)


def register_preview_routes(app):
    """
    Registra endpoints de preview na aplicação Flask

    Uso em app_final.py:
        from preview_integration import register_preview_routes
        register_preview_routes(app)
    """

    @app.route('/api/preview/calcular', methods=['POST'])
    def calcular_preview():
        """
        👁️ Calcula preview de saldo antes de inserir

        POST /api/preview/calcular
        Body:
        {
          "item": "AMARELO 1234",
          "tipo_movimentacao": "SAIDA",
          "quantidade": 100,
          "grupo": "FIOS"  // opcional
        }

        Response:
        {
          "preview": {
            "item": "AMARELO 1234",
            "grupo": "FIOS",
            "tipo_movimentacao": "saida",
            "quantidade": 100,
            "saldo_atual": 250.0,
            "novo_saldo": 150.0,
            "diferenca": -100.0,
            "status": "ok",
            "mensagem": "✅ Saída de estoque: 250.0 → 150.0 (-100.0)",
            "alerta": null,
            "recomendacao": "✅ Tudo certo! Pode confirmar.",
            "pode_confirmar": true,
            "timestamp": "2026-02-13T10:30:00"
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

            # Calcula preview
            preview = gerenciador_preview.calcular_preview(
                item=data['item'],
                tipo_movimentacao=data['tipo_movimentacao'],
                quantidade=float(data['quantidade']),
                grupo=data.get('grupo')
            )

            return jsonify({
                'preview': preview.to_dict()
            }), 200

        except ValueError as e:
            return jsonify({'error': f'Valor inválido: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Erro ao calcular preview: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/preview/validar', methods=['POST'])
    def validar_movimentacao():
        """
        ✅ Valida se movimentação pode ser executada

        POST /api/preview/validar
        Body:
        {
          "item": "AMARELO 1234",
          "tipo_movimentacao": "SAIDA",
          "quantidade": 100
        }

        Response (válido):
        {
          "valido": true,
          "motivo": null,
          "preview": {...}
        }

        Response (inválido):
        {
          "valido": false,
          "motivo": "⚠️ SALDO FICARÁ NEGATIVO (-50)! Verifique...",
          "preview": {...}
        }
        """
        try:
            data = request.get_json()

            # Valida campos
            if not all(k in data for k in ['item', 'tipo_movimentacao', 'quantidade']):
                return jsonify({
                    'error': 'Campos obrigatórios: item, tipo_movimentacao, quantidade'
                }), 400

            # Valida
            resultado = gerenciador_preview.validar_movimentacao(
                item=data['item'],
                tipo_movimentacao=data['tipo_movimentacao'],
                quantidade=float(data['quantidade'])
            )

            status_code = 200 if resultado['valido'] else 400

            return jsonify(resultado), status_code

        except Exception as e:
            logger.error(f"Erro ao validar movimentação: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/preview/lote', methods=['POST'])
    def calcular_preview_lote():
        """
        📦 Calcula preview para múltiplas movimentações

        POST /api/preview/lote
        Body:
        {
          "movimentacoes": [
            {"item": "AMARELO 1234", "tipo_movimentacao": "SAIDA", "quantidade": 50},
            {"item": "AZUL 5678", "tipo_movimentacao": "ENTRADA", "quantidade": 100}
          ]
        }

        Response:
        {
          "previews": [
            {...},
            {...}
          ],
          "total": 2,
          "validos": 2,
          "invalidos": 0
        }
        """
        try:
            data = request.get_json()

            if 'movimentacoes' not in data:
                return jsonify({'error': 'Campo obrigatório: movimentacoes'}), 400

            # Calcula previews
            previews = gerenciador_preview.calcular_preview_lote(data['movimentacoes'])

            # Conta válidos/inválidos
            validos = sum(1 for p in previews if p.pode_confirmar)
            invalidos = len(previews) - validos

            return jsonify({
                'previews': [p.to_dict() for p in previews],
                'total': len(previews),
                'validos': validos,
                'invalidos': invalidos
            }), 200

        except Exception as e:
            logger.error(f"Erro ao calcular preview em lote: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/preview/saldo/<item_nome>', methods=['GET'])
    def obter_saldo_preview(item_nome):
        """
        💰 Obtém saldo atual de um item (para preview rápido)

        GET /api/preview/saldo/<item_nome>

        Response:
        {
          "item": "AMARELO 1234",
          "saldo_atual": 250.0,
          "grupo": "FIOS",
          "existe": true
        }
        """
        try:
            from indice_otimizado import indice_otimizado

            dados = indice_otimizado.buscar_item(item_nome)

            if dados:
                return jsonify({
                    'item': item_nome,
                    'saldo_atual': float(dados.get('saldo', 0)),
                    'grupo': dados.get('grupo', ''),
                    'existe': True
                }), 200
            else:
                return jsonify({
                    'item': item_nome,
                    'saldo_atual': 0.0,
                    'grupo': '',
                    'existe': False
                }), 200

        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/preview/configuracoes', methods=['GET'])
    def obter_configuracoes_preview():
        """
        ⚙️ Retorna configurações de preview

        GET /api/preview/configuracoes

        Response:
        {
          "saldo_minimo_atencao": 10,
          "permitir_saldo_negativo": false,
          "cache_ttl": 60
        }
        """
        try:
            from preview_saldos import ConfigPreview

            config = {
                'saldo_minimo_atencao': ConfigPreview.SALDO_MINIMO_ATENCAO,
                'permitir_saldo_negativo': ConfigPreview.PERMITIR_SALDO_NEGATIVO,
                'cache_ttl': ConfigPreview.CACHE_TTL
            }

            return jsonify(config), 200

        except Exception as e:
            logger.error(f"Erro ao obter configurações: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de preview registrados")


if __name__ == '__main__':
    print("📚 Este arquivo contém endpoints de preview para Flask")
    print("✅ Use register_preview_routes(app) em app_final.py")
    print("")
    print("Endpoints disponíveis:")
    print("  - POST /api/preview/calcular")
    print("  - POST /api/preview/validar")
    print("  - POST /api/preview/lote")
    print("  - GET  /api/preview/saldo/<item>")
    print("  - GET  /api/preview/configuracoes")
