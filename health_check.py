#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Completo - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Verifica todos os módulos e dependências do sistema.
Execute para diagnosticar problemas antes de subir o servidor.

Uso:
    python health_check.py
    python health_check.py --verbose
    python health_check.py --json
"""

import sys
import time
import importlib
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


# =============================================
# CORES NO TERMINAL
# =============================================
OK     = "\033[92m✅\033[0m"
WARN   = "\033[93m⚠️ \033[0m"
ERRO   = "\033[91m❌\033[0m"
INFO   = "\033[94mℹ️ \033[0m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# =============================================
# RESULTADO DE UM CHECK
# =============================================
@dataclass
class CheckResult:
    nome: str
    ok: bool
    mensagem: str
    detalhe: Optional[str] = None
    tempo_ms: float = 0.0

    def icone(self) -> str:
        return OK if self.ok else ERRO


# =============================================
# VERIFICAÇÕES
# =============================================

def check_python_version() -> CheckResult:
    v = sys.version_info
    ok = v >= (3, 8)
    return CheckResult(
        nome="Python >= 3.8",
        ok=ok,
        mensagem=f"Python {v.major}.{v.minor}.{v.micro}",
        detalhe=None if ok else "Requer Python 3.8+"
    )


def check_dependencia(pacote: str, import_nome: Optional[str] = None,
                      versao_minima: Optional[str] = None) -> CheckResult:
    t0 = time.time()
    import_nome = import_nome or pacote
    try:
        mod = importlib.import_module(import_nome)
        versao = getattr(mod, '__version__', '?')
        tempo = (time.time() - t0) * 1000
        return CheckResult(
            nome=pacote,
            ok=True,
            mensagem=f"v{versao}",
            tempo_ms=tempo
        )
    except ImportError:
        return CheckResult(
            nome=pacote,
            ok=False,
            mensagem="NÃO INSTALADO",
            detalhe=f"pip install {pacote}"
        )


def check_modulo_marfim(nome: str, modulo: str, atributo: str) -> CheckResult:
    t0 = time.time()
    try:
        mod = importlib.import_module(modulo)
        obj = getattr(mod, atributo)
        tempo = (time.time() - t0) * 1000
        tipo = type(obj).__name__
        return CheckResult(
            nome=nome,
            ok=True,
            mensagem=f"OK ({tipo})",
            tempo_ms=tempo
        )
    except ImportError as e:
        return CheckResult(nome=nome, ok=False, mensagem=f"ImportError: {e}")
    except AttributeError as e:
        return CheckResult(nome=nome, ok=False, mensagem=f"AttrError: {e}")
    except Exception as e:
        return CheckResult(nome=nome, ok=False, mensagem=str(e)[:60])


def check_arquivo(caminho: str) -> CheckResult:
    import os
    existe = os.path.exists(caminho)
    tamanho = os.path.getsize(caminho) if existe else 0
    return CheckResult(
        nome=caminho,
        ok=existe,
        mensagem=f"{tamanho:,} bytes" if existe else "NÃO ENCONTRADO"
    )


def check_redis() -> CheckResult:
    t0 = time.time()
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_timeout=1)
        r.ping()
        tempo = (time.time() - t0) * 1000
        return CheckResult(nome="Redis", ok=True, mensagem="Conectado", tempo_ms=tempo)
    except ImportError:
        return CheckResult(nome="Redis", ok=False, mensagem="redis-py não instalado",
                           detalhe="pip install redis")
    except Exception as e:
        return CheckResult(nome="Redis", ok=False,
                           mensagem="Offline (cache em memória será usado)",
                           detalhe=str(e))


def check_credentials_json() -> CheckResult:
    import os, json
    path = "credentials.json"
    if not os.path.exists(path):
        return CheckResult(nome="credentials.json", ok=False,
                           mensagem="NÃO ENCONTRADO",
                           detalhe="Necessário para conectar ao Google Sheets")
    try:
        with open(path) as f:
            data = json.load(f)
        tipo = data.get('type', '?')
        email = data.get('client_email', '?')
        return CheckResult(nome="credentials.json", ok=True,
                           mensagem=f"OK (type={tipo})",
                           detalhe=f"client_email: {email}")
    except Exception as e:
        return CheckResult(nome="credentials.json", ok=False, mensagem=str(e))


def check_variaveis_ambiente() -> List[CheckResult]:
    import os
    resultados = []
    vars_check = [
        ("GROQ_API_KEY",      False),   # False = opcional
        ("GOOGLE_SHEET_NAME", False),
    ]
    for var, obrigatorio in vars_check:
        valor = os.getenv(var)
        ok = valor is not None
        resultados.append(CheckResult(
            nome=f"ENV: {var}",
            ok=ok or not obrigatorio,
            mensagem="Definida" if ok else ("NÃO DEFINIDA (opcional)" if not obrigatorio else "NÃO DEFINIDA"),
            detalhe=f"export {var}=..." if not ok else None
        ))
    return resultados


def check_endpoint_flask(url: str, timeout: float = 2.0) -> CheckResult:
    t0 = time.time()
    try:
        import urllib.request
        req = urllib.request.urlopen(url, timeout=timeout)
        tempo = (time.time() - t0) * 1000
        return CheckResult(nome=url, ok=True, mensagem=f"HTTP {req.status}", tempo_ms=tempo)
    except Exception as e:
        tempo = (time.time() - t0) * 1000
        return CheckResult(nome=url, ok=False,
                           mensagem="Servidor não alcançado (normal se ainda não iniciou)",
                           tempo_ms=tempo)


# =============================================
# EXECUTAR TODOS OS CHECKS
# =============================================

def executar_checks(verbose: bool = False) -> Dict[str, List[CheckResult]]:
    resultados = {}

    # 1. Python e dependências base
    resultados["🐍 Python e Dependências Base"] = [
        check_python_version(),
        check_dependencia("flask",           "flask"),
        check_dependencia("gspread",         "gspread"),
        check_dependencia("pandas",          "pandas"),
        check_dependencia("numpy",           "numpy"),
        check_dependencia("oauth2client",    "oauth2client"),
    ]

    # 2. Dependências dos módulos novos
    resultados["📦 Dependências dos Módulos (Fases 1-7)"] = [
        check_dependencia("redis",           "redis"),
        check_dependencia("openpyxl",        "openpyxl"),
        check_dependencia("fpdf2",           "fpdf"),
        check_dependencia("groq",            "groq"),
    ]

    # 3. Módulos das 7 fases
    resultados["⚙️  Módulos das 7 Fases"] = [
        check_modulo_marfim("F1 — cache_config",         "cache_config",          "cache_marfim"),
        check_modulo_marfim("F1 — indice_otimizado",     "indice_otimizado",      "indice_otimizado"),
        check_modulo_marfim("F1 — app_cache_integration","app_cache_integration", "register_cache_routes"),
        check_modulo_marfim("F2 — alertas_automaticos",  "alertas_automaticos",   "gerenciador_alertas"),
        check_modulo_marfim("F2 — alertas_integration",  "alertas_integration",   "register_alertas_routes"),
        check_modulo_marfim("F3 — preview_saldos",       "preview_saldos",        "gerenciador_preview"),
        check_modulo_marfim("F3 — preview_integration",  "preview_integration",   "register_preview_routes"),
        check_modulo_marfim("F4 — historico_otimizado",  "historico_otimizado",   "gerenciador_historico"),
        check_modulo_marfim("F4 — historico_integration","historico_integration", "register_historico_routes"),
        check_modulo_marfim("F5 — ia_avancada",          "ia_avancada",           "sistema_ia"),
        check_modulo_marfim("F5 — ia_integration",       "ia_integration",        "register_ia_routes"),
        check_modulo_marfim("F6 — relatorios",           "relatorios",            "gerenciador_relatorios"),
        check_modulo_marfim("F6 — relatorios_integration","relatorios_integration","register_relatorios_routes"),
        check_modulo_marfim("F7 — otimizacoes",          "otimizacoes",           "batch_inserter"),
        check_modulo_marfim("F7 — otimizacoes_integration","otimizacoes_integration","register_otimizacoes_routes"),
        check_modulo_marfim("F8 — integracao_final",     "integracao_final",      "registrar_tudo"),
    ]

    # 4. Arquivos essenciais
    resultados["📁 Arquivos Essenciais"] = [
        check_arquivo("credentials.json"),
        check_arquivo("app_final.py"),
        check_arquivo("config.py"),
        check_arquivo("integracao_final.py"),
        check_arquivo("health_check.py"),
        check_arquivo("requirements.txt"),
    ]

    # 5. Infraestrutura
    resultados["🔌 Infraestrutura"] = [
        check_credentials_json(),
        check_redis(),
        *check_variaveis_ambiente(),
    ]

    # 6. Servidor Flask (se já estiver rodando)
    resultados["🌐 Servidor Flask (opcional)"] = [
        check_endpoint_flask("http://localhost:5000/api/sistema/status"),
        check_endpoint_flask("http://localhost:5000/api/cache/stats"),
    ]

    return resultados


# =============================================
# RELATÓRIO
# =============================================

def imprimir_relatorio(resultados: Dict[str, List[CheckResult]], verbose: bool = False):
    total_ok = total_err = 0
    print()
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  HEALTH CHECK — MARFIM ESTOQUE CEARÁ{RESET}")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{BOLD}{'='*60}{RESET}")

    for secao, checks in resultados.items():
        print(f"\n{BOLD}  {secao}{RESET}")
        for c in checks:
            icone = OK if c.ok else (WARN if "opcional" in c.mensagem.lower() else ERRO)
            linha = f"    {icone} {c.nome:<40} {c.mensagem}"
            if c.tempo_ms > 0 and verbose:
                linha += f"  [{c.tempo_ms:.0f}ms]"
            print(linha)
            if c.detalhe and (not c.ok or verbose):
                print(f"         {INFO} {c.detalhe}")
            if c.ok:
                total_ok += 1
            elif "opcional" not in c.mensagem.lower():
                total_err += 1

    print(f"\n{BOLD}{'='*60}{RESET}")
    status = f"{OK} SISTEMA OK" if total_err == 0 else f"{ERRO} {total_err} PROBLEMA(S) ENCONTRADO(S)"
    print(f"  {status}")
    print(f"  Checks OK: {total_ok} | Com problema: {total_err}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    return total_err == 0


def gerar_json(resultados: Dict[str, List[CheckResult]]) -> dict:
    import json
    saida = {}
    total_ok = total_err = 0
    for secao, checks in resultados.items():
        saida[secao] = []
        for c in checks:
            saida[secao].append({
                'nome': c.nome,
                'ok': c.ok,
                'mensagem': c.mensagem,
                'detalhe': c.detalhe,
                'tempo_ms': round(c.tempo_ms, 2)
            })
            if c.ok:
                total_ok += 1
            else:
                total_err += 1
    saida['_resumo'] = {
        'total_ok': total_ok,
        'total_erro': total_err,
        'sistema_ok': total_err == 0,
        'timestamp': datetime.now().isoformat()
    }
    return saida


# =============================================
# MAIN
# =============================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Health Check — Marfim Estoque')
    parser.add_argument('--verbose', '-v', action='store_true', help='Detalha tempos')
    parser.add_argument('--json',    '-j', action='store_true', help='Saída em JSON')
    args = parser.parse_args()

    resultados = executar_checks(verbose=args.verbose)

    if args.json:
        import json
        print(json.dumps(gerar_json(resultados), ensure_ascii=False, indent=2))
    else:
        sistema_ok = imprimir_relatorio(resultados, verbose=args.verbose)
        sys.exit(0 if sistema_ok else 1)
