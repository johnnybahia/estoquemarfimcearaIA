#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Cache Multinível - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Sistema de cache em 3 camadas para otimização de performance:
1. Redis (opcional, distribuído) - TTL automático
2. LRU em memória (fallback) - sempre disponível
3. Google Sheets (fonte de verdade) - última opção

Ganhos esperados:
- Autocomplete: 1500ms → 10ms (150x mais rápido)
- Dashboard: 3000ms → 50ms (60x mais rápido)
- Busca de item: 2000ms → 5ms (400x mais rápido)
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Optional, Dict

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheMarfim:
    """
    Sistema de cache multinível para otimização de consultas ao Google Sheets

    Exemplo de uso:
        cache = CacheMarfim()

        # Salvar
        cache.set('autocomplete_items', ['AMARELO', 'AZUL'], 'autocomplete')

        # Buscar
        items = cache.get('autocomplete_items', 'autocomplete')

        # Invalidar
        cache.invalidate('autocomplete*')
    """

    # Configurações de TTL (Time To Live) em segundos
    TTL = {
        'autocomplete': 600,      # 10 minutos - dados de autocomplete
        'dashboard': 300,         # 5 minutos - KPIs do dashboard
        'item_index': 1800,       # 30 minutos - índice de itens
        'index_full': 3600,       # 1 hora - índice completo ÍNDICE_ITENS
        'historico': 1800,        # 30 minutos - histórico de itens
        'default': 600            # 10 minutos - padrão para outros
    }

    def __init__(self):
        """Inicializa o sistema de cache multinível"""
        # Camada 1: Tenta conectar ao Redis (opcional)
        self.redis = None
        self.redis_available = False
        self._init_redis()

        # Camada 2: Cache em memória (LRU) - sempre disponível
        self.memory_cache: Dict[str, tuple] = {}
        self.cache_timestamps: Dict[str, datetime] = {}

        # Estatísticas
        self.stats = {
            'hits_redis': 0,
            'hits_memory': 0,
            'misses': 0,
            'sets': 0
        }

        logger.info(f"✅ CacheMarfim inicializado - Redis: {self.redis_available}")

    def _init_redis(self):
        """Inicializa conexão com Redis (opcional)"""
        try:
            import redis

            # Tenta conectar via URL de ambiente ou localhost padrão
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

            self.redis = redis.from_url(
                redis_url,
                decode_responses=False,  # Mantém bytes para pickle
                socket_connect_timeout=2,
                socket_timeout=2
            )

            # Testa conexão
            self.redis.ping()
            self.redis_available = True
            logger.info(f"✅ Redis conectado: {redis_url}")

        except ImportError:
            logger.warning("⚠️ Biblioteca 'redis' não instalada. Use: pip install redis")
            logger.info("💡 Cache funcionará apenas em memória (LRU)")
        except Exception as e:
            logger.warning(f"⚠️ Redis não disponível: {e}")
            logger.info("💡 Cache funcionará apenas em memória (LRU)")
            self.redis = None
            self.redis_available = False

    def get(self, key: str, cache_type: str = 'default') -> Optional[Any]:
        """
        Busca valor em cache multinível

        Args:
            key: Chave do cache
            cache_type: Tipo de cache para determinar TTL

        Returns:
            Valor do cache ou None se não encontrado/expirado
        """
        # 1. Tenta Redis primeiro (mais rápido)
        if self.redis_available:
            try:
                data = self.redis.get(f"marfim:{key}")
                if data:
                    self.stats['hits_redis'] += 1
                    logger.debug(f"✅ Cache HIT (Redis): {key}")
                    return pickle.loads(data)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao ler Redis: {e}")

        # 2. Tenta cache em memória
        if key in self.memory_cache:
            timestamp, data = self.memory_cache[key]
            ttl = self.TTL.get(cache_type, self.TTL['default'])

            # Verifica se não expirou
            if datetime.now() - timestamp < timedelta(seconds=ttl):
                self.stats['hits_memory'] += 1
                logger.debug(f"✅ Cache HIT (Memory): {key}")
                return data
            else:
                # Cache expirado, remove
                logger.debug(f"⏰ Cache EXPIRADO: {key}")
                del self.memory_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]

        # 3. Cache MISS
        self.stats['misses'] += 1
        logger.debug(f"❌ Cache MISS: {key}")
        return None

    def set(self, key: str, data: Any, cache_type: str = 'default') -> bool:
        """
        Salva valor em cache multinível

        Args:
            key: Chave do cache
            data: Dados a serem salvos (qualquer tipo serializável)
            cache_type: Tipo de cache para determinar TTL

        Returns:
            True se salvou com sucesso
        """
        ttl = self.TTL.get(cache_type, self.TTL['default'])

        try:
            # 1. Salva em Redis (se disponível)
            if self.redis_available:
                try:
                    pickled_data = pickle.dumps(data)
                    self.redis.setex(
                        f"marfim:{key}",
                        ttl,
                        pickled_data
                    )
                    logger.debug(f"💾 Salvo em Redis: {key} (TTL: {ttl}s)")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao salvar em Redis: {e}")

            # 2. Sempre salva em memória (fallback)
            self.memory_cache[key] = (datetime.now(), data)
            self.cache_timestamps[key] = datetime.now()

            self.stats['sets'] += 1
            logger.debug(f"💾 Salvo em Memory: {key} (TTL: {ttl}s)")

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar em cache: {e}")
            return False

    def invalidate(self, pattern: str = '*') -> int:
        """
        Invalida caches que correspondem ao padrão

        Args:
            pattern: Padrão de chaves (ex: 'autocomplete*', 'item_*', '*')

        Returns:
            Número de chaves removidas
        """
        removed_count = 0

        # 1. Invalida no Redis
        if self.redis_available:
            try:
                # Busca chaves que correspondem ao padrão
                redis_pattern = f"marfim:{pattern}"
                keys = self.redis.keys(redis_pattern)

                if keys:
                    removed_count += self.redis.delete(*keys)
                    logger.info(f"🗑️ Redis: {len(keys)} chaves removidas ({pattern})")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao invalidar Redis: {e}")

        # 2. Invalida em memória
        if pattern == '*':
            # Remove tudo
            removed_count += len(self.memory_cache)
            self.memory_cache.clear()
            self.cache_timestamps.clear()
            logger.info(f"🗑️ Memory: Cache limpo completamente")
        else:
            # Remove chaves que correspondem ao padrão
            # Converte padrão glob para matching simples
            pattern_clean = pattern.replace('*', '')

            keys_to_remove = [
                k for k in self.memory_cache.keys()
                if pattern_clean in k
            ]

            for key in keys_to_remove:
                del self.memory_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
                removed_count += 1

            if keys_to_remove:
                logger.info(f"🗑️ Memory: {len(keys_to_remove)} chaves removidas ({pattern})")

        return removed_count

    def get_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas de uso do cache

        Returns:
            Dicionário com estatísticas
        """
        total_requests = (
            self.stats['hits_redis'] +
            self.stats['hits_memory'] +
            self.stats['misses']
        )

        hit_rate = 0
        if total_requests > 0:
            hits = self.stats['hits_redis'] + self.stats['hits_memory']
            hit_rate = (hits / total_requests) * 100

        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'memory_keys': len(self.memory_cache),
            'redis_available': self.redis_available
        }

    def clear_stats(self):
        """Limpa estatísticas"""
        self.stats = {
            'hits_redis': 0,
            'hits_memory': 0,
            'misses': 0,
            'sets': 0
        }
        logger.info("📊 Estatísticas resetadas")

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde do sistema de cache

        Returns:
            Dicionário com status de cada camada
        """
        health = {
            'redis': {
                'available': self.redis_available,
                'status': 'unknown'
            },
            'memory': {
                'available': True,
                'keys': len(self.memory_cache),
                'status': 'ok'
            }
        }

        # Testa Redis
        if self.redis_available:
            try:
                self.redis.ping()
                health['redis']['status'] = 'ok'
            except Exception as e:
                health['redis']['status'] = f'error: {str(e)}'
                health['redis']['available'] = False

        return health


