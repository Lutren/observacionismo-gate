# observacionismo_gate (SDK MIT)

Gate de decisiones por **evidencia + jamming + cost + approval** con witness ledger
JSONL. Sin dependencias externas. Sin imports al runtime interno de Claudio.

Distribuible como modulo open source para que terceros adopten el principio
observacionista en sus propios pipelines de IA y automatizacion.

## Problemas que ataca

- Claims sin evidencia: si no hay evidencia, el gate devuelve `hold/evidence`.
- Alucinación convertida en acción: antes de publicar, gastar, navegar o tocar
  archivos, la decisión queda registrada.
- Automatización sin humano: acciones caras, inciertas o sensibles piden
  aprobación.
- Memoria operativa débil: el witness ledger deja una línea verificable para la
  siguiente sesión o agente.

## Instalacion (uso directo)

Copia `observacionismo_gate.py` a tu proyecto. No requiere `pip install`.

## Uso minimo

```python
from observacionismo_gate import ObsGate, append_witness

gate = ObsGate()
decision = gate.decide("publish_video", evidence=True, R=0.22, epsilon=0.10)
if decision.decision == "allow":
    append_witness("witness/decisions.jsonl", decision)
    do_publish()
```

## Contrato de decisiones

| decision | significado |
|----------|-------------|
| `allow`   | procede con witness |
| `hold`    | espera o junta evidencia (no es failure) |
| `degrade` | usar camino mas barato/seguro |
| `ask`     | requiere aprobacion humana |
| `block`   | prohibido bajo politica actual |

## Reglas en orden

1. Sin evidencia        -> `hold/evidence`
2. R >= J_c             -> `hold/jamming`
3. Accion bloqueada     -> `block/blocked_action`
4. Browser sin manifest -> `block/browser_manifest`
5. paid_api o cost>0.7  -> `ask/cost`
6. Accion en aprobaciones -> `ask/approval_required`
7. epsilon >= 0.7       -> `degrade/uncertainty`
8. Resto                -> `allow/pass`

## Demo

```bash
python observacionismo_gate.py
# escribe observacionismo_gate_examples.csv con 7 escenarios
```

## Origen

Modulo originado en MEDIOEVO/Claudio bajo decision canonica D017 (Gate Unificado,
2026-04-24). El motor canonico interno (`claudio.core.psi_ethical_core`) NO se
distribuye en este paquete: usa este SDK si quieres adoptar solo el contrato
publico de decisiones.

## Licencia

MIT (ver `LICENSE`).
