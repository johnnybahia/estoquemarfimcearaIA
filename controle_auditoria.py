"""
Controle de Auditoria Obrigatória — Marfim Estoque Ceará
=========================================================
Força o usuário a conferir fisicamente o estoque a cada 20 dias.

Regra de negócio:
  - Toda conferência/correção de estoque deve ter "ATUALIZAÇÃO" no campo OBS
  - Se a última ATUALIZAÇÃO tiver mais de 20 dias → bloqueia entradas e saídas
  - Avisos progressivos começam em 15 dias

Níveis de alerta:
  ✅ VERDE    (0–14 dias)  → operação normal
  ⚠️  AMARELO  (15–17 dias) → aviso antecipado
  🚨 LARANJA  (18–19 dias) → urgente, requer ação imediata
  ⛔ VERMELHO (20+ dias)   → BLOQUEADO — sem movimento até conferir

Uso:
  from controle_auditoria import get_gerenciador_auditoria

  gerenciador = get_gerenciador_auditoria()
  pode, motivo = gerenciador.pode_movimentar()
  if not pode:
      return jsonify({"bloqueado": True, "motivo": motivo})
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────
PALAVRA_CHAVE         = "ATUALIZAÇÃO"
PALAVRA_CHAVE_SIMPLES = "ATUALIZACAO"   # sem acento (tolerância)
ABA_ESTOQUE           = "ESTOQUE"
DIAS_LIMITE           = 20              # dias → bloqueio total
DIAS_AVISO_AMARELO    = 15             # dias → aviso antecipado
DIAS_AVISO_LARANJA    = 18             # dias → urgente
CACHE_TTL_SEGUNDOS    = 300            # 5 min de cache


# ──────────────────────────────────────────────────────────────
# Enums e dataclasses
# ──────────────────────────────────────────────────────────────
class NivelAuditoria(Enum):
    VERDE    = "verde"
    AMARELO  = "amarelo"
    LARANJA  = "laranja"
    VERMELHO = "vermelho"


@dataclass
class RegistroAuditoria:
    """Um registro de ATUALIZAÇÃO encontrado na planilha."""
    data: datetime
    obs: str
    item: str
    grupo: str
    usuario: str
    linha: int


@dataclass
class StatusAuditoria:
    """Estado atual do controle de auditoria."""
    nivel: NivelAuditoria
    dias_desde_ultima: int
    ultima_auditoria: Optional[datetime]
    pode_movimentar: bool
    mensagem: str                          # curta (para badge)
    mensagem_detalhada: str                # longa (para modal/alerta)
    dias_para_bloqueio: int                # negativo = já bloqueado
    proxima_auditoria_limite: Optional[datetime]
    cor_hex: str
    emoji: str
    ts_verificacao: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nivel": self.nivel.value,
            "dias_desde_ultima": self.dias_desde_ultima,
            "ultima_auditoria": (
                self.ultima_auditoria.strftime('%d/%m/%Y %H:%M')
                if self.ultima_auditoria else None
            ),
            "pode_movimentar": self.pode_movimentar,
            "mensagem": self.mensagem,
            "mensagem_detalhada": self.mensagem_detalhada,
            "dias_para_bloqueio": self.dias_para_bloqueio,
            "proxima_auditoria_limite": (
                self.proxima_auditoria_limite.strftime('%d/%m/%Y')
                if self.proxima_auditoria_limite else None
            ),
            "cor_hex": self.cor_hex,
            "emoji": self.emoji,
            "ts_verificacao": self.ts_verificacao,
            "dias_limite_configurado": DIAS_LIMITE,
        }


# ──────────────────────────────────────────────────────────────
# Gerenciador principal
# ──────────────────────────────────────────────────────────────
class GerenciadorAuditoria:
    """
    Motor do controle de auditoria obrigatória.

    - Busca a última ocorrência de 'ATUALIZAÇÃO' na coluna OBS da aba ESTOQUE
    - Calcula nível de alerta com base nos dias desde essa data
    - Bloqueia movimentações quando supera DIAS_LIMITE
    - Cache interno de 5 minutos para evitar chamadas excessivas ao Sheets
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._cache_status: Optional[StatusAuditoria] = None
        self._cache_timestamp: Optional[datetime] = None

    # ── helpers ────────────────────────────────────────────────

    def _cache_valido(self) -> bool:
        if not self._cache_status or not self._cache_timestamp:
            return False
        return (datetime.now() - self._cache_timestamp).total_seconds() < CACHE_TTL_SEGUNDOS

    @staticmethod
    def _obs_e_auditoria(obs: str) -> bool:
        """Verifica se o texto de OBS contém a palavra-chave de auditoria."""
        obs_upper = obs.upper().strip()
        return (
            PALAVRA_CHAVE.upper() in obs_upper or
            PALAVRA_CHAVE_SIMPLES.upper() in obs_upper
        )

    @staticmethod
    def _parse_data(texto: str) -> Optional[datetime]:
        """Tenta converter string de data em objeto datetime."""
        texto = texto.strip()
        formatos = [
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(texto[:len(fmt)], fmt)
            except ValueError:
                continue
        return None

    def _conectar_e_carregar(self):
        """Retorna (header, rows) da aba ESTOQUE."""
        try:
            from app_final import conectar_google
            ss = conectar_google()
            aba = ss.worksheet(ABA_ESTOQUE)
            todos = aba.get_all_values()
            if not todos or len(todos) < 2:
                return None, []
            return todos[0], todos[1:]
        except Exception as e:
            logger.error(f"[Auditoria] Erro ao conectar ao Sheets: {e}")
            return None, []

    # ── busca principal ────────────────────────────────────────

    def buscar_ultima_auditoria(self) -> Optional[RegistroAuditoria]:
        """
        Varre a aba ESTOQUE e retorna o registro mais recente
        que contém 'ATUALIZAÇÃO' (ou 'ATUALIZACAO') na coluna OBS.
        """
        header, rows = self._conectar_e_carregar()
        if header is None:
            return None

        header_upper = [c.upper().strip() for c in header]

        def _idx(candidatos: List[str]) -> Optional[int]:
            for c in candidatos:
                try:
                    return header_upper.index(c)
                except ValueError:
                    pass
            return None

        col_obs    = _idx(['OBS', 'OBSERVAÇÃO', 'OBSERVACAO', 'OBSERVACOES', 'OBS.'])
        col_data   = _idx(['DATA'])          # coluna D — data do movimento
        col_item   = _idx(['ITEM'])
        col_grupo  = _idx(['GRUPO'])
        col_altpor = _idx(['ALT.POR', 'ALTPOR', 'ALT POR', 'ALTERADO POR'])

        if col_obs is None or col_data is None:
            logger.warning("[Auditoria] Colunas OBS ou DATA não encontradas no cabeçalho.")
            return None

        ultima: Optional[RegistroAuditoria] = None

        for linha_num, row in enumerate(rows, start=2):
            if len(row) <= col_obs or len(row) <= col_data:
                continue

            obs = row[col_obs]
            if not self._obs_e_auditoria(obs):
                continue

            data = self._parse_data(row[col_data])
            if data is None:
                continue

            registro = RegistroAuditoria(
                data=data,
                obs=obs,
                item=row[col_item]   if col_item   and col_item   < len(row) else "",
                grupo=row[col_grupo] if col_grupo  and col_grupo  < len(row) else "",
                usuario=row[col_altpor] if col_altpor and col_altpor < len(row) else "Sistema",
                linha=linha_num,
            )
            if ultima is None or data > ultima.data:
                ultima = registro

        return ultima

    def obter_historico(self, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna os últimos `limite` registros de ATUALIZAÇÃO,
        ordenados do mais recente para o mais antigo.
        """
        header, rows = self._conectar_e_carregar()
        if header is None:
            return []

        header_upper = [c.upper().strip() for c in header]

        def _idx(candidatos):
            for c in candidatos:
                try:
                    return header_upper.index(c)
                except ValueError:
                    pass
            return None

        col_obs    = _idx(['OBS', 'OBSERVAÇÃO', 'OBSERVACAO', 'OBS.'])
        col_data   = _idx(['DATA'])
        col_item   = _idx(['ITEM'])
        col_grupo  = _idx(['GRUPO'])
        col_altpor = _idx(['ALT.POR', 'ALTPOR', 'ALT POR'])

        auditorias = []
        for linha_num, row in enumerate(rows, start=2):
            obs = row[col_obs] if col_obs is not None and col_obs < len(row) else ""
            if not self._obs_e_auditoria(obs):
                continue

            data_str = row[col_data] if col_data is not None and col_data < len(row) else ""
            data = self._parse_data(data_str)
            if data is None:
                continue

            auditorias.append({
                "data":         data.strftime('%d/%m/%Y %H:%M'),
                "data_iso":     data.isoformat(),
                "item":         row[col_item]   if col_item   and col_item   < len(row) else "",
                "grupo":        row[col_grupo]  if col_grupo  and col_grupo  < len(row) else "",
                "obs":          obs,
                "usuario":      row[col_altpor] if col_altpor and col_altpor < len(row) else "",
                "linha":        linha_num,
                "dias_atras":   (datetime.now() - data).days,
            })

        auditorias.sort(key=lambda x: x["data_iso"], reverse=True)
        return auditorias[:limite]

    # ── cálculo do status ──────────────────────────────────────

    def _calcular_status(self, ultima: Optional[RegistroAuditoria]) -> StatusAuditoria:
        agora = datetime.now()

        # ── sem nenhum registro histórico ─────────────────────
        if ultima is None:
            return StatusAuditoria(
                nivel=NivelAuditoria.VERMELHO,
                dias_desde_ultima=9999,
                ultima_auditoria=None,
                pode_movimentar=False,
                mensagem="⛔ Nenhuma conferência registrada",
                mensagem_detalhada=(
                    "Nenhum registro de ATUALIZAÇÃO foi encontrado no histórico. "
                    "Para liberar movimentações, realize uma conferência física do "
                    "estoque e insira a palavra ATUALIZAÇÃO no campo OBS de qualquer lançamento."
                ),
                dias_para_bloqueio=-9999,
                proxima_auditoria_limite=None,
                cor_hex="#dc3545",
                emoji="⛔",
            )

        dias = (agora - ultima.data).days
        limite_dt = ultima.data + timedelta(days=DIAS_LIMITE)
        dias_para_bloqueio = DIAS_LIMITE - dias
        data_fmt = ultima.data.strftime('%d/%m/%Y')
        limite_fmt = limite_dt.strftime('%d/%m/%Y')

        # ── VERMELHO: bloqueado ────────────────────────────────
        if dias >= DIAS_LIMITE:
            return StatusAuditoria(
                nivel=NivelAuditoria.VERMELHO,
                dias_desde_ultima=dias,
                ultima_auditoria=ultima.data,
                pode_movimentar=False,
                mensagem=f"⛔ BLOQUEADO — {dias} dias sem conferência",
                mensagem_detalhada=(
                    f"A última conferência registrada foi em {data_fmt} ({dias} dias atrás). "
                    f"O prazo máximo é de {DIAS_LIMITE} dias. "
                    "Para desbloquear o estoque:\n"
                    "1. Realize a conferência física dos itens\n"
                    "2. Corrija as divergências encontradas\n"
                    "3. Registre qualquer movimentação com a palavra ATUALIZAÇÃO no campo OBS"
                ),
                dias_para_bloqueio=dias_para_bloqueio,
                proxima_auditoria_limite=limite_dt,
                cor_hex="#dc3545",
                emoji="⛔",
            )

        # ── LARANJA: urgente ──────────────────────────────────
        if dias >= DIAS_AVISO_LARANJA:
            return StatusAuditoria(
                nivel=NivelAuditoria.LARANJA,
                dias_desde_ultima=dias,
                ultima_auditoria=ultima.data,
                pode_movimentar=True,
                mensagem=f"🚨 URGENTE — {dias_para_bloqueio} dia(s) para bloqueio",
                mensagem_detalhada=(
                    f"Última conferência em {data_fmt}. "
                    f"Faltam apenas {dias_para_bloqueio} dia(s) para o bloqueio automático ({limite_fmt}). "
                    "Confira o estoque HOJE e registre ATUALIZAÇÃO no campo OBS."
                ),
                dias_para_bloqueio=dias_para_bloqueio,
                proxima_auditoria_limite=limite_dt,
                cor_hex="#fd7e14",
                emoji="🚨",
            )

        # ── AMARELO: aviso ────────────────────────────────────
        if dias >= DIAS_AVISO_AMARELO:
            return StatusAuditoria(
                nivel=NivelAuditoria.AMARELO,
                dias_desde_ultima=dias,
                ultima_auditoria=ultima.data,
                pode_movimentar=True,
                mensagem=f"⚠️ Aviso — {dias_para_bloqueio} dias para conferência",
                mensagem_detalhada=(
                    f"A conferência foi há {dias} dias (em {data_fmt}). "
                    f"O prazo limite é {limite_fmt}. "
                    "Planeje uma conferência de estoque em breve."
                ),
                dias_para_bloqueio=dias_para_bloqueio,
                proxima_auditoria_limite=limite_dt,
                cor_hex="#ffc107",
                emoji="⚠️",
            )

        # ── VERDE: em dia ─────────────────────────────────────
        return StatusAuditoria(
            nivel=NivelAuditoria.VERDE,
            dias_desde_ultima=dias,
            ultima_auditoria=ultima.data,
            pode_movimentar=True,
            mensagem=f"✅ Em dia — próxima conferência em {dias_para_bloqueio} dias",
            mensagem_detalhada=(
                f"Última conferência em {data_fmt}. "
                f"Próxima conferência obrigatória até {limite_fmt}."
            ),
            dias_para_bloqueio=dias_para_bloqueio,
            proxima_auditoria_limite=limite_dt,
            cor_hex="#28a745",
            emoji="✅",
        )

    # ── API pública ────────────────────────────────────────────

    def verificar_status(self, force_refresh: bool = False) -> StatusAuditoria:
        """
        Retorna o StatusAuditoria atual.
        Usa cache interno de 5 minutos — use force_refresh=True para forçar.
        """
        with self._lock:
            if not force_refresh and self._cache_valido():
                return self._cache_status   # type: ignore

            ultima = self.buscar_ultima_auditoria()
            status = self._calcular_status(ultima)
            self._cache_status = status
            self._cache_timestamp = datetime.now()
            return status

    def pode_movimentar(self) -> Tuple[bool, str]:
        """
        Retorna (pode: bool, motivo: str).
        Use antes de qualquer lançamento de entrada/saída.
        """
        status = self.verificar_status()
        return status.pode_movimentar, status.mensagem

    def checar_obs_tem_auditoria(self, obs: str) -> bool:
        """
        Verifica se a OBS de um lançamento contém ATUALIZAÇÃO.
        Usado para invalidar o cache quando uma nova auditoria é registrada.
        """
        return self._obs_e_auditoria(obs)

    def invalidar_cache(self):
        """Força nova consulta ao Sheets na próxima chamada."""
        with self._lock:
            self._cache_status = None
            self._cache_timestamp = None

    def notificar_novo_lancamento(self, obs: str):
        """
        Chamado após cada lançamento bem-sucedido.
        Se a OBS contém ATUALIZAÇÃO, invalida o cache imediatamente
        para que o próximo status reflita a nova conferência.
        """
        if self._obs_e_auditoria(obs):
            logger.info("[Auditoria] Nova ATUALIZAÇÃO detectada — cache invalidado.")
            self.invalidar_cache()

    def resumo_ia(self) -> Dict[str, Any]:
        """
        Retorna um dicionário resumido para integração com a IA (FASE 5).
        Inclui campos para o score de validação.
        """
        status = self.verificar_status()
        return {
            "bloqueado":          not status.pode_movimentar,
            "nivel":              status.nivel.value,
            "dias_desde_ultima":  status.dias_desde_ultima,
            "dias_para_bloqueio": status.dias_para_bloqueio,
            "mensagem":           status.mensagem,
            "penalidade_score":   self._calcular_penalidade(status),
        }

    @staticmethod
    def _calcular_penalidade(status: StatusAuditoria) -> int:
        """
        Penalidade que a IA aplica ao score de validação
        conforme o nível de auditoria (0 = OK, 100 = bloqueado).
        """
        if status.nivel == NivelAuditoria.VERMELHO:
            return 100   # bloqueia completamente
        if status.nivel == NivelAuditoria.LARANJA:
            return 20
        if status.nivel == NivelAuditoria.AMARELO:
            return 5
        return 0         # VERDE


# ──────────────────────────────────────────────────────────────
# Singleton thread-safe
# ──────────────────────────────────────────────────────────────
_gerenciador: Optional[GerenciadorAuditoria] = None
_lock_singleton = threading.Lock()


def get_gerenciador_auditoria() -> GerenciadorAuditoria:
    global _gerenciador
    if _gerenciador is None:
        with _lock_singleton:
            if _gerenciador is None:
                _gerenciador = GerenciadorAuditoria()
    return _gerenciador