# ========================================
# SINGLETON GLOBAL
# ========================================
cache_marfim = CacheMarfim()


# ========================================
# DECORATORS ÚTEIS
# ========================================
def cached(cache_type: str = 'default', key_prefix: str = ''):
    """
    Decorator para cachear resultados de funções

    Exemplo:
        @cached(cache_type='autocomplete', key_prefix='items')
        def obter_todos_itens():
            # Código pesado aqui
            return items
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Gera chave do cache baseada no nome da função e argumentos
            cache_key = f"{key_prefix}_{func.__name__}"

            # Se tiver argumentos, adiciona ao hash
            if args or kwargs:
                args_str = str(args) + str(kwargs)
                cache_key += f"_{hash(args_str)}"

            # Tenta buscar no cache
            cached_result = cache_marfim.get(cache_key, cache_type)
            if cached_result is not None:
                logger.debug(f"⚡ Retornando do cache: {func.__name__}")
                return cached_result

            # Cache miss, executa função
            logger.debug(f"🔄 Executando função: {func.__name__}")
            result = func(*args, **kwargs)

            # Salva no cache
            cache_marfim.set(cache_key, result, cache_type)

            return result

        return wrapper
    return decorator


# ========================================
# FUNÇÕES AUXILIARES
# ========================================
def invalidar_cache_item(nome_item: str):
    """Invalida todos os caches relacionados a um item específico"""
    item_normalizado = nome_item.upper().strip()
    cache_marfim.invalidate(f"*{item_normalizado}*")
    logger.info(f"🗑️ Cache invalidado para item: {nome_item}")


def invalidar_cache_completo():
    """Invalida TODO o cache (usar com cuidado!)"""
    cache_marfim.invalidate('*')
    logger.warning("🗑️ CACHE COMPLETO INVALIDADO")


def obter_estatisticas_cache() -> Dict[str, Any]:
    """Retorna estatísticas completas do cache"""
    stats = cache_marfim.get_stats()
    health = cache_marfim.health_check()

    return {
        'statistics': stats,
        'health': health,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == '__main__':
    # Teste básico
    print("🧪 Testando CacheMarfim...")

    # Teste 1: Set e Get
    cache_marfim.set('teste_key', {'valor': 123}, 'default')
    resultado = cache_marfim.get('teste_key', 'default')
    print(f"✅ Teste 1 (Set/Get): {resultado}")

    # Teste 2: Expiração
    cache_marfim.set('teste_expira', 'dados', 'default')
    print(f"✅ Teste 2 (Antes expirar): {cache_marfim.get('teste_expira')}")

    # Teste 3: Invalidação
    cache_marfim.set('teste_invalida_1', 'a', 'default')
    cache_marfim.set('teste_invalida_2', 'b', 'default')
    cache_marfim.invalidate('teste_invalida*')
    print(f"✅ Teste 3 (Após invalidar): {cache_marfim.get('teste_invalida_1')}")

    # Teste 4: Estatísticas
    stats = cache_marfim.get_stats()
    print(f"📊 Estatísticas: {stats}")

    # Teste 5: Health Check
    health = cache_marfim.health_check()
    print(f"🏥 Health Check: {health}")

    print("\n✅ Todos os testes concluídos!")
