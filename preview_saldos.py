#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Preview de Saldos - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Mostra preview do saldo ANTES de confirmar movimentação:
- 👁️ Saldo atual
- 🔢 Novo saldo (calculado)
- ⚠️ Alertas se ficará negativo
- ✅ Validação antes de inserir

Benefícios:
- Zero inserções erradas
- Validação visual
- Confirmação com dados completos
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from indice_otimizado import indice_otimizado
from cache_config import cache_marfim

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# ENUMS E CLASSES
# ========================================

class StatusPreview(Enum):
    """Status do preview de saldo"""
    OK = "ok"                    # ✅ Tudo OK
    ATENCAO = "atencao"          # ⚠️ Saldo ficará baixo
    CRITICO = "critico"          # 🔴 Saldo ficará negativo
    ITEM_NOVO = "item_novo"      # 🆕 Item não existe


class TipoMovimentacao(Enum):
    """Tipos de movimentação"""
    ENTRADA = "entrada"
    SAIDA = "saida"


@dataclass
class PreviewSaldo:
    """Dados do preview de saldo"""
    item: str
    grupo: str
    tipo_movimentacao: str
    quantidade: float
    saldo_atual: float
    novo_saldo: float
    diferenca: float
    status: StatusPreview
    mensagem: str
    alerta: Optional[str]
    recomendacao: str
    pode_confirmar: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'item': self.item,
            'grupo': self.grupo,
            'tipo_movimentacao': self.tipo_movimentacao,
            'quantidade': self.quantidade,
            'saldo_atual': self.saldo_atual,
            'novo_saldo': self.novo_saldo,
            'diferenca': self.diferenca,
            'status': self.status.value,
            'mensagem': self.mensagem,
            'alerta': self.alerta,
            'recomendacao': self.recomendacao,
            'pode_confirmar': self.pode_confirmar,
            'timestamp': self.timestamp
        }


# ========================================
# CONFIGURAÇÕES
# ========================================

class ConfigPreview:
    """Configurações do preview"""

    # Limites de alerta
    SALDO_MINIMO_ATENCAO = 10    # Abaixo disso = atenção
    PERMITIR_SALDO_NEGATIVO = False  # Se True, permite negativo com confirmação

    # Cache
    CACHE_TTL = 60  # 1 minuto (dados de preview são temporários)


# ========================================
# CLASSE PRINCIPAL
# ========================================

