#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de IA Avançada - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Sistema inteligente com:
- 🤖 Validação avançada de movimentações
- 🔮 Predição de saldo futuro
- 📊 Análise de padrões e anomalias
- 💡 Recomendações automáticas
- 🎯 Sistema de scoring/confiança

Benefícios:
- Detecta erros antes de acontecer
- Prevê quando item vai zerar
- Identifica padrões anormais
- Sugere ações proativas
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# ENUMS E CLASSES
# ========================================

class NivelConfianca(Enum):
    """Nível de confiança da IA"""
    MUITO_ALTA = "muito_alta"  # > 90%
    ALTA = "alta"              # 70-90%
    MEDIA = "media"            # 50-70%
    BAIXA = "baixa"            # < 50%


class TipoAnomalia(Enum):
    """Tipos de anomalia detectados"""
    QUANTIDADE_ANORMAL = "quantidade_anormal"
    FREQUENCIA_ANORMAL = "frequencia_anormal"
    HORARIO_INCOMUM = "horario_incomum"
    SALDO_INESPERADO = "saldo_inesperado"
    PADRAO_DIFERENTE = "padrao_diferente"


class TipoRecomendacao(Enum):
    """Tipos de recomendação"""
    REPOR_ESTOQUE = "repor_estoque"
    VERIFICAR_QUANTIDADE = "verificar_quantidade"
    AJUSTAR_TIPO = "ajustar_tipo"
    CONFERIR_SALDO = "conferir_saldo"
    ATENCAO_PADRAO = "atencao_padrao"


@dataclass
class ResultadoValidacao:
    """Resultado da validação por IA"""
    valido: bool
    confianca: float  # 0-100
    nivel_confianca: NivelConfianca
    problemas: List[str]
    avisos: List[str]
    sugestoes: List[str]
    score: float  # 0-100 (quanto maior, melhor)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valido': self.valido,
            'confianca': self.confianca,
            'nivel_confianca': self.nivel_confianca.value,
            'problemas': self.problemas,
            'avisos': self.avisos,
            'sugestoes': self.sugestoes,
            'score': self.score,
            'timestamp': self.timestamp
        }


@dataclass
class PredicaoSaldo:
    """Predição de saldo futuro"""
    item: str
    saldo_atual: float
    saldo_previsto: float
    dias_para_zerar: Optional[int]
    confianca: float
    tendencia: str  # crescente, decrescente, estavel
    media_diaria: float
    recomendacao: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'item': self.item,
            'saldo_atual': self.saldo_atual,
            'saldo_previsto': self.saldo_previsto,
            'dias_para_zerar': self.dias_para_zerar,
            'confianca': self.confianca,
            'tendencia': self.tendencia,
            'media_diaria': self.media_diaria,
            'recomendacao': self.recomendacao,
            'timestamp': self.timestamp
        }


@dataclass
class AnomaliaDetectada:
    """Anomalia detectada pela IA"""
    tipo: TipoAnomalia
    gravidade: str  # baixa, media, alta
    descricao: str
    valor_atual: Any
    valor_esperado: Any
    confianca: float
    recomendacao: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tipo': self.tipo.value,
            'gravidade': self.gravidade,
            'descricao': self.descricao,
            'valor_atual': self.valor_atual,
            'valor_esperado': self.valor_esperado,
            'confianca': self.confianca,
            'recomendacao': self.recomendacao
        }


@dataclass
class Recomendacao:
    """Recomendação gerada pela IA"""
    tipo: TipoRecomendacao
    titulo: str
    descricao: str
    prioridade: int  # 1-5 (5 = urgente)
    item: Optional[str]
    acao_sugerida: str
    impacto_estimado: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tipo': self.tipo.value,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'prioridade': self.prioridade,
            'item': self.item,
            'acao_sugerida': self.acao_sugerida,
            'impacto_estimado': self.impacto_estimado
        }


# ========================================
# CONFIGURAÇÕES
# ========================================

class ConfigIA:
    """Configurações do sistema de IA"""

    # Validação
    SCORE_MINIMO_VALIDO = 60  # Score mínimo para considerar válido
    CONFIANCA_MINIMA = 50     # Confiança mínima %

    # Detecção de anomalias
    DESVIO_PADRAO_MAX = 2.5   # Número de desvios padrão para considerar anormal
    QUANTIDADE_MIN_HISTORICO = 5  # Mínimo de registros para análise

    # Predição
    DIAS_HISTORICO = 30       # Dias de histórico para predição
    DIAS_PREDICAO = 7         # Dias no futuro para prever

    # Recomendações
    DIAS_CRITICO_ESTOQUE = 3  # Dias para zerar = crítico
    DIAS_ATENCAO_ESTOQUE = 7  # Dias para zerar = atenção


