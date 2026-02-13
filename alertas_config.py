#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Alertas Automáticos - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Sistema de monitoramento inteligente que detecta automaticamente:
- 🔴 CRÍTICO: Itens parados >20 dias (sem movimentação)
- 🟡 ATENÇÃO: Entrada de estoque detectada (ganhos)
- 🟢 NORMAL: Movimentação regular
- ⚪ INFO: Itens novos ou primeira movimentação

Funcionalidades:
- Classificação automática de movimentações
- Dashboard com contadores por cor
- Cache otimizado (TTL: 5 minutos)
- Detecção de padrões anormais
- Sugestões de ações
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from config import obter_planilha
from cache_config import cache_marfim
from indice_otimizado import indice_otimizado

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# ENUMS E CLASSES
# ========================================

class TipoAlerta(Enum):
    """Tipos de alertas no sistema"""
    CRITICO = "critico"      # 🔴 Vermelho
    ATENCAO = "atencao"      # 🟡 Amarelo
    NORMAL = "normal"        # 🟢 Verde
    INFO = "info"            # ⚪ Branco/Azul


class SeveridadeAlerta(Enum):
    """Níveis de severidade"""
    ALTA = 3      # Requer ação imediata
    MEDIA = 2     # Requer atenção
    BAIXA = 1     # Informativo
    NENHUMA = 0   # Tudo OK


@dataclass
class Alerta:
    """Representa um alerta no sistema"""
    tipo: TipoAlerta
    severidade: SeveridadeAlerta
    item: str
    grupo: str
    mensagem: str
    dias_parado: int
    ultima_data: str
    saldo_atual: float
    sugestao: str
    timestamp: str
    cor_hex: str
    icone: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'tipo': self.tipo.value,
            'severidade': self.severidade.value,
            'item': self.item,
            'grupo': self.grupo,
            'mensagem': self.mensagem,
            'dias_parado': self.dias_parado,
            'ultima_data': self.ultima_data,
            'saldo_atual': self.saldo_atual,
            'sugestao': self.sugestao,
            'timestamp': self.timestamp,
            'cor_hex': self.cor_hex,
            'icone': self.icone
        }


# ========================================
# CONFIGURAÇÕES
# ========================================

class ConfigAlerta:
    """Configurações dos alertas"""

    # Thresholds (limites)
    DIAS_CRITICO = 20        # >20 dias = crítico
    DIAS_ATENCAO = 10        # 10-20 dias = atenção
    DIAS_NORMAL = 7          # <7 dias = normal

    # Cores (Material Design)
    CORES = {
        TipoAlerta.CRITICO: '#F44336',  # Vermelho
        TipoAlerta.ATENCAO: '#FFC107',  # Amarelo
        TipoAlerta.NORMAL: '#4CAF50',   # Verde
        TipoAlerta.INFO: '#2196F3'      # Azul
    }

    # Ícones (Material Icons)
    ICONES = {
        TipoAlerta.CRITICO: '🔴',
        TipoAlerta.ATENCAO: '🟡',
        TipoAlerta.NORMAL: '🟢',
        TipoAlerta.INFO: '⚪'
    }

    # Cache TTL
    CACHE_TTL = 300  # 5 minutos


# ========================================
# CLASSE PRINCIPAL
# ========================================