class GerenciadorPreview:
    """
    Gerenciador de preview de saldos

    Uso:
        gerenciador = GerenciadorPreview()

        # Preview de movimentação
        preview = gerenciador.calcular_preview(
            item='AMARELO 1234',
            tipo_movimentacao='SAIDA',
            quantidade=100
        )

        if preview.pode_confirmar:
            # Prossegue com inserção
            pass
        else:
            # Mostra alerta
            print(preview.alerta)
    """

    def __init__(self):
        """Inicializa o gerenciador"""
        logger.info("✅ GerenciadorPreview inicializado")

    def normalizar_tipo_movimentacao(self, tipo: str) -> TipoMovimentacao:
        """
        Normaliza tipo de movimentação

        Args:
            tipo: ENTRADA, SAÍDA, entrada, saida, etc.

        Returns:
            TipoMovimentacao
        """
        tipo_upper = tipo.upper().strip()

        # Remove acentos
        tipo_upper = tipo_upper.replace('Á', 'A').replace('Ã', 'A').replace('Í', 'I')

        if 'ENTRADA' in tipo_upper or 'GANHO' in tipo_upper:
            return TipoMovimentacao.ENTRADA
        elif 'SAIDA' in tipo_upper or 'SAÍDA' in tipo_upper or 'PERDA' in tipo_upper:
            return TipoMovimentacao.SAIDA
        else:
            # Padrão: se quantidade positiva = entrada, negativa = saída
            return TipoMovimentacao.ENTRADA

    def calcular_novo_saldo(
        self,
        saldo_atual: float,
        tipo_movimentacao: TipoMovimentacao,
        quantidade: float
    ) -> float:
        """
        Calcula novo saldo baseado na movimentação

        Args:
            saldo_atual: Saldo atual
            tipo_movimentacao: ENTRADA ou SAIDA
            quantidade: Quantidade (sempre positiva)

        Returns:
            Novo saldo calculado
        """
        quantidade_abs = abs(quantidade)

        if tipo_movimentacao == TipoMovimentacao.ENTRADA:
            return saldo_atual + quantidade_abs
        else:  # SAIDA
            return saldo_atual - quantidade_abs

    def determinar_status(
        self,
        saldo_atual: float,
        novo_saldo: float,
        tipo_movimentacao: TipoMovimentacao,
        item_existe: bool
    ) -> StatusPreview:
        """
        Determina status do preview

        Args:
            saldo_atual: Saldo atual
            novo_saldo: Novo saldo calculado
            tipo_movimentacao: Tipo da movimentação
            item_existe: Se item existe no índice

        Returns:
            StatusPreview
        """
        if not item_existe:
            return StatusPreview.ITEM_NOVO

        if novo_saldo < 0:
            return StatusPreview.CRITICO

        if novo_saldo < ConfigPreview.SALDO_MINIMO_ATENCAO:
            return StatusPreview.ATENCAO

        return StatusPreview.OK

    def gerar_mensagem(
        self,
        status: StatusPreview,
        item: str,
        saldo_atual: float,
        novo_saldo: float,
        tipo_movimentacao: TipoMovimentacao
    ) -> str:
        """Gera mensagem descritiva do preview"""

        if status == StatusPreview.ITEM_NOVO:
            if tipo_movimentacao == TipoMovimentacao.ENTRADA:
                return f"🆕 Novo item '{item}' será criado com saldo inicial de {novo_saldo}"
            else:
                return f"🆕 Novo item '{item}' será criado com saldo {novo_saldo} (negativo!)"

        if status == StatusPreview.CRITICO:
            return f"🔴 ATENÇÃO: Saldo ficará NEGATIVO! {saldo_atual} → {novo_saldo}"

        if status == StatusPreview.ATENCAO:
            return f"⚠️ Saldo ficará baixo: {saldo_atual} → {novo_saldo}"

        # OK
        if tipo_movimentacao == TipoMovimentacao.ENTRADA:
            return f"✅ Entrada de estoque: {saldo_atual} → {novo_saldo} (+{abs(novo_saldo - saldo_atual)})"
        else:
            return f"✅ Saída de estoque: {saldo_atual} → {novo_saldo} (-{abs(saldo_atual - novo_saldo)})"

    def gerar_alerta(self, status: StatusPreview, novo_saldo: float) -> Optional[str]:
        """Gera mensagem de alerta se necessário"""

        if status == StatusPreview.CRITICO:
            return f"⚠️ SALDO FICARÁ NEGATIVO ({novo_saldo})! Verifique a quantidade ou tipo de movimentação."

        if status == StatusPreview.ATENCAO:
            return f"⚠️ Saldo ficará abaixo do mínimo recomendado ({ConfigPreview.SALDO_MINIMO_ATENCAO}). Considere repor o estoque."

        if status == StatusPreview.ITEM_NOVO and novo_saldo < 0:
            return "⚠️ Você está criando um item novo com saldo NEGATIVO. Verifique se o tipo de movimentação está correto."

        return None

    def gerar_recomendacao(
        self,
        status: StatusPreview,
        tipo_movimentacao: TipoMovimentacao,
        novo_saldo: float
    ) -> str:
        """Gera recomendação de ação"""

        if status == StatusPreview.CRITICO:
            if tipo_movimentacao == TipoMovimentacao.SAIDA:
                return "💡 Verifique se a quantidade está correta ou se deveria ser uma ENTRADA."
            else:
                return "💡 Verifique se o tipo de movimentação está correto."

        if status == StatusPreview.ATENCAO:
            return "💡 Considere fazer reposição de estoque em breve."

        if status == StatusPreview.ITEM_NOVO:
            if novo_saldo >= 0:
                return "✅ Confirme se os dados estão corretos para criar o novo item."
            else:
                return "⚠️ RECOMENDAÇÃO: Altere para ENTRADA se você está adicionando estoque."

        return "✅ Tudo certo! Pode confirmar a movimentação."

    def calcular_preview(
        self,
        item: str,
        tipo_movimentacao: str,
        quantidade: float,
        grupo: Optional[str] = None
    ) -> PreviewSaldo:
        """
        Calcula preview completo de uma movimentação

        Args:
            item: Nome do item
            tipo_movimentacao: ENTRADA ou SAIDA
            quantidade: Quantidade a movimentar
            grupo: Grupo do item (opcional)

        Returns:
            PreviewSaldo com todos os dados
        """
        # Normaliza tipo
        tipo_enum = self.normalizar_tipo_movimentacao(tipo_movimentacao)

        # Busca dados atuais do item
        dados_item = indice_otimizado.buscar_item(item)

        if dados_item:
            saldo_atual = float(dados_item.get('saldo', 0))
            grupo_item = dados_item.get('grupo', grupo or '')
            item_existe = True
        else:
            saldo_atual = 0.0
            grupo_item = grupo or ''
            item_existe = False

        # Calcula novo saldo
        novo_saldo = self.calcular_novo_saldo(saldo_atual, tipo_enum, quantidade)
        diferenca = novo_saldo - saldo_atual

        # Determina status
        status = self.determinar_status(saldo_atual, novo_saldo, tipo_enum, item_existe)

        # Gera mensagens
        mensagem = self.gerar_mensagem(status, item, saldo_atual, novo_saldo, tipo_enum)
        alerta = self.gerar_alerta(status, novo_saldo)
        recomendacao = self.gerar_recomendacao(status, tipo_enum, novo_saldo)

        # Determina se pode confirmar
        if status == StatusPreview.CRITICO and not ConfigPreview.PERMITIR_SALDO_NEGATIVO:
            pode_confirmar = False
        else:
            pode_confirmar = True

        # Cria objeto preview
        preview = PreviewSaldo(
            item=item,
            grupo=grupo_item,
            tipo_movimentacao=tipo_enum.value,
            quantidade=quantidade,
            saldo_atual=saldo_atual,
            novo_saldo=novo_saldo,
            diferenca=diferenca,
            status=status,
            mensagem=mensagem,
            alerta=alerta,
            recomendacao=recomendacao,
            pode_confirmar=pode_confirmar,
            timestamp=datetime.now().isoformat()
        )

        return preview

    def calcular_preview_lote(
        self,
        movimentacoes: List[Dict[str, Any]]
    ) -> List[PreviewSaldo]:
        """
        Calcula preview para múltiplas movimentações

        Args:
            movimentacoes: Lista de dicts com {item, tipo_movimentacao, quantidade, grupo?}

        Returns:
            Lista de PreviewSaldo
        """
        previews = []

        for mov in movimentacoes:
            try:
                preview = self.calcular_preview(
                    item=mov['item'],
                    tipo_movimentacao=mov['tipo_movimentacao'],
                    quantidade=mov['quantidade'],
                    grupo=mov.get('grupo')
                )
                previews.append(preview)
            except Exception as e:
                logger.error(f"Erro ao calcular preview de {mov.get('item')}: {e}")
                continue

        return previews

    def validar_movimentacao(
        self,
        item: str,
        tipo_movimentacao: str,
        quantidade: float
    ) -> Dict[str, Any]:
        """
        Valida se movimentação pode ser executada

        Args:
            item: Nome do item
            tipo_movimentacao: ENTRADA ou SAIDA
            quantidade: Quantidade

        Returns:
            Dict com {valido: bool, motivo: str?, preview: PreviewSaldo}
        """
        preview = self.calcular_preview(item, tipo_movimentacao, quantidade)

        if not preview.pode_confirmar:
            return {
                'valido': False,
                'motivo': preview.alerta or 'Movimentação não permitida',
                'preview': preview.to_dict()
            }

        return {
            'valido': True,
            'motivo': None,
            'preview': preview.to_dict()
        }


