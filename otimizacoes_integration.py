#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Otimizações com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para o sistema de otimizações avançadas.

INSTRUÇÃO: Adicione ao app_final.py com:
    from otimizacoes_integration import register_otimizacoes_routes
    register_otimizacoes_routes(app)
"""

from flask import jsonify, request
from otimizacoes import (
    batch_inserter, fila_retry, compressor_cache,
    monitor_perf, batch_validator, ConfigOtimizacoes
)
import logging

logger = logging.getLogger(__name__)


def register_otimizacoes_routes(app):
    """Registra endpoints de otimizações na aplicação Flask."""

    # ============================
    # BATCH INSERTER
    # ============================

    @app.route('/api/otimizacoes/batch/adicionar', methods=['POST'])
    def batch_adicionar():
        """
        📦 Adiciona itens ao buffer de batch

        POST /api/otimizacoes/batch/adicionar
        Body:
        {
          "itens": [
            {"item": "AMARELO 1234", "tipo_movimentacao": "SAIDA", "quantidade": 100},
            {"item": "AZUL 5678",    "tipo_movimentacao": "ENTRADA", "quantidade": 50}
          ]
        }

        Response:
        { "tamanho_buffer": 2, "mensagem": "2 itens adicionados ao buffer" }
        """
        try:
            data = request.get_json()
            itens = data.get('itens', [data])  # aceita lista ou item único

            if not itens:
                return jsonify({'error': 'Nenhum item fornecido'}), 400

            tamanho = batch_inserter.adicionar_muitos(itens)

            return jsonify({
                'tamanho_buffer': tamanho,
                'mensagem': f'{len(itens)} itens adicionados ao buffer'
            }), 200

        except Exception as e:
            logger.error(f"Erro ao adicionar ao batch: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/batch/flush', methods=['POST'])
    def batch_flush():
        """
        ⚡ Executa todos os itens do buffer em um único batch

        POST /api/otimizacoes/batch/flush

        Response:
        {
          "total": 50,
          "sucesso": 50,
          "erro": 0,
          "tempo_ms": 480.0,
          "throughput": 104.2,
          "economia_chamadas": 49
        }
        """
        try:
            resultado = batch_inserter.flush()
            return jsonify(resultado.to_dict()), 200
        except Exception as e:
            logger.error(f"Erro no batch flush: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/batch/status', methods=['GET'])
    def batch_status():
        """
        📊 Status atual do batch inserter

        GET /api/otimizacoes/batch/status

        Response:
        {
          "itens_pendentes": 12,
          "total_adicionado": 120,
          "total_flushed": 108,
          "total_batches": 3,
          "media_itens_por_batch": 36.0,
          "media_tempo_ms": 520.0
        }
        """
        try:
            return jsonify(batch_inserter.obter_stats()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ============================
    # FILA DE RETRY
    # ============================

    @app.route('/api/otimizacoes/fila/enqueue', methods=['POST'])
    def fila_enqueue():
        """
        🔄 Adiciona operação à fila com retry automático

        POST /api/otimizacoes/fila/enqueue
        Body:
        {
          "operacao": "inserir",
          "dados": { "item": "AMARELO 1234", "quantidade": 100 },
          "max_tentativas": 3
        }

        Response:
        { "id": "fila_000001_1739456789", "mensagem": "Operação enfileirada" }
        """
        try:
            data = request.get_json()

            if 'operacao' not in data or 'dados' not in data:
                return jsonify({'error': 'Campos obrigatórios: operacao, dados'}), 400

            id_ = fila_retry.enqueue(
                operacao=data['operacao'],
                dados=data['dados'],
                max_tentativas=data.get('max_tentativas', ConfigOtimizacoes.FILA_MAX_TENTATIVAS)
            )

            return jsonify({
                'id': id_,
                'mensagem': 'Operação enfileirada com sucesso'
            }), 201

        except Exception as e:
            logger.error(f"Erro ao enfileirar: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/fila/enqueue-lote', methods=['POST'])
    def fila_enqueue_lote():
        """
        📦 Enfileira múltiplas operações de uma vez

        POST /api/otimizacoes/fila/enqueue-lote
        Body:
        {
          "operacoes": [
            {"operacao": "inserir", "dados": {"item": "X"}},
            {"operacao": "inserir", "dados": {"item": "Y"}}
          ]
        }

        Response:
        { "ids": ["fila_000001_...", "fila_000002_..."], "total": 2 }
        """
        try:
            data = request.get_json()
            operacoes = data.get('operacoes', [])

            if not operacoes:
                return jsonify({'error': 'Campo obrigatório: operacoes'}), 400

            ids = fila_retry.enqueue_lote(operacoes)

            return jsonify({'ids': ids, 'total': len(ids)}), 201

        except Exception as e:
            logger.error(f"Erro ao enfileirar lote: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/fila/processar', methods=['POST'])
    def fila_processar():
        """
        ▶️ Processa próximo item da fila (ou todos)

        POST /api/otimizacoes/fila/processar
        Body: { "todos": false }

        Response (próximo):
        { "item": {...}, "status": "concluido" }

        Response (todos):
        { "sucesso": 45, "erro": 2 }
        """
        try:
            data = request.get_json() or {}
            todos = data.get('todos', False)

            if todos:
                resultado = fila_retry.processar_todos()
                return jsonify(resultado), 200
            else:
                item = fila_retry.processar_proximo()
                if item:
                    return jsonify({
                        'item': item.to_dict(),
                        'status': item.status.value
                    }), 200
                else:
                    return jsonify({'mensagem': 'Fila vazia'}), 200

        except Exception as e:
            logger.error(f"Erro ao processar fila: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/fila/status', methods=['GET'])
    def fila_status():
        """
        📊 Status da fila de retry

        GET /api/otimizacoes/fila/status

        Response:
        {
          "total_fila": 15,
          "pendentes": 10,
          "processando": 1,
          "retry": 3,
          "erro": 1,
          "total_processados": 120,
          "stats": { "total_enqueued": 135, "total_sucesso": 120, ... }
        }
        """
        try:
            return jsonify(fila_retry.obter_status()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/fila/erros', methods=['GET'])
    def fila_erros():
        """
        ❌ Lista itens com erro na fila

        GET /api/otimizacoes/fila/erros

        Response:
        { "erros": [...], "total": 2 }
        """
        try:
            erros = fila_retry.listar_erros()
            return jsonify({'erros': erros, 'total': len(erros)}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ============================
    # COMPRESSOR CACHE
    # ============================

    @app.route('/api/otimizacoes/compressor/stats', methods=['GET'])
    def compressor_stats():
        """
        🗜️ Estatísticas do compressor de cache

        GET /api/otimizacoes/compressor/stats

        Response:
        {
          "total_comprimido": 500,
          "total_descomprimido": 480,
          "bytes_original": 2048000,
          "bytes_comprimido": 450000,
          "taxa_compressao": "22.0%",
          "economia_bytes": 1598000,
          "economia_kb": 1561.5
        }
        """
        try:
            return jsonify(compressor_cache.obter_stats()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/compressor/testar', methods=['POST'])
    def compressor_testar():
        """
        🧪 Testa compressão de um payload

        POST /api/otimizacoes/compressor/testar
        Body: { "dados": { ... } }

        Response:
        {
          "bytes_original": 1024,
          "bytes_comprimido": 230,
          "taxa_compressao": "22.5%",
          "economia_bytes": 794
        }
        """
        try:
            data = request.get_json()
            dados = data.get('dados', data)

            import json
            raw = json.dumps(dados, ensure_ascii=False).encode('utf-8')
            comprimido = compressor_cache.comprimir(dados)

            orig = len(raw)
            comp = len(comprimido)
            economia = orig - comp

            return jsonify({
                'bytes_original': orig,
                'bytes_comprimido': comp,
                'taxa_compressao': f"{(comp / orig * 100):.1f}%" if orig > 0 else "0%",
                'economia_bytes': economia,
                'economia_pct': f"{(economia / orig * 100):.1f}%" if orig > 0 else "0%"
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ============================
    # MONITOR DE PERFORMANCE
    # ============================

    @app.route('/api/otimizacoes/monitor/resumo', methods=['GET'])
    def monitor_resumo():
        """
        📊 Resumo completo de performance

        GET /api/otimizacoes/monitor/resumo

        Response:
        {
          "uptime_segundos": 3600,
          "operacoes": {
            "inserir_item": {
              "total_chamadas": 500,
              "taxa_sucesso": "99.2%",
              "latencia_media_ms": 45.2,
              "latencia_min_ms": 12.0,
              "latencia_max_ms": 890.0
            }
          },
          "throughput_ultimo_minuto": 25,
          "total_operacoes": 1500,
          "total_erros": 12
        }
        """
        try:
            return jsonify(monitor_perf.obter_resumo()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/otimizacoes/monitor/operacao/<nome>', methods=['GET'])
    def monitor_operacao(nome):
        """
        📈 Stats de uma operação específica

        GET /api/otimizacoes/monitor/operacao/inserir_item

        Response:
        {
          "operacao": "inserir_item",
          "total_chamadas": 500,
          "sucesso": 496,
          "erro": 4,
          "taxa_sucesso": "99.2%",
          "latencia_media_ms": 45.2,
          "latencia_min_ms": 12.0,
          "latencia_max_ms": 890.0
        }
        """
        try:
            stats = monitor_perf.obter_stats_operacao(nome)
            if not stats:
                return jsonify({'mensagem': f'Sem dados para operação: {nome}'}), 404
            return jsonify(stats), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ============================
    # BATCH VALIDATOR
    # ============================

    @app.route('/api/otimizacoes/validar-lote', methods=['POST'])
    def validar_lote_paralelo():
        """
        ✅ Valida múltiplas movimentações em paralelo (RÁPIDO!)

        POST /api/otimizacoes/validar-lote
        Body:
        {
          "movimentacoes": [
            {"item": "ITEM1", "tipo_movimentacao": "SAIDA",   "quantidade": 100, "saldo_atual": 250},
            {"item": "ITEM2", "tipo_movimentacao": "ENTRADA", "quantidade": 50,  "saldo_atual": 0}
          ],
          "usar_ia": true
        }

        Response:
        {
          "resultados": [
            {"item": "ITEM1", "valido": true,  "score": 90.0, "avisos": []},
            {"item": "ITEM2", "valido": true,  "score": 100.0, "avisos": []}
          ],
          "resumo": {
            "total": 2, "validos": 2, "invalidos": 0,
            "score_medio": 95.0, "taxa_aprovacao": "100.0%"
          }
        }
        """
        try:
            data = request.get_json()
            movimentacoes = data.get('movimentacoes', [])
            usar_ia = data.get('usar_ia', True)

            if not movimentacoes:
                return jsonify({'error': 'Campo obrigatório: movimentacoes'}), 400

            with monitor_perf.medir('validar_lote_paralelo'):
                resultados = batch_validator.validar_lote(movimentacoes, usar_ia=usar_ia)

            resumo = batch_validator.resumo_validacao(resultados)

            return jsonify({
                'resultados': resultados,
                'resumo': resumo
            }), 200

        except Exception as e:
            logger.error(f"Erro ao validar lote: {e}")
            return jsonify({'error': str(e)}), 500

    # ============================
    # DASHBOARD GERAL
    # ============================

    @app.route('/api/otimizacoes/dashboard', methods=['GET'])
    def dashboard_otimizacoes():
        """
        🚀 Dashboard com todas as métricas de otimização

        GET /api/otimizacoes/dashboard

        Response: objeto com stats de todos os subsistemas
        """
        try:
            return jsonify({
                'batch': batch_inserter.obter_stats(),
                'fila': fila_retry.obter_status(),
                'compressor': compressor_cache.obter_stats(),
                'monitor': monitor_perf.obter_resumo(),
                'configuracoes': {
                    'batch_tamanho_maximo': ConfigOtimizacoes.BATCH_TAMANHO_MAXIMO,
                    'fila_max_tentativas': ConfigOtimizacoes.FILA_MAX_TENTATIVAS,
                    'compressao_nivel': ConfigOtimizacoes.COMPRESSAO_NIVEL,
                    'compressao_min_bytes': ConfigOtimizacoes.COMPRESSAO_MIN_BYTES
                }
            }), 200

        except Exception as e:
            logger.error(f"Erro no dashboard: {e}")
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de otimizações registrados")


if __name__ == '__main__':
    print("⚡ Endpoints de otimizações para Flask")
    print("✅ Use register_otimizacoes_routes(app) em app_final.py")
    print("")
    print("Endpoints (12):")
    print("  POST /api/otimizacoes/batch/adicionar")
    print("  POST /api/otimizacoes/batch/flush")
    print("  GET  /api/otimizacoes/batch/status")
    print("  POST /api/otimizacoes/fila/enqueue")
    print("  POST /api/otimizacoes/fila/enqueue-lote")
    print("  POST /api/otimizacoes/fila/processar")
    print("  GET  /api/otimizacoes/fila/status")
    print("  GET  /api/otimizacoes/fila/erros")
    print("  GET  /api/otimizacoes/compressor/stats")
    print("  POST /api/otimizacoes/compressor/testar")
    print("  GET  /api/otimizacoes/monitor/resumo")
    print("  GET  /api/otimizacoes/monitor/operacao/<nome>")
    print("  POST /api/otimizacoes/validar-lote")
    print("  GET  /api/otimizacoes/dashboard")
