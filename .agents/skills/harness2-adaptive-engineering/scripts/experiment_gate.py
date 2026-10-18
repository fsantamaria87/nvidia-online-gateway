#!/usr/bin/env python3
"""Harness2-inspired contrastive evidence gate. NEVER approves LKG."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def evaluate(record, root):
    if not isinstance(record, dict) or not record.get("case_id"):
        raise ValueError("case_id requerido")
    kind = record.get("data_kind")
    if kind not in ("real", "synthetic_demo"):
        raise ValueError("data_kind incorrecto")
    base, candidate, gates = (record.get(k) for k in ("baseline", "candidate", "gates"))
    if not all(isinstance(v, dict) for v in (base, candidate, gates)):
        raise ValueError("baseline, candidate, gates requeridos")
    if not base.get("revision") or not candidate.get("revision") or base["revision"] == candidate["revision"]:
        raise ValueError("revisiones ausentes o idénticas")
    if not base.get("environment") or base["environment"] != candidate.get("environment"):
        raise ValueError("entornos no comparables")
    required = gates.get("required_tests")
    target = gates.get("target_tests", [])
    if not isinstance(required, list) or not required or not isinstance(target, list):
        raise ValueError("required_tests requeridos; target_tests debe ser lista")
    if not all(isinstance(t, str) and t for t in required + target) or len(set(required + target)) != len(required + target):
        raise ValueError("test names inválidos o duplicados")
    limits = gates.get("metric_limits", {})
    if not isinstance(limits, dict):
        raise ValueError("metric_limits incorrecto")
    verified = []
    for label, obj in (("baseline", base), ("candidate", candidate)):
        if not isinstance(obj.get("test_results"), dict) or not isinstance(obj.get("metrics"), dict):
            raise ValueError(f"{label}: tests/metrics requeridos")
        evidence = obj.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{label}: evidencia ausente")
        for entry in evidence:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise ValueError(f"{label}: evidencia incorrecta")
            p = (root / entry["path"]).resolve()
            if not p.is_relative_to(root.resolve()) or not p.is_file():
                raise ValueError(f"{label}: ruta insegura o inexistente")
            sha = entry.get("sha256")
            if not isinstance(sha, str) or len(sha) != 64 or hashlib.sha256(p.read_bytes()).hexdigest() != sha.lower():
                raise ValueError(f"{label}: SHA256 inválido")
            verified.append(f'{label}:{entry["path"]}')
    blocking, gains = [], []
    for name in required + target:
        old, new = base["test_results"].get(name), candidate["test_results"].get(name)
        if type(old) is not bool or type(new) is not bool:
            raise ValueError(f"test {name} incompleto")
        if name in required and (not old or not new):
            blocking.append(f"test crítico no pasa en ambas: {name}")
        elif old and not new:
            blocking.append(f"regresión de test: {name}")
        elif not old and new:
            gains.append(f"test reparado: {name}")
    for key, cfg in limits.items():
        if not isinstance(cfg, dict) or not any(k in cfg for k in ("max_increase", "max_regression_pct")):
            raise ValueError(f"límite de métrica {key} incorrecto")
        old, new = base["metrics"].get(key), candidate["metrics"].get(key)
        if not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x < 1e15 for x in (old, new)):
            raise ValueError(f"valor de métrica {key} inválido")
        for bound in ("max_increase", "max_regression_pct"):
            if bound in cfg and (type(cfg[bound]) not in (int, float) or not math.isfinite(cfg[bound]) or cfg[bound] < 0):
                raise ValueError(f"límite {bound} inválido")
        if "max_increase" in cfg and new > old + cfg["max_increase"] + 1e-9:
            blocking.append(f"métrica {key} supera incremento permitido")
        if "max_regression_pct" in cfg and new > old * (1 + cfg["max_regression_pct"] / 100.0) + 1e-9:
            blocking.append(f"métrica {key} supera tolerancia porcentual")
        if new < old:
            gains.append(f"métrica mejorada: {key}")
    if not gains:
        blocking.append("ninguna mejora comprobable")
    status = "BLOCK" if blocking else ("DEMO_ONLY" if kind == "synthetic_demo" else "ELIGIBLE_FOR_REVIEW")
    return {"status": status, "case_id": record["case_id"], "gains": gains,
            "blocking": blocking, "evidence_verified": verified,
            "disclaimer": "Gate declarativo: no autentica pruebas ni autoriza cambiar LKG."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        path = args.record.resolve()
        result = evaluate(json.loads(path.read_text(encoding="utf-8")), path.parent)
    except (OSError, ValueError, TypeError) as error:
        result = {"status": "INVALID", "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("DEMO_ONLY", "ELIGIBLE_FOR_REVIEW") else 2


if __name__ == "__main__":
    raise SystemExit(main())
