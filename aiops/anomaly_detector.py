"""aiops/anomaly_detector.py — Módulo B: detección automática de anomalías + correlación.

Implementa la regla pedida por la actividad:
    error_rate > baseline + 2*sigma  Y  latency_p99 > SLO_threshold  -> alerta enriquecida
    con el trace_id de un request fallido reciente (correlación con Jaeger).

En paralelo evalúa una regla de umbral estático clásica (error_rate > 5% O p99 > SLO) para
poder comparar cuántas alertas "ruidosas" genera cada enfoque (evidencia cuantitativa pedida
en los criterios de calificación).

Simulación local: en GCP esto sería una política de "Cloud Monitoring Anomaly Detection" y en
AWS "DevOps Guru" (ver terraform/aiops.tf); aquí se reimplementa el mismo algoritmo (media +
2 sigma sobre una ventana móvil) como un servicio Python para poder demostrarlo con el stack
100% local, tal como autoriza la consigna de la actividad.
"""
import json
import logging
import os
import threading
import time
import urllib.parse
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aiops")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
JAEGER_URL = os.getenv("JAEGER_URL", "http://jaeger:16686")
ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL", "http://alertmanager:9093")
TARGET_SERVICE = os.getenv("AIOPS_TARGET_SERVICE", "data-service")

POLL_INTERVAL_SECONDS = float(os.getenv("AIOPS_POLL_INTERVAL_SECONDS", "10"))
BASELINE_WINDOW = int(os.getenv("AIOPS_BASELINE_WINDOW", "30"))
SIGMA_MULTIPLIER = float(os.getenv("AIOPS_SIGMA_MULTIPLIER", "2"))
SLO_LATENCY_P99_SECONDS = float(os.getenv("AIOPS_SLO_LATENCY_P99_SECONDS", "0.3"))

# Regla ingenua de comparación (lo que haría un sistema con umbrales estáticos clásico).
STATIC_ERROR_RATE_THRESHOLD = float(os.getenv("AIOPS_STATIC_ERROR_RATE_THRESHOLD", "0.02"))
STATIC_LATENCY_THRESHOLD_SECONDS = float(os.getenv("AIOPS_STATIC_LATENCY_THRESHOLD_SECONDS", "0.15"))

RESULTS_DIR = Path(os.getenv("AIOPS_RESULTS_DIR", "/app/results"))
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_LOG_PATH = RESULTS_DIR / "alerts_log.jsonl"
SUMMARY_PATH = RESULTS_DIR / "comparison_summary.json"

error_rate_history: deque = deque(maxlen=BASELINE_WINDOW)

state = {
    "correlated_alerts_count": 0,
    "static_alerts_count": 0,
    "last_error_rate": None,
    "last_latency_p99": None,
    "last_evaluation": None,
}


def _prom_instant_query(promql: str):
    resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": promql}, timeout=5)
    resp.raise_for_status()
    result = resp.json().get("data", {}).get("result", [])
    if not result:
        return None
    try:
        return float(result[0]["value"][1])
    except (KeyError, IndexError, ValueError):
        return None


def get_error_rate(service: str) -> float:
    promql = (
        f'sum(rate({service.replace("-", "_")}_errors_total[1m])) / '
        f'clamp_min(sum(rate({service.replace("-", "_")}_requests_total[1m])), 1)'
    )
    value = _prom_instant_query(promql)
    return value if value is not None else 0.0


def get_latency_p99(service: str) -> float:
    metric = f"{service.replace('-', '_')}_request_duration_seconds_bucket"
    promql = f"histogram_quantile(0.99, sum(rate({metric}[1m])) by (le))"
    value = _prom_instant_query(promql)
    return value if value is not None else 0.0


def find_recent_error_trace_id(service: str) -> str | None:
    """Correlación con Jaeger: busca el trace_id de un request fallido reciente."""
    tags = urllib.parse.quote(json.dumps({"error": "true"}))
    url = f"{JAEGER_URL}/api/traces?service={service}&tags={tags}&limit=1&lookback=5m"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0]["traceID"]
    except requests.RequestException as exc:
        log.warning("no se pudo consultar Jaeger para correlación: %s", exc)
    return None


