#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração Final - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Registra TODOS os módulos das 7 fases em uma única chamada.

COMO USAR — adicione 3 linhas ao final do app_final.py:

    from integracao_final import registrar_tudo, imprimir_mapa_rotas
    registrar_tudo(app)
    imprimir_mapa_rotas()

Pronto! 55 endpoints novos disponíveis.
"""

import logging
import time
from typing import Optional
from flask import Flask, jsonify

logger = logging.getLogger(__name__)


# ================================================
# RESULTADO DO REGISTRO
# ================================================

class ResultadoRegistro:
    def __init__(self):
        self.fases_ok: list = []
        self.fases_erro: list = []
        self.endpoints_total: int = 0
        self.tempo_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            'fases_registradas': self.fases_ok,
            'fases_com_erro': self.fases_erro,
            'total_fases': len(self.fases_ok) + len(self.fases_erro),
            'fases_ok': len(self.fases_ok),
            'endpoints_novos': self.endpoints_total,
            'tempo_inicializacao_ms': round(self.tempo_ms, 2)
        }


# ================================================
# REGISTRADOR DE CADA FASE
# ================================================

def _registrar_fase(app, nome: str, importar_fn: str, modulo: str, n_endpoints: int,
                    resultado: ResultadoRegistro):
    """Tenta registrar uma fase, captura erros sem parar o restante."""
    try:
        mod = __import__(modulo, fromlist=[importar_fn])
        fn = getattr(mod, importar_fn)
        fn(app)
        resultado.fases_ok.append(nome)
        resultado.endpoints_total += n_endpoints
        logger.info(f"  ✅ {nome} ({n_endpoints} endpoints)")
    except ImportError as e:
        resultado.fases_erro.append(f"{nome} [ImportError: {e}]")
        logger.warning(f"  ⚠️  {nome} não carregado: {e}")
    except Exception as e:
        resultado.fases_erro.append(f"{nome} [Erro: {e}]")
        logger.error(f"  ❌ {nome} falhou: {e}")


# ================================================
# FUNÇÃO PRINCIPAL
# ================================================

def registrar_tudo(app: Flask) -> ResultadoRegistro:
    """
    Registra todos os módulos das 7 fases no app Flask.

    Args:
        app: Instância do Flask

    Returns:
        ResultadoRegistro com status de cada fase

    Exemplo de uso (ao final de app_final.py):
        from integracao_final import registrar_tudo
        registrar_tudo(app)
    """
    t0 = time.time()
    resultado = ResultadoRegistro()

    logger.info("🚀 Iniciando registro de todos os módulos Marfim...")

    fases = [
        # (nome_exibição, função, módulo, nº endpoints)
        ("FASE 1 — Cache Multinível",      "register_cache_routes",       "app_cache_integration",   8),
        ("FASE 2 — Alertas Automáticos",   "register_alertas_routes",     "alertas_integration",    10),
        ("FASE 3 — Preview de Saldos",     "register_preview_routes",     "preview_integration",     5),
        ("FASE 4 — Histórico Otimizado",   "register_historico_routes",   "historico_integration",  12),
        ("FASE 5 — IA Avançada",           "register_ia_routes",          "ia_integration",          8),
        ("FASE 6 — Relatórios",            "register_relatorios_routes",  "relatorios_integration",  8),
        ("FASE 7 — Otimizações",           "register_otimizacoes_routes", "otimizacoes_integration", 14),
    ]

    for nome, fn, modulo, n_ep in fases:
        _registrar_fase(app, nome, fn, modulo, n_ep, resultado)

    # Endpoint de status do sistema
    _registrar_endpoint_status(app, resultado)
    resultado.endpoints_total += 1

    resultado.tempo_ms = (time.time() - t0) * 1000

    # Resumo
    ok  = len(resultado.fases_ok)
    err = len(resultado.fases_erro)
    logger.info(
        f"\n{'='*55}\n"
        f"  Marfim Estoque — Integração Completa\n"
        f"  Fases carregadas : {ok}/{ok+err}\n"
        f"  Endpoints novos  : {resultado.endpoints_total}\n"
        f"  Tempo de boot    : {resultado.tempo_ms:.0f}ms\n"
        f"{'='*55}"
    )

    if resultado.fases_erro:
        logger.warning(f"  Fases com problema: {resultado.fases_erro}")

    return resultado


# ================================================
# ENDPOINT /api/sistema/status
# ================================================

def _registrar_endpoint_status(app: Flask, resultado: ResultadoRegistro):
    """Registra o endpoint de saúde do sistema."""

    @app.route('/api/sistema/status', methods=['GET'])
    def sistema_status():
        """
        🏥 Status completo do sistema

        GET /api/sistema/status

        Response:
        {
          "status": "ok",
          "fases_registradas": ["FASE 1...", ...],
          "fases_com_erro": [],
          "endpoints_novos": 56,
          "modulos": {
            "cache": true,
            "alertas": true,
            "preview": true,
            "historico": true,
            "ia": true,
            "relatorios": true,
            "otimizacoes": true
          },
          "timestamp": "2026-02-13T10:30:00"
        }
        """
        from datetime import datetime

        # Verifica quais módulos estão operacionais
        modulos = {}
        checks = [
            ("cache",       "indice_otimizado",     "indice_otimizado"),
            ("alertas",     "alertas_automaticos",  "gerenciador_alertas"),
            ("preview",     "preview_saldos",       "gerenciador_preview"),
            ("historico",   "historico_otimizado",  "gerenciador_historico"),
            ("ia",          "ia_avancada",          "sistema_ia"),
            ("relatorios",  "relatorios",           "gerenciador_relatorios"),
            ("otimizacoes", "otimizacoes",          "batch_inserter"),
        ]

        for nome, modulo, atributo in checks:
            try:
                mod = __import__(modulo, fromlist=[atributo])
                getattr(mod, atributo)
                modulos[nome] = True
            except Exception:
                modulos[nome] = False

        total_ok = sum(modulos.values())
        status_geral = "ok" if total_ok == len(modulos) else \
                       "degradado" if total_ok > 0 else "erro"

        return jsonify({
            "status": status_geral,
            "fases_registradas": resultado.fases_ok,
            "fases_com_erro": resultado.fases_erro,
            "endpoints_novos": resultado.endpoints_total,
            "tempo_inicializacao_ms": round(resultado.tempo_ms, 2),
            "modulos": modulos,
            "modulos_ok": total_ok,
            "modulos_total": len(modulos),
            "timestamp": datetime.now().isoformat()
        }), 200


# ================================================
# UTILITÁRIOS
# ================================================

def imprimir_mapa_rotas():
    """Imprime mapa completo de todos os endpoints novos."""
    mapa = {
        "FASE 1 — Cache Multinível (8)": [
            "GET  /api/cache/stats",
            "POST /api/cache/invalidate",
            "GET  /api/cache/health",
            "POST /api/indice/reconstruir",
            "GET  /api/indice/item/<nome>",
            "GET  /api/indice/saldo/<nome>",
            "GET  /api/indice/todos-itens",
            "GET  /api/indice/todos-grupos",
        ],
        "FASE 2 — Alertas Automáticos (10)": [
            "GET  /api/alertas/dashboard",
            "GET  /api/alertas/todos",
            "GET  /api/alertas/criticos",
            "GET  /api/alertas/atencao",
            "GET  /api/alertas/por-tipo/<tipo>",
            "POST /api/alertas/classificar",
            "GET  /api/alertas/item/<nome>",
            "GET  /api/alertas/estatisticas",
            "POST /api/alertas/invalidar-cache",
            "GET  /api/alertas/configuracoes",
        ],
        "FASE 3 — Preview de Saldos (5)": [
            "POST /api/preview/calcular",
            "POST /api/preview/validar",
            "POST /api/preview/lote",
            "GET  /api/preview/saldo/<item>",
            "GET  /api/preview/configuracoes",
        ],
        "FASE 4 — Histórico Otimizado (12)": [
            "GET  /api/historico/ultimos",
            "GET  /api/historico/item/<nome>",
            "GET  /api/historico/grupo/<nome>",
            "GET  /api/historico/tipo/<tipo>",
            "GET  /api/historico/periodo",
            "GET  /api/historico/hoje",
            "GET  /api/historico/paginado",
            "POST /api/historico/adicionar",
            "GET  /api/historico/estatisticas",
            "POST /api/historico/limpar",
            "POST /api/historico/carregar-redis",
            "GET  /api/historico/configuracoes",
        ],
        "FASE 5 — IA Avançada (8)": [
            "POST /api/ia/validar",
            "POST /api/ia/prever-saldo",
            "POST /api/ia/detectar-anomalias",
            "GET  /api/ia/recomendacoes",
            "GET  /api/ia/analisar-item/<nome>",
            "POST /api/ia/validar-lote",
            "GET  /api/ia/dashboard",
            "GET  /api/ia/configuracoes",
        ],
        "FASE 6 — Relatórios (8)": [
            "GET  /api/relatorios/completo",
            "GET  /api/relatorios/curva-abc",
            "GET  /api/relatorios/grupos",
            "GET  /api/relatorios/itens-parados",
            "GET  /api/relatorios/exportar/excel",
            "GET  /api/relatorios/exportar/pdf",
            "GET  /api/relatorios/graficos",
            "GET  /api/relatorios/configuracoes",
        ],
        "FASE 7 — Otimizações (14)": [
            "POST /api/otimizacoes/batch/adicionar",
            "POST /api/otimizacoes/batch/flush",
            "GET  /api/otimizacoes/batch/status",
            "POST /api/otimizacoes/fila/enqueue",
            "POST /api/otimizacoes/fila/enqueue-lote",
            "POST /api/otimizacoes/fila/processar",
            "GET  /api/otimizacoes/fila/status",
            "GET  /api/otimizacoes/fila/erros",
            "GET  /api/otimizacoes/compressor/stats",
            "POST /api/otimizacoes/compressor/testar",
            "GET  /api/otimizacoes/monitor/resumo",
            "GET  /api/otimizacoes/monitor/operacao/<nome>",
            "POST /api/otimizacoes/validar-lote",
            "GET  /api/otimizacoes/dashboard",
        ],
        "FASE 8 — Sistema (1)": [
            "GET  /api/sistema/status",
        ],
    }

    print("\n" + "="*60)
    print("  MAPA DE ROTAS — MARFIM ESTOQUE CEARÁ")
    print("="*60)

    total = 0
    for fase, rotas in mapa.items():
        print(f"\n  {fase}")
        for rota in rotas:
            print(f"    {rota}")
        total += len(rotas)

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total} endpoints")
    print("="*60 + "\n")
