"""Claudio SDK publico (MIT).

Modulos open source distribuibles separados del runtime interno.
Ver D017 (Gate Unificado) para contexto.
"""

from .observacionismo_gate import (
    DECISIONS,
    DEFAULT_APPROVAL_ACTIONS,
    DEFAULT_BLOCKED_ACTIONS,
    Decision,
    ObsGate,
    append_witness,
    canon_hash,
    demo_csv,
    __version__,
)

__all__ = [
    "ObsGate",
    "Decision",
    "DECISIONS",
    "DEFAULT_APPROVAL_ACTIONS",
    "DEFAULT_BLOCKED_ACTIONS",
    "append_witness",
    "canon_hash",
    "demo_csv",
    "__version__",
]