def push_enriched_alert(error_rate: float, latency_p99: float, baseline_mean: float, baseline_std: float, trace_id: str | None):
    now = datetime.now(timezone.utc)
    alert = {
        "labels": {
            "alertname": "AnomalyCorrelatedErrorRateLatency",
            "service": TARGET_SERVICE,
            "severity": "critical",
        },
        "annotations": {
            "summary": f"{TARGET_SERVICE}: error_rate={error_rate:.4f} supera baseline+{SIGMA_MULTIPLIER}sigma "
            f"({baseline_mean:.4f}+{SIGMA_MULTIPLIER}*{baseline_std:.4f}) Y latency_p99={latency_p99:.3f}s supera SLO "
            f"({SLO_LATENCY_P99_SECONDS:.3f}s)",
            "trace_id": trace_id or "no-trace-found",
            "jaeger_url": f"{JAEGER_URL}/trace/{trace_id}" if trace_id else "",
        },
        "startsAt": now.isoformat(),
    }
    try:
        requests.post(f"{ALERTMANAGER_URL}/api/v2/alerts", json=[alert], timeout=5)
    except requests.RequestException as exc:
        log.warning("no se pudo enviar la alerta a Alertmanager: %s", exc)

    with ALERTS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "correlated", **alert, "timestamp": now.isoformat()}) + "\n")

    log.warning("ALERTA CORRELACIONADA emitida: %s", alert["annotations"]["summary"])


def log_static_alert(error_rate: float, latency_p99: float):
    now = datetime.now(timezone.utc)
    entry = {
        "type": "static_threshold",
        "timestamp": now.isoformat(),
        "error_rate": error_rate,
        "latency_p99": latency_p99,
        "reason": "error_rate>threshold" if error_rate > STATIC_ERROR_RATE_THRESHOLD else "latency_p99>threshold",
    }
    with ALERTS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    log.info("alerta de umbral est\u00e1tico (ruidosa) emitida: %s", entry["reason"])


def write_summary():
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                **state,
                "noise_reduction_pct": _noise_reduction_pct(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


def _noise_reduction_pct():
    static = state["static_alerts_count"]
    correlated = state["correlated_alerts_count"]
    if static == 0:
        return None
    return round(100 * (1 - (correlated / static)), 2)


def evaluation_loop():
    while True:
        try:
            error_rate = get_error_rate(TARGET_SERVICE)
            latency_p99 = get_latency_p99(TARGET_SERVICE)
            state["last_error_rate"] = error_rate
            state["last_latency_p99"] = latency_p99
            state["last_evaluation"] = datetime.now(timezone.utc).isoformat()

            # --- regla ingenua de umbrales est\u00e1ticos (para comparaci\u00f3n de ruido) ---
            if error_rate > STATIC_ERROR_RATE_THRESHOLD or latency_p99 > STATIC_LATENCY_THRESHOLD_SECONDS:
                state["static_alerts_count"] += 1
                log_static_alert(error_rate, latency_p99)

            # --- regla AIOps: baseline din\u00e1mico (media + 2 sigma) sobre ventana m\u00f3vil ---
            if len(error_rate_history) >= 5:
                mean = sum(error_rate_history) / len(error_rate_history)
                variance = sum((x - mean) ** 2 for x in error_rate_history) / len(error_rate_history)
                std = variance ** 0.5
                dynamic_threshold = mean + SIGMA_MULTIPLIER * std

                if error_rate > dynamic_threshold and latency_p99 > SLO_LATENCY_P99_SECONDS:
                    state["correlated_alerts_count"] += 1
                    trace_id = find_recent_error_trace_id(TARGET_SERVICE)
                    push_enriched_alert(error_rate, latency_p99, mean, std, trace_id)

            error_rate_history.append(error_rate)
            write_summary()
        except Exception as exc:  # el loop no debe morir por un error transitorio de red
            log.error("error en el ciclo de evaluaci\u00f3n AIOps: %s", exc)

        time.sleep(POLL_INTERVAL_SECONDS)


app = FastAPI(title="aiops-anomaly-detector")


@app.on_event("startup")
def on_startup():
    threading.Thread(target=evaluation_loop, daemon=True).start()
    log.info("aiops anomaly detector iniciado (target=%s)", TARGET_SERVICE)


@app.get("/health")
def health():
    return {"status": "ok", "service": "aiops-anomaly-detector"}


@app.get("/summary")
def summary():
    return {**state, "noise_reduction_pct": _noise_reduction_pct()}