class GerenciadorAlertas:
    """
    Gerenciador de alertas automáticos

    Uso:
        gerenciador = GerenciadorAlertas()

        # Analisa todos os itens
        alertas = gerenciador.analisar_todos_itens()

        # Obtém dashboard
        dashboard = gerenciador.obter_dashboard()

        # Classifica movimentação
        alerta = gerenciador.classificar_movimentacao('AMARELO', 'ENTRADA', 100)
    """

    def __init__(self):
        """Inicializa o gerenciador"""
        self.planilha = obter_planilha()
        logger.info("✅ GerenciadorAlertas inicializado")

    def calcular_dias_parado(self, ultima_data: str) -> int:
        """
        Calcula quantos dias desde a última movimentação

        Args:
            ultima_data: Data no formato DD/MM/YYYY

        Returns:
            Número de dias desde a última movimentação
        """
        try:
            # Parse da data
            if '/' in ultima_data:
                data_obj = datetime.strptime(ultima_data, '%d/%m/%Y')
            elif '-' in ultima_data:
                data_obj = datetime.strptime(ultima_data, '%Y-%m-%d')
            else:
                return 0

            # Calcula diferença
            hoje = datetime.now()
            diferenca = hoje - data_obj

            return diferenca.days

        except (ValueError, AttributeError) as e:
            logger.warning(f"Erro ao calcular dias parado: {e}")
            return 0

    def classificar_por_dias(self, dias_parado: int) -> TipoAlerta:
        """
        Classifica alerta baseado em dias parado

        Args:
            dias_parado: Número de dias sem movimentação

        Returns:
            Tipo do alerta
        """
        if dias_parado > ConfigAlerta.DIAS_CRITICO:
            return TipoAlerta.CRITICO
        elif dias_parado > ConfigAlerta.DIAS_ATENCAO:
            return TipoAlerta.ATENCAO
        elif dias_parado > ConfigAlerta.DIAS_NORMAL:
            return TipoAlerta.INFO
        else:
            return TipoAlerta.NORMAL

    def detectar_entrada_estoque(
        self,
        item: str,
        tipo_movimentacao: str,
        quantidade: float
    ) -> bool:
        """
        Detecta se é uma entrada de estoque (ganho)

        Args:
            item: Nome do item
            tipo_movimentacao: ENTRADA ou SAÍDA
            quantidade: Quantidade movimentada

        Returns:
            True se é entrada de estoque
        """
        tipo_upper = tipo_movimentacao.upper().strip()

        # Entrada = ENTRADA ou quantidade positiva
        if 'ENTRADA' in tipo_upper or quantidade > 0:
            return True

        return False

    def gerar_mensagem_alerta(
        self,
        tipo: TipoAlerta,
        item: str,
        dias_parado: int,
        saldo: float,
        eh_entrada: bool = False
    ) -> str:
        """
        Gera mensagem descritiva do alerta

        Args:
            tipo: Tipo do alerta
            item: Nome do item
            dias_parado: Dias sem movimentação
            saldo: Saldo atual
            eh_entrada: Se é entrada de estoque

        Returns:
            Mensagem formatada
        """
        if eh_entrada:
            return f"✨ Entrada de estoque detectada! Item: {item} (Saldo: {saldo})"

        if tipo == TipoAlerta.CRITICO:
            return f"🔴 CRÍTICO: Item '{item}' parado há {dias_parado} dias! (Saldo: {saldo})"
        elif tipo == TipoAlerta.ATENCAO:
            return f"🟡 ATENÇÃO: Item '{item}' com {dias_parado} dias sem movimentação (Saldo: {saldo})"
        elif tipo == TipoAlerta.INFO:
            return f"ℹ️ Item '{item}' com {dias_parado} dias desde última movimentação (Saldo: {saldo})"
        else:
            return f"✅ Item '{item}' com movimentação regular (Saldo: {saldo})"

    def gerar_sugestao(
        self,
        tipo: TipoAlerta,
        item: str,
        dias_parado: int,
        saldo: float,
        eh_entrada: bool = False
    ) -> str:
        """
        Gera sugestão de ação

        Args:
            tipo: Tipo do alerta
            item: Nome do item
            dias_parado: Dias sem movimentação
            saldo: Saldo atual
            eh_entrada: Se é entrada de estoque

        Returns:
            Sugestão de ação
        """
        if eh_entrada:
            return "📝 Verifique se o registro está correto. Entradas aumentam o estoque."

        if tipo == TipoAlerta.CRITICO:
            if saldo > 0:
                return f"⚠️ Item parado há {dias_parado} dias com saldo {saldo}. Considere: 1) Verificar demanda, 2) Promoção, 3) Transferência"
            else:
                return f"📦 Item zerado há {dias_parado} dias. Considere: 1) Reposição se há demanda, 2) Descontinuar se sem demanda"

        elif tipo == TipoAlerta.ATENCAO:
            return f"👀 Monitore o item. Se demanda baixa, considere ajustar estoque mínimo."

        elif tipo == TipoAlerta.INFO:
            return "✅ Movimentação dentro do esperado. Continue monitorando."

        else:
            return "✅ Tudo normal. Item com movimentação regular."

    def criar_alerta(
        self,
        item: str,
        grupo: str,
        ultima_data: str,
        saldo: float,
        tipo_movimentacao: Optional[str] = None,
        quantidade: Optional[float] = None
    ) -> Alerta:
        """
        Cria um alerta completo para um item

        Args:
            item: Nome do item
            grupo: Grupo do item
            ultima_data: Data da última movimentação
            saldo: Saldo atual
            tipo_movimentacao: ENTRADA ou SAÍDA (opcional)
            quantidade: Quantidade movimentada (opcional)

        Returns:
            Objeto Alerta
        """
        # Calcula dias parado
        dias_parado = self.calcular_dias_parado(ultima_data)

        # Detecta entrada de estoque
        eh_entrada = False
        if tipo_movimentacao and quantidade:
            eh_entrada = self.detectar_entrada_estoque(item, tipo_movimentacao, quantidade)

        # Classifica alerta
        if eh_entrada:
            tipo_alerta = TipoAlerta.ATENCAO  # Entrada = amarelo (atenção)
            severidade = SeveridadeAlerta.MEDIA
        else:
            tipo_alerta = self.classificar_por_dias(dias_parado)

            # Define severidade
            if tipo_alerta == TipoAlerta.CRITICO:
                severidade = SeveridadeAlerta.ALTA
            elif tipo_alerta == TipoAlerta.ATENCAO:
                severidade = SeveridadeAlerta.MEDIA
            else:
                severidade = SeveridadeAlerta.BAIXA

        # Gera mensagem e sugestão
        mensagem = self.gerar_mensagem_alerta(tipo_alerta, item, dias_parado, saldo, eh_entrada)
        sugestao = self.gerar_sugestao(tipo_alerta, item, dias_parado, saldo, eh_entrada)

        # Cria objeto alerta
        alerta = Alerta(
            tipo=tipo_alerta,
            severidade=severidade,
            item=item,
            grupo=grupo,
            mensagem=mensagem,
            dias_parado=dias_parado,
            ultima_data=ultima_data,
            saldo_atual=saldo,
            sugestao=sugestao,
            timestamp=datetime.now().isoformat(),
            cor_hex=ConfigAlerta.CORES[tipo_alerta],
            icone=ConfigAlerta.ICONES[tipo_alerta]
        )

        return alerta

    def analisar_todos_itens(self, forcar_recarga: bool = False) -> List[Alerta]:
        """
        Analisa todos os itens e retorna lista de alertas

        Args:
            forcar_recarga: Se True, ignora cache

        Returns:
            Lista de alertas ordenada por severidade
        """
        # Tenta cache primeiro
        if not forcar_recarga:
            alertas_cached = cache_marfim.get('alertas_todos', 'alertas')
            if alertas_cached:
                logger.debug("⚡ Alertas retornados do cache")
                # Converte dicionários de volta para objetos Alerta
                return [
                    Alerta(**a) if isinstance(a, dict) else a
                    for a in alertas_cached
                ]

        logger.info("🔍 Analisando todos os itens...")

        # Obtém índice completo
        indice = indice_otimizado.obter_indice()

        alertas = []

        for item_key, dados in indice.items():
            try:
                alerta = self.criar_alerta(
                    item=dados['item_original'],
                    grupo=dados.get('grupo', ''),
                    ultima_data=dados.get('data', ''),
                    saldo=float(dados.get('saldo', 0))
                )

                alertas.append(alerta)

            except Exception as e:
                logger.warning(f"Erro ao criar alerta para {item_key}: {e}")
                continue

        # Ordena por severidade (ALTA -> BAIXA)
        alertas.sort(key=lambda a: a.severidade.value, reverse=True)

        # Salva em cache (converte para dict para serialização)
        alertas_dict = [a.to_dict() for a in alertas]
        cache_marfim.set('alertas_todos', alertas_dict, 'alertas')

        logger.info(f"✅ Análise concluída: {len(alertas)} alertas gerados")

        return alertas

    def obter_alertas_criticos(self) -> List[Alerta]:
        """
        Retorna apenas alertas críticos

        Returns:
            Lista de alertas críticos
        """
        todos_alertas = self.analisar_todos_itens()
        return [a for a in todos_alertas if a.tipo == TipoAlerta.CRITICO]

    def obter_alertas_atencao(self) -> List[Alerta]:
        """
        Retorna apenas alertas de atenção

        Returns:
            Lista de alertas de atenção
        """
        todos_alertas = self.analisar_todos_itens()
        return [a for a in todos_alertas if a.tipo == TipoAlerta.ATENCAO]

    def obter_dashboard(self) -> Dict[str, Any]:
        """
        Retorna dashboard completo de alertas

        Returns:
            Dicionário com contadores e estatísticas
        """
        # Tenta cache
        dashboard_cached = cache_marfim.get('dashboard_alertas', 'dashboard')
        if dashboard_cached:
            logger.debug("⚡ Dashboard de alertas do cache")
            return dashboard_cached

        # Analisa todos
        alertas = self.analisar_todos_itens()

        # Contadores por tipo
        contadores = {
            'critico': 0,
            'atencao': 0,
            'normal': 0,
            'info': 0,
            'total': len(alertas)
        }

        for alerta in alertas:
            contadores[alerta.tipo.value] += 1

        # Top 10 críticos
        criticos = [a for a in alertas if a.tipo == TipoAlerta.CRITICO][:10]

        # Top 10 atenção
        atencao = [a for a in alertas if a.tipo == TipoAlerta.ATENCAO][:10]

        # Estatísticas
        if alertas:
            media_dias = sum(a.dias_parado for a in alertas) / len(alertas)
            max_dias = max(a.dias_parado for a in alertas)
        else:
            media_dias = 0
            max_dias = 0

        dashboard = {
            'contadores': contadores,
            'top_criticos': [a.to_dict() for a in criticos],
            'top_atencao': [a.to_dict() for a in atencao],
            'estatisticas': {
                'total_itens': len(alertas),
                'media_dias_parado': round(media_dias, 1),
                'max_dias_parado': max_dias,
                'porcentagem_critico': round((contadores['critico'] / len(alertas) * 100) if alertas else 0, 1),
                'porcentagem_atencao': round((contadores['atencao'] / len(alertas) * 100) if alertas else 0, 1)
            },
            'timestamp': datetime.now().isoformat()
        }

        # Salva em cache
        cache_marfim.set('dashboard_alertas', dashboard, 'dashboard')

        return dashboard

    def classificar_movimentacao(
        self,
        item: str,
        tipo_movimentacao: str,
        quantidade: float
    ) -> Alerta:
        """
        Classifica uma movimentação em tempo real

        Args:
            item: Nome do item
            tipo_movimentacao: ENTRADA ou SAÍDA
            quantidade: Quantidade movimentada

        Returns:
            Alerta para a movimentação
        """
        # Busca dados do item
        dados_item = indice_otimizado.buscar_item(item)

        if not dados_item:
            # Item novo
            return self.criar_alerta(
                item=item,
                grupo='',
                ultima_data=datetime.now().strftime('%d/%m/%Y'),
                saldo=quantidade if tipo_movimentacao.upper() == 'ENTRADA' else -quantidade,
                tipo_movimentacao=tipo_movimentacao,
                quantidade=quantidade
            )

        # Cria alerta com dados existentes
        return self.criar_alerta(
            item=dados_item['item_original'],
            grupo=dados_item.get('grupo', ''),
            ultima_data=dados_item.get('data', ''),
            saldo=float(dados_item.get('saldo', 0)),
            tipo_movimentacao=tipo_movimentacao,
            quantidade=quantidade
        )

    def invalidar_cache(self):
        """Invalida cache de alertas"""
        cache_marfim.invalidate('alertas*')
        cache_marfim.invalidate('dashboard_alertas')
        logger.info("🗑️ Cache de alertas invalidado")


