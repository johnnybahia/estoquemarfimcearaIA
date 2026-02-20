"""
Integração Flask — Controle de Auditoria Obrigatória
=====================================================
Registra rotas e fornece o decorator `requer_auditoria_valida`
para proteger endpoints de movimentação.

Endpoints registrados:
  GET  /api/auditoria/status           → status atual (badge/painel)
  GET  /api/auditoria/historico        → últimas auditorias
  POST /api/auditoria/verificar-obs    → verifica se OBS tem ATUALIZAÇÃO
  POST /api/auditoria/refresh          → força re-leitura do Sheets
  GET  /api/auditoria/configuracoes    → parâmetros do sistema

Decorator para proteger endpoints:
  from auditoria_integration import requer_auditoria_valida

  @app.route('/api/movimentacao', methods=['POST'])
  @requer_auditoria_valida
  def api_movimentacao():
      ...
"""

import logging
from functools import wraps
from flask import jsonify, request

from controle_auditoria import get_gerenciador_auditoria, DIAS_LIMITE, DIAS_AVISO_AMARELO, DIAS_AVISO_LARANJA

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Decorator de proteção
# ──────────────────────────────────────────────────────────────

def requer_auditoria_valida(fn):
    """
    Decorator que bloqueia a execução do endpoint caso o estoque
    esteja com auditoria vencida (> DIAS_LIMITE dias).

    Retorna HTTP 403 com payload de erro detalhado quando bloqueado.
    Adiciona o header  X-Auditoria-Nivel  em todas as respostas.

    Uso:
        @app.route('/api/movimentacao', methods=['POST'])
        @requer_auditoria_valida
        def api_movimentacao():
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            gerenciador = get_gerenciador_auditoria()
            status = gerenciador.verificar_status()

            if not status.pode_movimentar:
                response = jsonify({
                    "success": False,
                    "bloqueado_auditoria": True,
                    "nivel": status.nivel.value,
                    "dias_desde_ultima": status.dias_desde_ultima,
                    "ultima_auditoria": (
                        status.ultima_auditoria.strftime('%d/%m/%Y %H:%M')
                        if status.ultima_auditoria else None
                    ),
                    "mensagem": status.mensagem,
                    "mensagem_detalhada": status.mensagem_detalhada,
                    "cor_hex": status.cor_hex,
                    "emoji": status.emoji,
                    "instrucoes": (
                        "Para desbloquear: realize a conferência física do estoque "
                        f"e registre qualquer movimentação com a palavra "
                        f"ATUALIZAÇÃO no campo OBS."
                    ),
                    "dias_limite": DIAS_LIMITE,
                })
                response.headers['X-Auditoria-Nivel'] = status.nivel.value
                return response, 403

            # Auditoria OK — executa o endpoint normalmente
            result = fn(*args, **kwargs)

            # Após execução bem-sucedida, notifica o gerenciador
            # para que ele invalide o cache se a OBS tiver ATUALIZAÇÃO
            try:
                dados = request.get_json(silent=True) or {}
                itens = dados.get('itens', [])
                for item in itens:
                    obs = item.get('obs', '')
                    if obs:
                        gerenciador.notificar_novo_lancamento(obs)
                # Também verifica OBS direto (em endpoints simples)
                obs_direto = dados.get('obs', '')
                if obs_direto:
                    gerenciador.notificar_novo_lancamento(obs_direto)
            except Exception:
                pass   # não interrompe o fluxo principal

            return result

        except Exception as e:
            logger.error(f"[Auditoria] Erro no decorator: {e}")
            # Se o sistema de auditoria falhar, deixa passar (fail-open)
            # para não bloquear o estoque por problema técnico
            logger.warning("[Auditoria] Falha no controle — operação permitida por segurança.")
            return fn(*args, **kwargs)

    return wrapper


# ──────────────────────────────────────────────────────────────
# Registro de rotas
# ──────────────────────────────────────────────────────────────

def register_auditoria_routes(app):
    """Registra todas as rotas de auditoria na aplicação Flask."""

    gerenciador = get_gerenciador_auditoria()

    # ── GET /api/auditoria/status ──────────────────────────────
    @app.route('/api/auditoria/status', methods=['GET'])
    def api_auditoria_status():
        """
        Retorna o status atual da auditoria.
        Use force_refresh=true para ignorar o cache.

        Query params:
          force_refresh=true   → força re-leitura do Google Sheets
        """
        try:
            force = request.args.get('force_refresh', 'false').lower() == 'true'
            status = gerenciador.verificar_status(force_refresh=force)
            response = jsonify({"success": True, "auditoria": status.to_dict()})
            response.headers['X-Auditoria-Nivel'] = status.nivel.value
            return response
        except Exception as e:
            logger.error(f"[Auditoria] Erro em /status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ── GET /api/auditoria/historico ───────────────────────────
    @app.route('/api/auditoria/historico', methods=['GET'])
    def api_auditoria_historico():
        """
        Retorna as últimas auditorias registradas.

        Query params:
          limite=10   → quantidade máxima de registros (default 10, max 50)
        """
        try:
            limite = min(int(request.args.get('limite', 10)), 50)
            historico = gerenciador.obter_historico(limite=limite)
            return jsonify({
                "success": True,
                "total": len(historico),
                "historico": historico,
            })
        except Exception as e:
            logger.error(f"[Auditoria] Erro em /historico: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ── POST /api/auditoria/verificar-obs ─────────────────────
    @app.route('/api/auditoria/verificar-obs', methods=['POST'])
    def api_auditoria_verificar_obs():
        """
        Verifica em tempo real se o campo OBS digitado contém ATUALIZAÇÃO.
        Use no frontend para dar feedback imediato ao usuário.

        Body: { "obs": "texto digitado" }
        """
        try:
            dados = request.json or {}
            obs = dados.get('obs', '')
            tem_auditoria = gerenciador.checar_obs_tem_auditoria(obs)
            return jsonify({
                "success": True,
                "obs": obs,
                "contem_auditoria": tem_auditoria,
                "palavra_chave": "ATUALIZAÇÃO",
                "mensagem": (
                    "✅ Campo OBS contém ATUALIZAÇÃO — esta movimentação será registrada como conferência."
                    if tem_auditoria else
                    "ℹ️ OBS não contém ATUALIZAÇÃO — movimentação normal."
                ),
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ── POST /api/auditoria/refresh ────────────────────────────
    @app.route('/api/auditoria/refresh', methods=['POST'])
    def api_auditoria_refresh():
        """
        Invalida o cache e retorna o novo status após re-leitura do Sheets.
        Use após registrar uma conferência para ver o novo prazo imediatamente.
        """
        try:
            gerenciador.invalidar_cache()
            status = gerenciador.verificar_status(force_refresh=True)
            return jsonify({
                "success": True,
                "mensagem": "Cache invalidado e status atualizado.",
                "auditoria": status.to_dict(),
            })
        except Exception as e:
            logger.error(f"[Auditoria] Erro em /refresh: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ── GET /api/auditoria/configuracoes ───────────────────────
    @app.route('/api/auditoria/configuracoes', methods=['GET'])
    def api_auditoria_configuracoes():
        """Retorna os parâmetros configurados do sistema de auditoria."""
        return jsonify({
            "success": True,
            "configuracoes": {
                "dias_limite":            DIAS_LIMITE,
                "dias_aviso_amarelo":     DIAS_AVISO_AMARELO,
                "dias_aviso_laranja":     DIAS_AVISO_LARANJA,
                "palavra_chave":          "ATUALIZAÇÃO",
                "cache_ttl_segundos":     300,
                "aba_planilha":           "ESTOQUE",
                "coluna_verificada":      "OBS",
                "fail_open":              True,
                "descricao": (
                    "O sistema verifica se a última movimentação com 'ATUALIZAÇÃO' no campo OBS "
                    f"foi feita há menos de {DIAS_LIMITE} dias. Caso contrário, bloqueia "
                    "todas as entradas e saídas até que o estoque seja conferido."
                ),
            },
        })

    logger.info("[Auditoria] Rotas registradas: status, historico, verificar-obs, refresh, configuracoes")
    return app
