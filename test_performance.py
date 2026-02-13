#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste de Performance - Cache Multinível
Autor: Johnny
Data: 2026-02-13

Testa e compara performance ANTES vs DEPOIS da implementação de cache
"""

import time
import sys
from typing import Callable, Tuple
from config import obter_planilha
from cache_config import cache_marfim
from indice_otimizado import indice_otimizado


def medir_tempo(funcao: Callable, nome: str, repeticoes: int = 5) -> Tuple[float, any]:
    """
    Mede tempo de execução de uma função

    Args:
        funcao: Função a ser medida
        nome: Nome descritivo
        repeticoes: Número de execuções para média

    Returns:
        Tupla (tempo_medio_ms, resultado)
    """
    tempos = []
    resultado = None

    print(f"\n⏱️  Testando: {nome}")
    print(f"   Repetições: {repeticoes}")

    for i in range(repeticoes):
        inicio = time.time()
        resultado = funcao()
        fim = time.time()

        tempo_ms = (fim - inicio) * 1000
        tempos.append(tempo_ms)

        print(f"   #{i+1}: {tempo_ms:.2f}ms")

    tempo_medio = sum(tempos) / len(tempos)
    print(f"   📊 Média: {tempo_medio:.2f}ms")

    return tempo_medio, resultado


def test_busca_item_sem_cache():
    """Busca item SEM cache (lê planilha inteira)"""
    planilha = obter_planilha()
    aba_estoque = planilha.worksheet("ESTOQUE")
    dados = aba_estoque.get_all_values()[1:]

    # Busca linear por "AMARELO" (ou primeiro item)
    for linha in dados:
        if len(linha) > 1 and linha[1]:
            if 'AMARELO' in linha[1].upper():
                return linha[1]

    # Se não encontrou, retorna primeiro item
    return dados[0][1] if dados else None


def test_busca_item_com_cache():
    """Busca item COM cache (índice otimizado)"""
    # Busca "AMARELO" ou usa primeiro item disponível
    item = indice_otimizado.buscar_item('AMARELO')

    if not item:
        # Se não encontrou, busca qualquer item
        itens = indice_otimizado.obter_todos_itens()
        if itens:
            item = indice_otimizado.buscar_item(itens[0])

    return item


def test_autocomplete_sem_cache():
    """Autocomplete SEM cache"""
    planilha = obter_planilha()
    aba_estoque = planilha.worksheet("ESTOQUE")
    dados = aba_estoque.get_all_values()[1:]

    # Extrai itens únicos
    itens = set()
    for linha in dados:
        if len(linha) > 1 and linha[1]:
            itens.add(linha[1])

    return list(itens)


def test_autocomplete_com_cache():
    """Autocomplete COM cache"""
    itens = indice_otimizado.obter_todos_itens()
    return itens


def test_dashboard_sem_cache():
    """Dashboard SEM cache (múltiplas leituras)"""
    planilha = obter_planilha()
    aba_estoque = planilha.worksheet("ESTOQUE")
    dados = aba_estoque.get_all_values()[1:]

    # Conta itens únicos
    itens = set()
    grupos = set()

    for linha in dados:
        if len(linha) > 1:
            if linha[1]:
                itens.add(linha[1])
            if linha[0]:
                grupos.add(linha[0])

    return {
        'total_itens': len(itens),
        'total_grupos': len(grupos),
        'total_linhas': len(dados)
    }


def test_dashboard_com_cache():
    """Dashboard COM cache"""
    itens = indice_otimizado.obter_todos_itens()
    grupos = indice_otimizado.obter_todos_grupos()

    return {
        'total_itens': len(itens),
        'total_grupos': len(grupos)
    }


def calcular_melhoria(tempo_antes: float, tempo_depois: float) -> str:
    """Calcula percentual de melhoria"""
    if tempo_depois == 0:
        return "∞x mais rápido!"

    melhoria = tempo_antes / tempo_depois

    if melhoria < 1:
        return f"{(1/melhoria):.1f}x mais lento ⚠️"
    else:
        return f"{melhoria:.1f}x mais rápido! 🚀"


def main():
    """Executa todos os testes de performance"""
    print("=" * 60)
    print("🧪 TESTE DE PERFORMANCE - Cache Multinível")
    print("=" * 60)

    # AVISO: Cache limpo para testes justos
    print("\n⚠️  Limpando cache para testes justos...")
    cache_marfim.invalidate('*')

    # Aguarda um pouco
    time.sleep(1)

    resultados = {}

    # ========================================
    # TESTE 1: Busca de Item
    # ========================================
    print("\n" + "=" * 60)
    print("📦 TESTE 1: Busca de Item Individual")
    print("=" * 60)

    # Sem cache (primeira execução)
    tempo_sem_cache, _ = medir_tempo(
        test_busca_item_sem_cache,
        "Busca SEM cache (lê planilha inteira)",
        repeticoes=3
    )

    # Com cache (primeira execução - cache miss)
    cache_marfim.invalidate('indice_completo')
    tempo_com_cache_miss, _ = medir_tempo(
        test_busca_item_com_cache,
        "Busca COM cache (primeira vez - miss)",
        repeticoes=1
    )

    # Com cache (hit)
    tempo_com_cache_hit, _ = medir_tempo(
        test_busca_item_com_cache,
        "Busca COM cache (hit)",
        repeticoes=5
    )

    resultados['busca_item'] = {
        'sem_cache': tempo_sem_cache,
        'com_cache_miss': tempo_com_cache_miss,
        'com_cache_hit': tempo_com_cache_hit,
        'melhoria': calcular_melhoria(tempo_sem_cache, tempo_com_cache_hit)
    }

    # ========================================
    # TESTE 2: Autocomplete
    # ========================================
    print("\n" + "=" * 60)
    print("🔍 TESTE 2: Autocomplete (Lista de Itens)")
    print("=" * 60)

    # Sem cache
    tempo_auto_sem, _ = medir_tempo(
        test_autocomplete_sem_cache,
        "Autocomplete SEM cache",
        repeticoes=3
    )

    # Com cache (hit)
    tempo_auto_com, _ = medir_tempo(
        test_autocomplete_com_cache,
        "Autocomplete COM cache",
        repeticoes=5
    )

    resultados['autocomplete'] = {
        'sem_cache': tempo_auto_sem,
        'com_cache': tempo_auto_com,
        'melhoria': calcular_melhoria(tempo_auto_sem, tempo_auto_com)
    }

    # ========================================
    # TESTE 3: Dashboard
    # ========================================
    print("\n" + "=" * 60)
    print("📊 TESTE 3: Dashboard (Múltiplas Consultas)")
    print("=" * 60)

    # Sem cache
    tempo_dash_sem, _ = medir_tempo(
        test_dashboard_sem_cache,
        "Dashboard SEM cache",
        repeticoes=3
    )

    # Com cache
    tempo_dash_com, _ = medir_tempo(
        test_dashboard_com_cache,
        "Dashboard COM cache",
        repeticoes=5
    )

    resultados['dashboard'] = {
        'sem_cache': tempo_dash_sem,
        'com_cache': tempo_dash_com,
        'melhoria': calcular_melhoria(tempo_dash_sem, tempo_dash_com)
    }

    # ========================================
    # RELATÓRIO FINAL
    # ========================================
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DE PERFORMANCE")
    print("=" * 60)

    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│ TESTE 1: Busca de Item                                 │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ SEM cache:       {resultados['busca_item']['sem_cache']:>10.2f}ms (lê planilha)  │")
    print(f"│ COM cache (hit): {resultados['busca_item']['com_cache_hit']:>10.2f}ms                  │")
    print(f"│ Melhoria:        {resultados['busca_item']['melhoria']:>30} │")
    print("└─────────────────────────────────────────────────────────┘")

    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│ TESTE 2: Autocomplete                                   │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ SEM cache:       {resultados['autocomplete']['sem_cache']:>10.2f}ms                  │")
    print(f"│ COM cache:       {resultados['autocomplete']['com_cache']:>10.2f}ms                  │")
    print(f"│ Melhoria:        {resultados['autocomplete']['melhoria']:>30} │")
    print("└─────────────────────────────────────────────────────────┘")

    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│ TESTE 3: Dashboard                                      │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ SEM cache:       {resultados['dashboard']['sem_cache']:>10.2f}ms                  │")
    print(f"│ COM cache:       {resultados['dashboard']['com_cache']:>10.2f}ms                  │")
    print(f"│ Melhoria:        {resultados['dashboard']['melhoria']:>30} │")
    print("└─────────────────────────────────────────────────────────┘")

    # Estatísticas de cache
    print("\n" + "=" * 60)
    print("📊 ESTATÍSTICAS DO CACHE")
    print("=" * 60)

    stats = cache_marfim.get_stats()
    print(f"\n✅ Hits Redis:    {stats['hits_redis']}")
    print(f"✅ Hits Memória:  {stats['hits_memory']}")
    print(f"❌ Misses:        {stats['misses']}")
    print(f"📊 Total:         {stats['total_requests']}")
    print(f"🎯 Hit Rate:      {stats['hit_rate_percent']:.1f}%")
    print(f"💾 Keys Memory:   {stats['memory_keys']}")
    print(f"🔌 Redis:         {'✅ Disponível' if stats['redis_available'] else '❌ Indisponível'}")

    # Health check
    print("\n" + "=" * 60)
    print("🏥 HEALTH CHECK")
    print("=" * 60)

    health = cache_marfim.health_check()
    print(f"\n🔌 Redis:   {health['redis']['status']}")
    print(f"💾 Memória: {health['memory']['status']} ({health['memory']['keys']} keys)")

    print("\n" + "=" * 60)
    print("✅ Testes concluídos com sucesso!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testes interrompidos pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro durante testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
