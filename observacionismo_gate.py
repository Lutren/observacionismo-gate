#!/usr/bin/env python3
"""
observacionismo_gate - SDK publico (MIT) del principio observacionista.

Gate de decisiones por evidencia + jamming + cost + approval. Sin dependencias
externas. Sin imports al runtime interno de Claudio. Auditable de un vistazo.

Uso minimo:
    from observacionismo_gate import ObsGate
    gate = ObsGate()
    decision = gate.decide("publish_video", evidence=True, R=0.22, epsilon=0.10)
    if decision.decision == "allow":
        ...

Contrato de decisiones (`decision`):
- "allow":   procede con witness.
- "hold":    espera o junta evidencia. No es failure.
- "degrade": usar camino mas barato/seguro.
- "ask":     requiere aprobacion humana.
- "block":   prohibido bajo politica actual.

Este modulo es el SDK publico del proyecto MEDIOEVO/Claudio. El motor canonico
interno vive en `claudio.core.psi_ethical_core` y NO se distribuye en este
paquete. Para uso comercial / open source este SDK es suficiente: define el
contrato de decisiones y un ledger JSONL append-only.

Licencia: MIT (ver LICENSE).
Version: 1.0.0
Canon: D017 (Gate Unificado, MEDIOEVO 2026-04-24).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import json


__version__ = "1.0.0"
__license__ = "MIT"
__all__ = [
    "ObsGate",
    "Decision",
    "canon_hash",
    "append_witness",
    "demo_csv",
    "DECISIONS",
    "DEFAULT_APPROVAL_ACTIONS",
    "DEFAULT_BLOCKED_ACTIONS",
]


DECISIONS = {"allow", "hold", "degrade", "ask", "block"}
DEFAULT_APPROVAL_ACTIONS = {
    "publish",
    "spend_credits",
    "paid_api",
    "clone_voice",
    "canon_write",
    "irreversible",
}
DEFAULT_BLOCKED_ACTIONS = {
    "bypass_captcha",
    "create_account",
    "change_password",
    "scrape_private_data",
    "purchase_without_approval",
}


@dataclass(frozen=True)
class Decision:
    """Witness-ready gate decision."""

    decision_id: str
    action: str
    decision: str
    gate: str
    reason: str
    timestamp: str
    next_step: str
    fallback: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canon_hash(payload: Any) -> str:
    """Return a stable short fingerprint for text or JSON-like payloads."""
    if isinstance(payload, str):
        raw = payload.strip()
    else:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_set(value: Iterable[str] | None) -> set[str]:
    return {str(item).strip() for item in (value or []) if str(item).strip()}


class ObsGate:
    """Observacionista decision engine.

    Reglas en orden:
        1. Sin evidencia      -> hold/evidence
        2. R >= J_c           -> hold/jamming
        3. accion bloqueada   -> block/blocked_action
        4. browser sin manifest -> block/browser_manifest
        5. paid_api o cost>0.7 -> ask/cost
        6. accion en aprobaciones -> ask/approval_required
        7. epsilon >= 0.7     -> degrade/uncertainty
        8. resto              -> allow/pass
    """

    def __init__(
        self,
        *,
        j_c: float = 0.65,
        epsilon_degrade: float = 0.70,
        approval_actions: Iterable[str] | None = None,
        blocked_actions: Iterable[str] | None = None,
        browser_requires_manifest: bool = True,
    ) -> None:
        self.j_c = j_c
        self.epsilon_degrade = epsilon_degrade
        self.approval_actions = set(DEFAULT_APPROVAL_ACTIONS)
        self.blocked_actions = set(DEFAULT_BLOCKED_ACTIONS)
        if approval_actions:
            self.approval_actions.update(_as_set(approval_actions))
        if blocked_actions:
            self.blocked_actions.update(_as_set(blocked_actions))
        self.browser_requires_manifest = browser_requires_manifest

    def decide(
        self,
        action: str,
        *,
        tags: Iterable[str] | None = None,
        evidence: bool = True,
        R: float = 0.0,
        J_c: float | None = None,
        epsilon: float = 0.0,
        browser: bool = False,
        manifest: bool = False,
        paid_api: bool = False,
        cost: float = 0.0,
    ) -> Decision:
        action = (action or "unknown").strip()
        tokens = {action, *_as_set(tags)}
        threshold = self.j_c if J_c is None else float(J_c)
        context = {
            "tags": sorted(tokens - {action}),
            "evidence": bool(evidence),
            "R": float(R),
            "J_c": threshold,
            "epsilon": float(epsilon),
            "browser": bool(browser),
            "manifest": bool(manifest),
            "paid_api": bool(paid_api),
            "cost": float(cost),
        }

        if not evidence:
            return self._decision(action, "hold", "evidence", "missing evidence", "gather missing artifact", "ask-for-input", context)
        if float(R) >= threshold:
            return self._decision(action, "hold", "jamming", f"R={float(R):.2f} >= J_c={threshold:.2f}", "wait and remeasure", "queue", context)
        blocked = tokens & self.blocked_actions
        if blocked:
            return self._decision(action, "block", "blocked_action", f"forbidden action: {sorted(blocked)}", "stop", "none", context)
        if browser and self.browser_requires_manifest and not manifest:
            return self._decision(action, "block", "browser_manifest", "browser automation requires manifest", "provide browser manifest", "manual-only", context)
        if paid_api or cost > 0.70:
            return self._decision(action, "ask", "cost", "external cost/API requires approval", "request approval", "free-first", context)
        approval = tokens & self.approval_actions
        if approval:
            return self._decision(action, "ask", "approval_required", f"approval required: {sorted(approval)}", "request approval", "manual-review", context)
        if float(epsilon) >= self.epsilon_degrade:
            return self._decision(action, "degrade", "uncertainty", f"epsilon={float(epsilon):.2f}", "run safer path", "local-only", context)
        return self._decision(action, "allow", "pass", "allowed with witness", "execute with witness", "none", context)

    def _decision(
        self,
        action: str,
        decision: str,
        gate: str,
        reason: str,
        next_step: str,
        fallback: str,
        context: dict[str, Any],
    ) -> Decision:
        payload = {"action": action, "decision": decision, "gate": gate, "reason": reason, "context": context}
        return Decision(
            decision_id=canon_hash(payload),
            action=action,
            decision=decision,
            gate=gate,
            reason=reason,
            timestamp=_utc_now(),
            next_step=next_step,
            fallback=fallback,
            context=context,
        )


def append_witness(path: str | Path, decision: Decision) -> None:
    """Append one JSONL witness event to `path` (creates parents)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")


def demo_csv(path: str | Path) -> None:
    """Generate examples CSV for human inspection."""
    gate = ObsGate()
    examples = [
        {"action": "local_render", "evidence": True, "R": 0.22, "epsilon": 0.10},
        {"action": "missing_brief", "evidence": False, "R": 0.22},
        {"action": "heavy_render", "evidence": True, "R": 0.71},
        {"action": "uncertain_edit", "evidence": True, "R": 0.22, "epsilon": 0.91},
        {"action": "publish", "tags": ["publish"], "evidence": True, "R": 0.22},
        {"action": "browser_upload", "browser": True, "manifest": False, "evidence": True, "R": 0.22},
        {"action": "change_password", "tags": ["change_password"], "evidence": True, "R": 0.22},
    ]
    rows = [gate.decide(**example).to_dict() for example in examples]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "observacionismo_gate_examples.csv"
    demo_csv(out)
    print(f"escrito {out}")
