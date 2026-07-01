#!/usr/bin/env python3
"""
karma_integrado_por_capas.py - Eco Gardener v1
Arquitectura de cuatro capas para un sistema de karma basado en experiencia real.
"""

import hashlib
import json
import os
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
REGIONS = ["LATAM", "USA", "EUROPA"]
TOTAL_TICKS = 20000
CRISIS_DURATION = 1000
CRISIS_STARTS = [3000, 8000, 13000]
CRISIS_ENDS = [s + CRISIS_DURATION for s in CRISIS_STARTS]

BASE_LAT = {"LATAM": 28, "USA": 18, "EUROPA": 22}
BASE_NRG = {"LATAM": 42, "USA": 35, "EUROPA": 38}
LAT_FAIL_MULT = 6.5
NRG_FAIL_MULT = 2.2
NRG_DEG_MULT = 1.4

# Pesos de la nueva fórmula de Karma (KF)
W_MEMORY = 0.3
W_CYCLES = 0.25
W_ANCHOR = 0.2
W_EFF = 0.15
W_CORR = 0.1

WINDOW_SIZE = 2000


# ============================================================================
# CAPA 1: LOCIVAULT (Libro contable inmutable)
# ============================================================================
class LocIVault:
    def __init__(self, vault_dir: str, identity: str):
        self.vault_dir = Path(vault_dir) / identity
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.chain_file = self.vault_dir / "chain.json"
        self._chain = self._load_chain()

    def _load_chain(self) -> List[Dict]:
        if self.chain_file.exists():
            with open(self.chain_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_chain(self):
        with open(self.chain_file, "w", encoding="utf-8") as f:
            json.dump(self._chain, f, indent=2, ensure_ascii=False)

    def write(self, data: bytes, metadata: Dict = None) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        nonce = os.urandom(16).hex()
        content_hash = hashlib.sha256(data).hexdigest()
        encrypted_hash = hashlib.sha256((content_hash + nonce).encode()).hexdigest()
        prev_hash = self._chain[-1]["entry_hash"] if self._chain else "0" * 64

        entry = {
            "index": len(self._chain),
            "timestamp": timestamp,
            "encrypted_hash": encrypted_hash,
            "content_hash": content_hash,
            "prev_hash": prev_hash,
            "metadata": metadata or {},
            "nonce": nonce,
        }
        entry_str = json.dumps(entry, sort_keys=True)
        entry["entry_hash"] = hashlib.sha256(entry_str.encode()).hexdigest()

        self._chain.append(entry)
        self._save_chain()
        return entry["entry_hash"]

    def verify_integrity(self) -> bool:
        for i, entry in enumerate(self._chain):
            entry_copy = entry.copy()
            stored_hash = entry_copy.pop("entry_hash")
            entry_str = json.dumps(entry_copy, sort_keys=True)
            if hashlib.sha256(entry_str.encode()).hexdigest() != stored_hash:
                return False
            if i > 0 and entry["prev_hash"] != self._chain[i-1]["entry_hash"]:
                return False
        return True


# ============================================================================
# CAPA 2: CORRECTION VERIFIER
# ============================================================================
class ValidatorOrigin(Enum):
    HUMAN = "human"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"

ORIGIN_WEIGHTS = {
    ValidatorOrigin.HUMAN: 1.0,
    ValidatorOrigin.AI_AGENT: 0.5,
    ValidatorOrigin.SYSTEM: 0.2
}

@dataclass
class HistoricalError:
    region: str
    cycle_number: int
    timestamp: float
    context_hash: str
    error_description: str
    resolved: bool = False

@dataclass
class CorrectionCandidate:
    region: str
    timestamp: float
    context_hash: str
    validator_origin: ValidatorOrigin
    validator_id: str
    references_error_cycle: int
    description: str = ""

@dataclass
class VerificationResult:
    is_correction: bool
    correction_weight: float
    reason: str
    details: Dict = field(default_factory=dict)

class CorrectionVerifier:
    def __init__(self, vault: LocIVault, min_context_delta: float = 0.1):
        self.vault = vault
        self.min_context_delta = min_context_delta
        self._errors: Dict[str, Dict[int, HistoricalError]] = {}

    def register_error(self, region: str, cycle_number: int, context: Dict, description: str = "") -> HistoricalError:
        context_hash = self._hash_context(context)
        error = HistoricalError(region, cycle_number, time.time(), context_hash, description)
        self._errors.setdefault(region, {})[cycle_number] = error
        self.vault.write(json.dumps({"type": "error", "region": region, "cycle": cycle_number,
                                     "context_hash": context_hash}).encode())
        return error

    def verify(self, candidate: CorrectionCandidate) -> VerificationResult:
        error = self._errors.get(candidate.region, {}).get(candidate.references_error_cycle)
        if not error or error.resolved:
            return VerificationResult(False, 0.0, "no_error")
        delta = self._context_delta(error.context_hash, candidate.context_hash)
        if delta < self.min_context_delta:
            return VerificationResult(False, 0.0, "sin_delta")

        weight = ORIGIN_WEIGHTS[candidate.validator_origin]
        delta_bonus = min(0.1, (delta - self.min_context_delta) * 0.2)
        final = min(1.0, weight + delta_bonus)

        error.resolved = True
        self.vault.write(json.dumps({"type": "correction", "region": candidate.region,
                                     "ref_cycle": candidate.references_error_cycle,
                                     "weight": final}).encode())
        return VerificationResult(True, final, "ok", {"weight": final, "delta": delta})

    @staticmethod
    def _hash_context(ctx: Dict) -> str:
        return hashlib.sha256(json.dumps(ctx, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _context_delta(h1: str, h2: str) -> float:
        if h1 == h2:
            return 0.0
        int1 = int(h1, 16)
        int2 = int(h2, 16)
        xor = int1 ^ int2
        return bin(xor).count("1") / (len(h1) * 4)


# ============================================================================
# CAPA 3: GHOST BALANCER (Cálculo del Nuevo Karma)
# ============================================================================
class GhostBalancer:
    def __init__(self, regions: List[str], window_size: int = WINDOW_SIZE):
        self.regions = regions
        self.window_size = window_size
        self.events: Dict[str, deque] = {r: deque(maxlen=window_size) for r in regions}
        self.corrections: Dict[str, List[Dict]] = {r: [] for r in regions}
        self.tick = 0

    def record(self, region: str, is_ok: bool, energy: float = 1.0,
               correction: bool = False, anchor: bool = False,
               correction_weight: float = 0.0, ref_error_cycle: Optional[int] = None):
        self.tick += 1
        event = {
            "tick": self.tick,
            "is_ok": is_ok,
            "energy": energy,
            "correction": correction,
            "anchor": anchor,
            "correction_weight": correction_weight if correction else 0.0,
            "ref_error_cycle": ref_error_cycle
        }
        self.events[region].append(event)
        if correction and correction_weight > 0:
            self.corrections[region].append(event)

    def calculate_karma(self, region: str) -> Dict[str, float]:
        if not self.events[region]:
            return {"kf": 0.0, "M": 0.0, "C": 0.0, "A": 0.0, "E": 0.0, "R": 0.0}

        window = list(self.events[region])
        total_ticks = len(window)

        # M: Memoria actualizada (porcentaje de eventos con anchor)
        M = sum(1 for e in window if e["anchor"]) / total_ticks

        # C: Ciclos completados (eventos "is_ok")
        C = sum(1 for e in window if e["is_ok"]) / total_ticks

        # A: Anclaje externo (promedio de anchors)
        A = sum(1 for e in window if e["anchor"]) / total_ticks

        # E: Eficiencia de recursos (1 - energía normalizada)
        avg_energy = sum(e["energy"] for e in window) / total_ticks
        E = max(0.0, 1.0 - (avg_energy / 100.0))

        # R: Corrección demostrada (suma ponderada de correcciones)
        R = sum(e["correction_weight"] for e in window) / total_ticks

        # Fórmula final
        kf = (M * W_MEMORY) + (C * W_CYCLES) + (A * W_ANCHOR) + (E * W_EFF) + (R * W_CORR)

        return {
            "kf": round(kf, 4),
            "M": round(M, 4),
            "C": round(C, 4),
            "A": round(A, 4),
            "E": round(E, 4),
            "R": round(R, 4)
        }


# ============================================================================
# SIMULACIÓN PRINCIPAL
# ============================================================================
def main():
    print("🚀 Iniciando simulación Eco Gardener v1 - Karma basado en experiencia\n")

    vault = LocIVault("vault", "sim_global")
    verifier = CorrectionVerifier(vault)
    balancer = GhostBalancer(REGIONS)

    # Simulación de ticks
    for tick in range(TOTAL_TICKS):
        for region in REGIONS:
            in_crisis = any(s <= tick < e for s, e in zip(CRISIS_STARTS, CRISIS_ENDS))

            # Probabilidades base
            fail_prob = 0.08
            if in_crisis and region == "LATAM":
                fail_prob *= LAT_FAIL_MULT
            elif in_crisis:
                fail_prob *= NRG_FAIL_MULT

            is_ok = random.random() > fail_prob
            energy = BASE_NRG[region] * (NRG_DEG_MULT if in_crisis else 1.0)
            anchor = random.random() < 0.15  # 15% de eventos tienen anclaje externo

            # Corrección humana (solo durante crisis y en LATAM más frecuente)
            correction = False
            corr_weight = 0.0
            if in_crisis and random.random() < (0.12 if region == "LATAM" else 0.04):
                correction = True
                # Simular verificación
                candidate = CorrectionCandidate(
                    region=region,
                    timestamp=time.time(),
                    context_hash="sim_context_" + str(tick),
                    validator_origin=ValidatorOrigin.HUMAN,
                    validator_id="human_expert_01",
                    references_error_cycle=tick - random.randint(5, 50)
                )
                result = verifier.verify(candidate)
                if result.is_correction:
                    corr_weight = result.correction_weight

            balancer.record(
                region=region,
                is_ok=is_ok,
                energy=energy,
                correction=correction,
                anchor=anchor,
                correction_weight=corr_weight
            )

        # Mostrar progreso cada 5000 ticks
        if tick % 5000 == 0 and tick > 0:
            print(f"✅ Tick {tick}/{TOTAL_TICKS} completado")

    # Resultados finales
    print("\n" + "="*60)
    print("📊 RESULTADOS FINALES - NUEVO KARMA (KF)")
    print("="*60)
    for region in REGIONS:
        karma = balancer.calculate_karma(region)
        print(f"\n🌎 Región: {region}")
        print(f"   KF (Karma Final)     : {karma['kf']:.4f}")
        print(f"   M - Memoria          : {karma['M']:.4f}")
        print(f"   C - Ciclos OK        : {karma['C']:.4f}")
        print(f"   A - Anclaje externo  : {karma['A']:.4f}")
        print(f"   E - Eficiencia       : {karma['E']:.4f}")
        print(f"   R - Correcciones     : {karma['R']:.4f}")

    print("\n✅ Integridad del vault:", vault.verify_integrity())
    print("🎉 Simulación finalizada. El vault está guardado en la carpeta 'vault/'")


if __name__ == "__main__":
    main()
