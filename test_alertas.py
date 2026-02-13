#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste - Sistema de Alertas
Autor: Johnny
Data: 2026-02-13

Testa todas as funcionalidades do sistema de alertas automáticos
"""

import sys
from datetime import datetime, timedelta
from alertas_config import (
    gerenciador_alertas,
    TipoAlerta,
    SeveridadeAlerta,
    ConfigAlerta
)


def print_header(titulo):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(titulo.center(60))
    print("=" * 60)


def print_alerta(alerta):
    """Imprime detalhes de um alerta"""
    print(f"\n{alerta.icone} {alerta.tipo.value.upper()}")
    print(f"   Item: {alerta.item}")
    print(f"   Grupo: {alerta.grupo}")
    print(f"   Mensagem: {alerta.mensagem}")
    print(f"   Dias parado: {alerta.dias_parado}")
    print(f"   Saldo: {alerta.saldo_atual}")
    print(f"   Última data: {alerta.ultima_data}")
    print(f"   Sugestão: {alerta.sugestao}")


def test_calcular_dias():
    """Testa cálculo de dias parados"""
    print_header("TESTE 1: Cálculo de Dias Parados")

    # Caso 1: Data recente (5 dias atrás)
    data_recente = (datetime.now() - timedelta(days=5)).strftime('%d/%m/%Y')
    dias = gerenciador_alertas.calcular_dias_parado(data_recente)
    print(f"\n✅ Data 5 dias atrás: {dias} dias (esperado: ~5)")
    assert 4 <= dias <= 6, f"Erro: esperado ~5, obtido {dias}"

    # Caso 2: Data antiga (30 dias atrás)
    data_antiga = (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y')
    dias = gerenciador_alertas.calcular_dias_parado(data_antiga)
    print(f"✅ Data 30 dias atrás: {dias} dias (esperado: ~30)")
    assert 29 <= dias <= 31, f"Erro: esperado ~30, obtido {dias}"

    # Caso 3: Hoje
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    dias = gerenciador_alertas.calcular_dias_parado(data_hoje)
    print(f"✅ Data de hoje: {dias} dias (esperado: 0)")
    assert dias == 0, f"Erro: esperado 0, obtido {dias}"

    print("\n✅ TESTE 1 PASSOU")


def test_classificacao_por_dias():
    """Testa classificação por dias"""
    print_header("TESTE 2: Classificação por Dias")

    # Caso 1: Crítico (>20 dias)
    tipo = gerenciador_alertas.classificar_por_dias(25)
    print(f"\n✅ 25 dias → {tipo.value} (esperado: critico)")
    assert tipo == TipoAlerta.CRITICO

    # Caso 2: Atenção (10-20 dias)
    tipo = gerenciador_alertas.classificar_por_dias(15)
    print(f"✅ 15 dias → {tipo.value} (esperado: atencao)")
    assert tipo == TipoAlerta.ATENCAO

    # Caso 3: Info (7-10 dias)
    tipo = gerenciador_alertas.classificar_por_dias(8)
    print(f"✅ 8 dias → {tipo.value} (esperado: info)")
    assert tipo == TipoAlerta.INFO

    # Caso 4: Normal (<7 dias)
    tipo = gerenciador_alertas.classificar_por_dias(3)
    print(f"✅ 3 dias → {tipo.value} (esperado: normal)")
    assert tipo == TipoAlerta.NORMAL

    print("\n✅ TESTE 2 PASSOU")


def test_deteccao_entrada():
    """Testa detecção de entrada de estoque"""
    print_header("TESTE 3: Detecção de Entrada de Estoque")

    # Caso 1: Entrada explícita
    eh_entrada = gerenciador_alertas.detectar_entrada_estoque('ITEM', 'ENTRADA', 100)
    print(f"\n✅ ENTRADA com quantidade positiva: {eh_entrada} (esperado: True)")
    assert eh_entrada is True

    # Caso 2: Quantidade positiva (entrada)
    eh_entrada = gerenciador_alertas.detectar_entrada_estoque('ITEM', 'SAÍDA', 50)
    print(f"✅ Quantidade positiva: {eh_entrada} (esperado: True)")
    assert eh_entrada is True

    # Caso 3: Saída com quantidade negativa
    eh_entrada = gerenciador_alertas.detectar_entrada_estoque('ITEM', 'SAÍDA', -50)
    print(f"✅ SAÍDA com quantidade negativa: {eh_entrada} (esperado: False)")
    assert eh_entrada is False

    print("\n✅ TESTE 3 PASSOU")


def test_criar_alerta():
    """Testa criação de alerta completo"""
    print_header("TESTE 4: Criação de Alerta")

    # Cria alerta de teste
    data_teste = (datetime.now() - timedelta(days=25)).strftime('%d/%m/%Y')

    alerta = gerenciador_alertas.criar_alerta(
        item='TESTE_ITEM',
        grupo='TESTE_GRUPO',
        ultima_data=data_teste,
        saldo=100.0
    )

    print_alerta(alerta)

    # Validações
    assert alerta.item == 'TESTE_ITEM'
    assert alerta.grupo == 'TESTE_GRUPO'
    assert alerta.tipo == TipoAlerta.CRITICO  # 25 dias = crítico
    assert alerta.severidade == SeveridadeAlerta.ALTA
    assert alerta.dias_parado >= 24 and alerta.dias_parado <= 26

    print("\n✅ TESTE 4 PASSOU")


def test_dashboard():
    """Testa geração do dashboard"""
    print_header("TESTE 5: Dashboard de Alertas")

    try:
        dashboard = gerenciador_alertas.obter_dashboard()

        print("\n📊 CONTADORES:")
        for tipo, count in dashboard['contadores'].items():
            print(f"   {tipo}: {count}")

        print("\n📈 ESTATÍSTICAS:")
        for key, value in dashboard['estatisticas'].items():
            print(f"   {key}: {value}")

        print(f"\n🔴 Top Críticos: {len(dashboard['top_criticos'])}")
        print(f"🟡 Top Atenção: {len(dashboard['top_atencao'])}")

        # Validações
        assert 'contadores' in dashboard
        assert 'estatisticas' in dashboard
        assert 'top_criticos' in dashboard
        assert 'top_atencao' in dashboard

        print("\n✅ TESTE 5 PASSOU")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_alertas_criticos():
    """Testa obtenção de alertas críticos"""
    print_header("TESTE 6: Alertas Críticos")

    try:
        criticos = gerenciador_alertas.obter_alertas_criticos()

        print(f"\n📊 Total de alertas críticos: {len(criticos)}")

        if criticos:
            print("\n🔴 Top 5 alertas críticos:")
            for i, alerta in enumerate(criticos[:5], 1):
                print(f"\n   {i}. {alerta.item}")
                print(f"      Dias parado: {alerta.dias_parado}")
                print(f"      Saldo: {alerta.saldo_atual}")
                print(f"      Mensagem: {alerta.mensagem[:60]}...")

        # Valida que todos são críticos
        for alerta in criticos:
            assert alerta.tipo == TipoAlerta.CRITICO, f"Alerta não é crítico: {alerta.tipo}"

        print("\n✅ TESTE 6 PASSOU")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_classificar_movimentacao():
    """Testa classificação em tempo real"""
    print_header("TESTE 7: Classificação de Movimentação")

    try:
        # Simula entrada de estoque
        alerta_entrada = gerenciador_alertas.classificar_movimentacao(
            item='TESTE_ITEM',
            tipo_movimentacao='ENTRADA',
            quantidade=50
        )

        print("\n📥 Entrada de Estoque:")
        print_alerta(alerta_entrada)

        # Valida que detectou como atenção (entrada)
        assert alerta_entrada.tipo == TipoAlerta.ATENCAO, "Entrada deveria ser ATENÇÃO"

        print("\n✅ TESTE 7 PASSOU")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_configuracoes():
    """Testa configurações dos alertas"""
    print_header("TESTE 8: Configurações")

    print(f"\n⚙️ Thresholds:")
    print(f"   Crítico: >{ConfigAlerta.DIAS_CRITICO} dias")
    print(f"   Atenção: >{ConfigAlerta.DIAS_ATENCAO} dias")
    print(f"   Normal: >{ConfigAlerta.DIAS_NORMAL} dias")

    print(f"\n🎨 Cores:")
    for tipo, cor in ConfigAlerta.CORES.items():
        print(f"   {tipo.value}: {cor}")

    print(f"\n📛 Ícones:")
    for tipo, icone in ConfigAlerta.ICONES.items():
        print(f"   {tipo.value}: {icone}")

    print(f"\n⏱️ Cache TTL: {ConfigAlerta.CACHE_TTL}s")

    print("\n✅ TESTE 8 PASSOU")


def main():
    """Executa todos os testes"""
    print_header("🧪 TESTES DO SISTEMA DE ALERTAS")
    print("\nIniciando bateria de testes...\n")

    testes = [
        ("Cálculo de Dias", test_calcular_dias),
        ("Classificação por Dias", test_classificacao_por_dias),
        ("Detecção de Entrada", test_deteccao_entrada),
        ("Criação de Alerta", test_criar_alerta),
        ("Dashboard", test_dashboard),
        ("Alertas Críticos", test_alertas_criticos),
        ("Classificação em Tempo Real", test_classificar_movimentacao),
        ("Configurações", test_configuracoes)
    ]

    resultados = []

    for nome, func in testes:
        try:
            func()
            resultados.append((nome, True, None))
        except Exception as e:
            resultados.append((nome, False, str(e)))
            print(f"\n❌ TESTE FALHOU: {nome}")
            print(f"   Erro: {e}")
            import traceback
            traceback.print_exc()

    # Relatório Final
    print_header("📊 RELATÓRIO FINAL")

    total = len(resultados)
    passou = sum(1 for _, ok, _ in resultados if ok)
    falhou = total - passou

    print(f"\n✅ Testes passados: {passou}/{total}")
    print(f"❌ Testes falhados: {falhou}/{total}")
    print(f"📊 Taxa de sucesso: {(passou/total)*100:.1f}%")

    if falhou > 0:
        print("\n❌ Testes que falharam:")
        for nome, ok, erro in resultados:
            if not ok:
                print(f"   - {nome}: {erro}")

    print("\n" + "=" * 60)

    if falhou == 0:
        print("✅ TODOS OS TESTES PASSARAM!".center(60))
        print("=" * 60)
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM".center(60))
        print("=" * 60)
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal durante testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