# ========================================
# SINGLETON GLOBAL
# ========================================
gerenciador_preview = GerenciadorPreview()


# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def obter_preview_rapido(item: str, tipo: str, quantidade: float) -> Dict[str, Any]:
    """Atalho para obter preview rapidamente"""
    preview = gerenciador_preview.calcular_preview(item, tipo, quantidade)
    return preview.to_dict()


def validar_antes_inserir(item: str, tipo: str, quantidade: float) -> bool:
    """
    Valida movimentação antes de inserir

    Returns:
        True se pode inserir, False caso contrário
    """
    resultado = gerenciador_preview.validar_movimentacao(item, tipo, quantidade)
    return resultado['valido']


if __name__ == '__main__':
    # Exemplos de uso
    print("🧪 Testando GerenciadorPreview...")

    # Teste 1: Saída normal
    print("\n1. Preview de SAÍDA (normal):")
    preview = gerenciador_preview.calcular_preview('TESTE', 'SAIDA', 50)
    print(f"   Mensagem: {preview.mensagem}")
    print(f"   Pode confirmar: {preview.pode_confirmar}")

    # Teste 2: Entrada
    print("\n2. Preview de ENTRADA:")
    preview = gerenciador_preview.calcular_preview('TESTE', 'ENTRADA', 100)
    print(f"   Mensagem: {preview.mensagem}")
    print(f"   Novo saldo: {preview.novo_saldo}")

    # Teste 3: Validação
    print("\n3. Validando movimentação:")
    valido = validar_antes_inserir('TESTE', 'SAIDA', 999999)
    print(f"   Válido: {valido}")

    print("\n✅ Testes concluídos!")
