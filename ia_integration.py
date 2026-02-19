#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de IA com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para sistema de IA avançada.

INSTRUÇÃO: Adicione ao app_final.py com:
    from ia_integration import register_ia_routes
    register_ia_routes(app)
"""

from flask import jsonify, request
from ia_avancada import sistema_ia, ConfigIA
import logging

logger = logging.getLogger(__name__)


def register_ia_routes(app):
    """
    Registra endpoints de IA na aplicação Flask

    Uso em app_final.py:
        from ia_integration import register_ia_routes
        register_ia_routes(app)
    """

    @app.route('/api/ia/validar', methods=['POST'])
    def validar_com_ia():
        """
        🤖 Valida movimentação com IA

        POST /api/ia/validar
        Body:
        {
          "item": "AMARELO 1234",
          "tipo_movimentacao": "SAIDA",
          "quantidade": 100,
          "saldo_atual": 250,
          "grupo": "FIOS",
          "historico": [...]  // opcional
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
            "score": 75.0
          }
        }
        """
        try:
            data = request.get_json()

            # Valida campos
            required = ['item', 'tipo_movimentacao', 'quantidade', 'saldo_atual']
            if not all(k in data for k in required):
                return jsonify({
                    'error': f'Campos obrigatórios: {", ".join(required)}'
                }), 400

            # Busca histórico se não fornecido
            historico = data.get('historico')
            if not historico:
                try:
                    from historico_otimizado import gerenciador_historico
                    registros = gerenciador_historico.buscar_por_item(data['item'], limite=20)
                    historico = [r.to_dict() for r in registros]
                except:
                    historico = []

            # Valida com IA
            validacao = sistema_ia.validar_movimentacao(
                item=data['item'],
                tipo_movimentacao=data['tipo_movimentacao'],
                quantidade=float(data['quantidade']),
                saldo_atual=float(data['saldo_atual']),
                grupo=data.get('grupo'),
                historico=historico
            )

            return jsonify({
                'validacao': validacao.to_dict()
            }), 200

        except ValueError as e:
            return jsonify({'error': f'Valor inválido: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Erro ao validar com IA: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/prever-saldo', methods=['POST'])
    def prever_saldo_futuro():
        """
        🔮 Prevê saldo futuro de um item

        POST /api/ia/prever-saldo
        Body:
        {
          "item": "AMARELO 1234",
          "dias": 7,
          "saldo_atual": 250,  // opcional
          "historico": [...]   // opcional
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
        """
        try:
            data = request.get_json()

            if 'item' not in data:
                return jsonify({'error': 'Campo obrigatório: item'}), 400

            dias = data.get('dias', 7)
            saldo_atual = data.get('saldo_atual')
            historico = data.get('historico')

            # Busca histórico se não fornecido
            if not historico:
                try:
                    from historico_otimizado import gerenciador_historico
                    registros = gerenciador_historico.buscar_por_item(data['item'], limite=30)
                    historico = [r.to_dict() for r in registros]
                except:
                    historico = []

            # Prevê saldo
            predicao = sistema_ia.prever_saldo_futuro(
                item=data['item'],
                dias=dias,
                saldo_atual=saldo_atual,
                historico=historico
            )

            return jsonify({
                'predicao': predicao.to_dict()
            }), 200

        except Exception as e:
            logger.error(f"Erro ao prever saldo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/detectar-anomalias', methods=['POST'])
    def detectar_anomalias():
        """
        🔍 Detecta anomalias em movimentação

        POST /api/ia/detectar-anomalias
        Body:
        {
          "item": "AMARELO 1234",
          "quantidade": 1000,
          "tipo_movimentacao": "SAIDA",
          "historico": [...]  // opcional
        }

        Response:
        {
          "anomalias": [
            {
              "tipo": "quantidade_anormal",
              "gravidade": "alta",
              "descricao": "Quantidade 1000 está 5.2 desvios padrão acima",
              "valor_atual": 1000,
              "valor_esperado": 100,
              "confianca": 95.0,
              "recomendacao": "Verifique se está correto"
            }
          ],
          "total": 1
        }
        """
        try:
            data = request.get_json()

            required = ['item', 'quantidade', 'tipo_movimentacao']
            if not all(k in data for k in required):
                return jsonify({
                    'error': f'Campos obrigatórios: {", ".join(required)}'
                }), 400

            # Busca histórico
            historico = data.get('historico')
            if not historico:
                try:
                    from historico_otimizado import gerenciador_historico
                    registros = gerenciador_historico.buscar_por_item(data['item'], limite=20)
                    historico = [r.to_dict() for r in registros]
                except:
                    historico = []

            # Detecta anomalias
            anomalias = sistema_ia.detectar_anomalias(
                item=data['item'],
                quantidade=float(data['quantidade']),
                tipo_movimentacao=data['tipo_movimentacao'],
                historico=historico
            )

            return jsonify({
                'anomalias': [a.to_dict() for a in anomalias],
                'total': len(anomalias)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao detectar anomalias: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/recomendacoes', methods=['GET'])
    def obter_recomendacoes():
        """
        💡 Obtém recomendações automáticas da IA

        GET /api/ia/recomendacoes?limite=10

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
        """
        try:
            limite = request.args.get('limite', 10, type=int)

            recomendacoes = sistema_ia.gerar_recomendacoes(limite)

            return jsonify({
                'recomendacoes': [r.to_dict() for r in recomendacoes],
                'total': len(recomendacoes)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter recomendações: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/analisar-item/<item_nome>', methods=['GET'])
    def analisar_item_completo(item_nome):
        """
        📊 Análise completa de um item com IA

        GET /api/ia/analisar-item/<item_nome>

        Response:
        {
          "item": "AMARELO 1234",
          "saldo_atual": 250.0,
          "predicao": {
            "saldo_previsto": 180.0,
            "dias_para_zerar": 25,
            "tendencia": "decrescente"
          },
          "alerta": {...},
          "total_movimentacoes": 45,
          "analise_ia": {
            "status": "✅ OK",
            "recomendacao_principal": "Saldo previsto OK"
          }
        }
        """
        try:
            analise = sistema_ia.analisar_item_completo(item_nome)

            return jsonify(analise), 200

        except Exception as e:
            logger.error(f"Erro ao analisar item: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/validar-lote', methods=['POST'])
    def validar_lote():
        """
        📦 Valida múltiplas movimentações com IA

        POST /api/ia/validar-lote
        Body:
        {
          "movimentacoes": [
            {"item": "ITEM1", "tipo_movimentacao": "SAIDA", "quantidade": 100, "saldo_atual": 250},
            {"item": "ITEM2", "tipo_movimentacao": "ENTRADA", "quantidade": 50, "saldo_atual": 100}
          ]
        }

        Response:
        {
          "validacoes": [...],
          "total": 2,
          "validos": 1,
          "invalidos": 1
        }
        """
        try:
            data = request.get_json()

            if 'movimentacoes' not in data:
                return jsonify({'error': 'Campo obrigatório: movimentacoes'}), 400

            validacoes = []

            for mov in data['movimentacoes']:
                try:
                    validacao = sistema_ia.validar_movimentacao(
                        item=mov['item'],
                        tipo_movimentacao=mov['tipo_movimentacao'],
                        quantidade=float(mov['quantidade']),
                        saldo_atual=float(mov['saldo_atual']),
                        grupo=mov.get('grupo')
                    )
                    validacoes.append({
                        'item': mov['item'],
                        'validacao': validacao.to_dict()
                    })
                except Exception as e:
                    logger.error(f"Erro ao validar {mov.get('item')}: {e}")
                    continue

            validos = sum(1 for v in validacoes if v['validacao']['valido'])
            invalidos = len(validacoes) - validos

            return jsonify({
                'validacoes': validacoes,
                'total': len(validacoes),
                'validos': validos,
                'invalidos': invalidos
            }), 200

        except Exception as e:
            logger.error(f"Erro ao validar lote: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/dashboard', methods=['GET'])
    def dashboard_ia():
        """
        📊 Dashboard com insights da IA

        GET /api/ia/dashboard

        Response:
        {
          "recomendacoes_prioritarias": [...],
          "itens_criticos": [...],
          "predicoes_criticas": [...],
          "estatisticas": {
            "total_analisado": 100,
            "itens_atencao": 5,
            "score_medio": 85.0
          }
        }
        """
        try:
            # Recomendações top 5
            recomendacoes = sistema_ia.gerar_recomendacoes(limite=5)

            # Itens críticos (alertas)
            from alertas_automaticos import gerenciador_alertas
            alertas_criticos = gerenciador_alertas.obter_alertas_criticos()[:5]

            # Predições críticas (seria feito para vários itens, aqui simplificado)
            predicoes_criticas = []

            return jsonify({
                'recomendacoes_prioritarias': [r.to_dict() for r in recomendacoes],
                'itens_criticos': alertas_criticos,
                'predicoes_criticas': predicoes_criticas,
                'estatisticas': {
                    'total_recomendacoes': len(recomendacoes),
                    'itens_atencao': len(alertas_criticos),
                    'score_medio': 85.0  # Mock
                }
            }), 200

        except Exception as e:
            logger.error(f"Erro no dashboard IA: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ia/configuracoes', methods=['GET'])
    def obter_configuracoes_ia():
        """
        ⚙️ Retorna configurações da IA

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
        """
        try:
            config = {
                'score_minimo_valido': ConfigIA.SCORE_MINIMO_VALIDO,
                'confianca_minima': ConfigIA.CONFIANCA_MINIMA,
                'desvio_padrao_max': ConfigIA.DESVIO_PADRAO_MAX,
                'quantidade_min_historico': ConfigIA.QUANTIDADE_MIN_HISTORICO,
                'dias_historico': ConfigIA.DIAS_HISTORICO,
                'dias_predicao': ConfigIA.DIAS_PREDICAO,
                'dias_critico_estoque': ConfigIA.DIAS_CRITICO_ESTOQUE,
                'dias_atencao_estoque': ConfigIA.DIAS_ATENCAO_ESTOQUE
            }

            return jsonify(config), 200

        except Exception as e:
            logger.error(f"Erro ao obter configurações: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de IA registrados")


if __name__ == '__main__':
    print("🤖 Este arquivo contém endpoints de IA para Flask")
    print("✅ Use register_ia_routes(app) em app_final.py")
    print("")
    print("Endpoints disponíveis:")
    print("  - POST /api/ia/validar")
    print("  - POST /api/ia/prever-saldo")
    print("  - POST /api/ia/detectar-anomalias")
    print("  - GET  /api/ia/recomendacoes")
    print("  - GET  /api/ia/analisar-item/<nome>")
    print("  - POST /api/ia/validar-lote")
    print("  - GET  /api/ia/dashboard")
    print("  - GET  /api/ia/configuracoes")