# ========================================
# SINGLETON GLOBAL
# ========================================
gerenciador_alertas = GerenciadorAlertas()


# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def obter_badge_html(tipo: TipoAlerta, contador: int) -> str:
    """
    Gera HTML de badge para exibição

    Args:
        tipo: Tipo do alerta
        contador: Número de alertas

    Returns:
        HTML do badge
    """
    cor = ConfigAlerta.CORES[tipo]
    icone = ConfigAlerta.ICONES[tipo]

    return f'''
    <span class="badge" style="background-color: {cor}; color: white; padding: 5px 10px; border-radius: 12px; font-weight: bold;">
        {icone} {contador}
    </span>
    '''


if __name__ == '__main__':
    # Testes básicos
    print("🧪 Testando GerenciadorAlertas...")

    # Teste 1: Dashboard
    print("\n1. Obtendo dashboard de alertas...")
    dashboard = gerenciador_alertas.obter_dashboard()
    print(f"   Total de alertas: {dashboard['contadores']['total']}")
    print(f"   Críticos: {dashboard['contadores']['critico']}")
    print(f"   Atenção: {dashboard['contadores']['atencao']}")
    print(f"   Normal: {dashboard['contadores']['normal']}")

    # Teste 2: Alertas críticos
    print("\n2. Obtendo alertas críticos...")
    criticos = gerenciador_alertas.obter_alertas_criticos()
    print(f"   Total críticos: {len(criticos)}")
    if criticos:
        print(f"   Primeiro: {criticos[0].mensagem}")

    # Teste 3: Classificar movimentação
    print("\n3. Classificando movimentação...")
    alerta = gerenciador_alertas.classificar_movimentacao('TESTE', 'ENTRADA', 100)
    print(f"   Tipo: {alerta.tipo.value}")
    print(f"   Mensagem: {alerta.mensagem}")

    print("\n✅ Todos os testes concluídos!")