# ========================================
# CLASSE PRINCIPAL
# ========================================

class SistemaIA:
    """
    Sistema de IA Avançada para gestão de estoque

    Uso:
        ia = SistemaIA()

        # Valida movimentação
        validacao = ia.validar_movimentacao(
            item='AMARELO 1234',
            tipo='SAIDA',
            quantidade=100,
            saldo_atual=250
        )

        # Prediz saldo futuro
        predicao = ia.prever_saldo_futuro(
            item='AMARELO 1234',
            dias=7
        )

        # Detecta anomalias
        anomalias = ia.detectar_anomalias(
            item='AMARELO 1234',
            quantidade=1000  # Muito acima do normal
        )

        # Gera recomendações
        recomendacoes = ia.gerar_recomendacoes()
    """

    def __init__(self):
        """Inicializa o sistema de IA"""
        self._cache_analises = {}  # Cache de análises
        logger.info("✅ SistemaIA inicializado")

    def validar_movimentacao(
        self,
        item: str,
        tipo_movimentacao: str,
        quantidade: float,
        saldo_atual: float,
        grupo: Optional[str] = None,
        historico: Optional[List[Dict]] = None
    ) -> ResultadoValidacao:
        """
        Valida movimentação com IA

        Args:
            item: Nome do item
            tipo_movimentacao: ENTRADA ou SAIDA
            quantidade: Quantidade
            saldo_atual: Saldo atual
            grupo: Grupo do item
            historico: Histórico do item (opcional)

        Returns:
            ResultadoValidacao
        """
        problemas = []
        avisos = []
        sugestoes = []
        score = 100.0
        confianca = 100.0

        tipo_upper = tipo_movimentacao.upper()

        # ========================================
        # REGRA 1: Validação básica de quantidade
        # ========================================
        if quantidade <= 0:
            problemas.append("❌ Quantidade deve ser maior que zero")
            score -= 50
            confianca = 100

        if quantidade > 10000:
            avisos.append("⚠️ Quantidade muito alta (>10000). Verifique se está correto.")
            sugestoes.append("💡 Confirme se não é um erro de digitação (ex: 100 ao invés de 10000)")
            score -= 10
            confianca -= 15

        # ========================================
        # REGRA 2: Validação de saldo para SAÍDA
        # ========================================
        if 'SAIDA' in tipo_upper or 'SAÍDA' in tipo_upper:
            if quantidade > saldo_atual:
                problemas.append(f"❌ SAÍDA de {quantidade} com saldo de apenas {saldo_atual}")
                sugestoes.append("💡 Verifique se deveria ser ENTRADA ao invés de SAÍDA")
                score -= 30
                confianca = 95

            if saldo_atual - quantidade < 0:
                problemas.append("❌ Saldo ficará NEGATIVO")
                score -= 20

        # ========================================
        # REGRA 3: Análise de histórico (se disponível)
        # ========================================
        if historico and len(historico) >= ConfigIA.QUANTIDADE_MIN_HISTORICO:
            # Calcula média e desvio padrão
            quantidades = [abs(float(h.get('quantidade', 0))) for h in historico]

            try:
                media = statistics.mean(quantidades)
                desvio = statistics.stdev(quantidades) if len(quantidades) > 1 else 0

                # Detecta quantidade anormal
                if desvio > 0:
                    z_score = abs(quantidade - media) / desvio

                    if z_score > ConfigIA.DESVIO_PADRAO_MAX:
                        avisos.append(
                            f"⚠️ Quantidade {quantidade:.1f} está muito acima da média ({media:.1f})"
                        )
                        sugestoes.append(
                            f"💡 Normalmente você movimenta ~{media:.0f}. Confirme se {quantidade:.0f} está correto."
                        )
                        score -= 15
                        confianca -= 20

            except Exception as e:
                logger.debug(f"Erro ao calcular estatísticas: {e}")

            # Análise de padrão de tipo
            tipos_historico = [h.get('tipo_movimentacao', '').upper() for h in historico[-5:]]
            entradas = sum(1 for t in tipos_historico if 'ENTRADA' in t)
            saidas = sum(1 for t in tipos_historico if 'SAIDA' in t or 'SAÍDA' in t)

            if 'ENTRADA' in tipo_upper and saidas > entradas * 2:
                avisos.append("ℹ️ Item tem mais SAÍDAS que ENTRADAS recentemente")
                sugestoes.append("💡 Verifique se não esqueceu de registrar entradas anteriores")
                confianca -= 10

        # ========================================
        # REGRA 4: Validação de padrões comuns
        # ========================================

        # Entrada com saldo já alto
        if 'ENTRADA' in tipo_upper and saldo_atual > 1000:
            avisos.append(f"ℹ️ Item já tem saldo alto ({saldo_atual}). Entrada necessária?")
            confianca -= 5

        # Saída pequena com saldo alto
        if 'SAIDA' in tipo_upper and quantidade < 10 and saldo_atual > 500:
            # OK, saída pequena é normal
            pass

        # ========================================
        # REGRA 5: Validação de horário (se aplicável)
        # ========================================
        hora_atual = datetime.now().hour

        if hora_atual < 6 or hora_atual > 22:
            avisos.append(f"⏰ Movimentação em horário incomum ({hora_atual:02d}h)")
            sugestoes.append("💡 Confirme se a data/hora está correta")
            confianca -= 10
            score -= 5

        # ========================================
        # CÁLCULO FINAL
        # ========================================

        # Garante limites
        score = max(0, min(100, score))
        confianca = max(0, min(100, confianca))

        # Determina nível de confiança
        if confianca >= 90:
            nivel = NivelConfianca.MUITO_ALTA
        elif confianca >= 70:
            nivel = NivelConfianca.ALTA
        elif confianca >= 50:
            nivel = NivelConfianca.MEDIA
        else:
            nivel = NivelConfianca.BAIXA

        # Valido se score >= mínimo e sem problemas críticos
        valido = score >= ConfigIA.SCORE_MINIMO_VALIDO and len(problemas) == 0

        if not valido and not problemas:
            problemas.append(f"⚠️ Score de validação baixo ({score:.0f}/100)")

        return ResultadoValidacao(
            valido=valido,
            confianca=confianca,
            nivel_confianca=nivel,
            problemas=problemas,
            avisos=avisos,
            sugestoes=sugestoes,
            score=score
        )

    def prever_saldo_futuro(
        self,
        item: str,
        dias: int = 7,
        saldo_atual: Optional[float] = None,
        historico: Optional[List[Dict]] = None
    ) -> PredicaoSaldo:
        """
        Prevê saldo futuro baseado em histórico

        Args:
            item: Nome do item
            dias: Dias no futuro
            saldo_atual: Saldo atual (se None, busca)
            historico: Histórico do item

        Returns:
            PredicaoSaldo
        """
        # Busca saldo atual se não fornecido
        if saldo_atual is None:
            try:
                from indice_otimizado import indice_otimizado
                dados = indice_otimizado.buscar_item(item)
                saldo_atual = float(dados.get('saldo', 0)) if dados else 0.0
            except:
                saldo_atual = 0.0

        # Busca histórico se não fornecido
        if historico is None:
            try:
                from historico_otimizado import gerenciador_historico
                registros = gerenciador_historico.buscar_por_item(item, limite=30)
                historico = [r.to_dict() for r in registros]
            except:
                historico = []

        # Calcula média diária
        media_diaria = 0.0
        confianca = 50.0
        tendencia = "estavel"

        if historico and len(historico) >= 3:
            try:
                # Filtra saídas dos últimos N dias
                saidas_recentes = [
                    float(h['quantidade'])
                    for h in historico[:10]
                    if 'SAIDA' in h.get('tipo_movimentacao', '').upper()
                ]

                if saidas_recentes:
                    media_diaria = statistics.mean(saidas_recentes)
                    confianca = min(90, 50 + len(saidas_recentes) * 5)

                    # Determina tendência
                    if len(saidas_recentes) >= 5:
                        primeira_metade = statistics.mean(saidas_recentes[:len(saidas_recentes)//2])
                        segunda_metade = statistics.mean(saidas_recentes[len(saidas_recentes)//2:])

                        if segunda_metade > primeira_metade * 1.2:
                            tendencia = "crescente"
                        elif segunda_metade < primeira_metade * 0.8:
                            tendencia = "decrescente"

            except Exception as e:
                logger.debug(f"Erro ao calcular média: {e}")

        # Prevê saldo futuro
        saldo_previsto = saldo_atual - (media_diaria * dias)

        # Calcula dias para zerar
        dias_para_zerar = None
        if media_diaria > 0 and saldo_atual > 0:
            dias_para_zerar = int(saldo_atual / media_diaria)

        # Gera recomendação
        recomendacao = self._gerar_recomendacao_predicao(
            saldo_atual, saldo_previsto, dias_para_zerar, tendencia
        )

        return PredicaoSaldo(
            item=item,
            saldo_atual=saldo_atual,
            saldo_previsto=saldo_previsto,
            dias_para_zerar=dias_para_zerar,
            confianca=confianca,
            tendencia=tendencia,
            media_diaria=media_diaria,
            recomendacao=recomendacao
        )

    def _gerar_recomendacao_predicao(
        self,
        saldo_atual: float,
        saldo_previsto: float,
        dias_para_zerar: Optional[int],
        tendencia: str
    ) -> str:
        """Gera recomendação baseada na predição"""

        if dias_para_zerar is not None:
            if dias_para_zerar <= ConfigIA.DIAS_CRITICO_ESTOQUE:
                return f"🔴 CRÍTICO: Estoque zerará em ~{dias_para_zerar} dias! REPOR URGENTE!"
            elif dias_para_zerar <= ConfigIA.DIAS_ATENCAO_ESTOQUE:
                return f"⚠️ ATENÇÃO: Estoque zerará em ~{dias_para_zerar} dias. Programar reposição."

        if saldo_previsto < 0:
            return "🔴 Saldo previsto NEGATIVO. Repor estoque antes disso!"

        if saldo_previsto < saldo_atual * 0.2:
            return "⚠️ Saldo cairá para menos de 20%. Considere repor."

        if tendencia == "crescente":
            return "📈 Consumo em crescimento. Monitore de perto."

        if tendencia == "decrescente":
            return "📉 Consumo em queda. Estoque durará mais."

        return "✅ Saldo previsto OK para os próximos dias."

    def detectar_anomalias(
        self,
        item: str,
        quantidade: float,
        tipo_movimentacao: str,
        historico: Optional[List[Dict]] = None
    ) -> List[AnomaliaDetectada]:
        """
        Detecta anomalias na movimentação

        Args:
            item: Nome do item
            quantidade: Quantidade
            tipo_movimentacao: ENTRADA/SAIDA
            historico: Histórico do item

        Returns:
            Lista de AnomaliaDetectada
        """
        anomalias = []

        if not historico or len(historico) < ConfigIA.QUANTIDADE_MIN_HISTORICO:
            return anomalias

        try:
            # Extrai quantidades do histórico
            quantidades = [abs(float(h.get('quantidade', 0))) for h in historico]

            if not quantidades:
                return anomalias

            media = statistics.mean(quantidades)
            desvio = statistics.stdev(quantidades) if len(quantidades) > 1 else 0

            # ANOMALIA 1: Quantidade muito acima da média
            if desvio > 0:
                z_score = abs(quantidade - media) / desvio

                if z_score > ConfigIA.DESVIO_PADRAO_MAX:
                    anomalias.append(AnomaliaDetectada(
                        tipo=TipoAnomalia.QUANTIDADE_ANORMAL,
                        gravidade="alta" if z_score > 4 else "media",
                        descricao=f"Quantidade {quantidade:.0f} está {z_score:.1f} desvios padrão acima da média",
                        valor_atual=quantidade,
                        valor_esperado=media,
                        confianca=min(95, 70 + z_score * 5),
                        recomendacao="Verifique se a quantidade está correta antes de confirmar"
                    ))

            # ANOMALIA 2: Frequência anormal (muitas movimentações seguidas)
            if len(historico) >= 3:
                # Verifica se as últimas 3 foram do mesmo tipo
                ultimos_tipos = [h.get('tipo_movimentacao', '').upper() for h in historico[:3]]
                if all('SAIDA' in t or 'SAÍDA' in t for t in ultimos_tipos):
                    if 'SAIDA' in tipo_movimentacao.upper():
                        anomalias.append(AnomaliaDetectada(
                            tipo=TipoAnomalia.FREQUENCIA_ANORMAL,
                            gravidade="baixa",
                            descricao="4 SAÍDAS seguidas sem ENTRADA",
                            valor_atual="4 saídas",
                            valor_esperado="Alternância entrada/saída",
                            confianca=70,
                            recomendacao="Verifique se não há entradas não registradas"
                        ))

        except Exception as e:
            logger.debug(f"Erro ao detectar anomalias: {e}")

        return anomalias

    def gerar_recomendacoes(
        self,
        limite: int = 10
    ) -> List[Recomendacao]:
        """
        Gera recomendações automáticas

        Args:
            limite: Número máximo de recomendações

        Returns:
            Lista de Recomendacao ordenada por prioridade
        """
        recomendacoes = []

        try:
            # Busca itens críticos (alertas FASE 2)
            from alertas_automaticos import gerenciador_alertas

            alertas_criticos = gerenciador_alertas.obter_alertas_criticos()

            for alerta_dict in alertas_criticos[:5]:
                recomendacoes.append(Recomendacao(
                    tipo=TipoRecomendacao.REPOR_ESTOQUE,
                    titulo=f"⚠️ Repor estoque: {alerta_dict.get('item', 'N/A')}",
                    descricao=alerta_dict.get('mensagem', ''),
                    prioridade=5,
                    item=alerta_dict.get('item'),
                    acao_sugerida="Realizar entrada de estoque",
                    impacto_estimado="Evita parada de produção"
                ))

        except Exception as e:
            logger.debug(f"Erro ao gerar recomendações: {e}")

        # Ordena por prioridade
        recomendacoes.sort(key=lambda r: r.prioridade, reverse=True)

        return recomendacoes[:limite]

    def analisar_item_completo(
        self,
        item: str
    ) -> Dict[str, Any]:
        """
        Análise completa de um item com IA

        Args:
            item: Nome do item

        Returns:
            Dict com análise completa
        """
        try:
            from indice_otimizado import indice_otimizado
            from historico_otimizado import gerenciador_historico
            from alertas_automaticos import gerenciador_alertas

            # Dados atuais
            dados = indice_otimizado.buscar_item(item)
            saldo_atual = float(dados.get('saldo', 0)) if dados else 0.0

            # Histórico
            registros = gerenciador_historico.buscar_por_item(item, limite=30)
            historico = [r.to_dict() for r in registros]

            # Predição
            predicao = self.prever_saldo_futuro(item, dias=7, saldo_atual=saldo_atual, historico=historico)

            # Alerta
            alerta = gerenciador_alertas.classificar_item(item)

            return {
                'item': item,
                'saldo_atual': saldo_atual,
                'predicao': predicao.to_dict(),
                'alerta': alerta.to_dict() if alerta else None,
                'total_movimentacoes': len(historico),
                'analise_ia': {
                    'status': '🔴 CRÍTICO' if predicao.dias_para_zerar and predicao.dias_para_zerar <= 3
                              else '⚠️ ATENÇÃO' if predicao.dias_para_zerar and predicao.dias_para_zerar <= 7
                              else '✅ OK',
                    'recomendacao_principal': predicao.recomendacao
                }
            }

        except Exception as e:
            logger.error(f"Erro na análise completa: {e}")
            return {
                'item': item,
                'error': str(e)
            }


# ========================================
# SINGLETON GLOBAL
# ========================================
sistema_ia = SistemaIA()


# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def validar_com_ia(item: str, tipo: str, quantidade: float, **kwargs) -> Dict[str, Any]:
    """Atalho para validar com IA"""
    resultado = sistema_ia.validar_movimentacao(item, tipo, quantidade, **kwargs)
    return resultado.to_dict()


def prever_saldo(item: str, dias: int = 7) -> Dict[str, Any]:
    """Atalho para prever saldo"""
    predicao = sistema_ia.prever_saldo_futuro(item, dias)
    return predicao.to_dict()


if __name__ == '__main__':
    # Testes rápidos
    print("🧪 Testando SistemaIA...")

    # Teste 1: Validação
    print("\n1. Validação de movimentação:")
    validacao = sistema_ia.validar_movimentacao(
        item='TESTE',
        tipo_movimentacao='SAIDA',
        quantidade=100,
        saldo_atual=250
    )
    print(f"   Válido: {validacao.valido}")
    print(f"   Score: {validacao.score:.0f}/100")
    print(f"   Confiança: {validacao.confianca:.0f}%")

    # Teste 2: Predição
    print("\n2. Predição de saldo:")
    predicao = sistema_ia.prever_saldo_futuro(
        item='TESTE',
        dias=7,
        saldo_atual=100
    )
    print(f"   Saldo previsto: {predicao.saldo_previsto:.1f}")
    print(f"   Tendência: {predicao.tendencia}")

    print("\n✅ Testes concluídos!")
