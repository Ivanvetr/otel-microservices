"""chaos/run_chaos_experiment.py — Módulo D: Chaos Engineering Controlado.

Ejecuta uno de los dos experimentos pedidos por la actividad, genera carga concurrente
mientras el fallo está activo, y mide el MTTD (Mean Time To Detect) como el tiempo entre
la inyección del fallo y el instante en que Alertmanager reporta la alerta de SLO
correspondiente (ver reglas en ../otel-collector/alerting_rules.yml, grupo
"slo-chaos-experiments").

Experimentos:
  latency     -> +200ms en service-b (POST /chaos/latency), carga sobre /transfer (service-a).
                 Alerta esperada: TransferLatencySLOBreach.
  error-rate  -> 10% de error rate en data-service (POST /chaos/error-rate), carga sobre
                 /records/gcp (data-service, vía service-a que llama data-service en cada
                 transferencia, o directamente).
                 Alerta esperada: DataServiceErrorRateSLOBreach.

Uso:
    python chaos/run_chaos_experiment.py latency --duration 180
    python chaos/run_chaos_experiment.py error-rate --duration 180

Requiere el stack levantado (`docker compose up -d --build`) y accesible en localhost.
El resultado (MTTD real medido) se guarda en chaos/results/<experimento>_mttd.json — estos
números deben generarse ejecutando este script contra el stack local, no se deben inventar.
"""
import argparse
import json
import random
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SERVICE_A_URL = "http://localhost:8001"
SERVICE_B_URL = "http://localhost:8002"
DATA_SERVICE_URL = "http://localhost:8003"
ALERTMANAGER_URL = "http://localhost:9093"

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

EXPERIMENTS = {
    "latency": {
        "expected_alert": "TransferLatencySLOBreach",
        "enable_url": f"{SERVICE_B_URL}/chaos/latency",
        "enable_payload": {"enabled": True, "latency_ms": 200},
        "disable_payload": {"enabled": False, "latency_ms": 200},
    },
    "error-rate": {
        "expected_alert": "DataServiceErrorRateSLOBreach",
        "enable_url": f"{DATA_SERVICE_URL}/chaos/error-rate",
        "enable_payload": {"enabled": True, "error_rate": 0.1},
        "disable_payload": {"enabled": False, "error_rate": 0.1},
    },
}

ACCOUNTS = ["acc-001", "acc-002", "acc-003"]
stop_load = threading.Event()


def generate_load():
    while not stop_load.is_set():
        from_acc, to_acc = random.sample(ACCOUNTS, 2)
        payload = {"from_account": from_acc, "to_account": to_acc, "amount": round(random.uniform(1, 50), 2)}
        try:
            requests.post(f"{SERVICE_A_URL}/transfer", json=payload, timeout=5)
        except requests.RequestException:
            pass
        time.sleep(0.1)


def get_active_alerts():
    resp = requests.get(f"{ALERTMANAGER_URL}/api/v2/alerts", timeout=5)
    resp.raise_for_status()
    return resp.json()


def wait_for_alert(alertname: str, after: datetime, timeout_seconds: int):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            alerts = get_active_alerts()
            for alert in alerts:
                if alert.get("labels", {}).get("alertname") == alertname:
                    starts_at = datetime.fromisoformat(alert["startsAt"].replace("Z", "+00:00"))
                    if starts_at >= after:
                        return starts_at
        except requests.RequestException as exc:
            print(f"  (aviso) no se pudo consultar Alertmanager todavía: {exc}")
        time.sleep(2)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", choices=EXPERIMENTS.keys())
    parser.add_argument("--duration", type=int, default=180, help="Duración total del experimento en segundos")
    parser.add_argument("--mttd-target", type=int, default=120, help="MTTD objetivo en segundos (default 2 min)")
    args = parser.parse_args()

    config = EXPERIMENTS[args.experiment]

    print(f"[1/4] Iniciando generación de carga base contra {SERVICE_A_URL}/transfer ...")
    load_thread = threading.Thread(target=generate_load, daemon=True)
    load_thread.start()
    time.sleep(10)  # línea base antes de inyectar el fallo

    print(f"[2/4] Inyectando fallo: {args.experiment} ({config['enable_payload']})")
    t_injection = datetime.now(timezone.utc)
    requests.post(config["enable_url"], json=config["enable_payload"], timeout=5).raise_for_status()

    print(f"[3/4] Esperando alerta '{config['expected_alert']}' en Alertmanager (objetivo MTTD <= {args.mttd_target}s)...")
    t_detected = wait_for_alert(config["expected_alert"], t_injection, args.duration)

    print("[4/4] Desactivando el fallo inyectado...")
    requests.post(config["enable_url"], json=config["disable_payload"], timeout=5).raise_for_status()
    stop_load.set()
    load_thread.join(timeout=5)

    mttd_seconds = (t_detected - t_injection).total_seconds() if t_detected else None
    result = {
        "experiment": args.experiment,
        "expected_alert": config["expected_alert"],
        "injected_at": t_injection.isoformat(),
        "detected_at": t_detected.isoformat() if t_detected else None,
        "mttd_seconds": mttd_seconds,
        "mttd_target_seconds": args.mttd_target,
        "mttd_within_target": (mttd_seconds is not None and mttd_seconds <= args.mttd_target),
    }

    out_path = RESULTS_DIR / f"{args.experiment.replace('-', '_')}_mttd.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if mttd_seconds is not None:
        print(f"\nMTTD medido: {mttd_seconds:.1f}s (objetivo <= {args.mttd_target}s) -> "
              f"{'CUMPLE' if result['mttd_within_target'] else 'NO CUMPLE'}")
    else:
        print(f"\nNo se detectó la alerta '{config['expected_alert']}' dentro de {args.duration}s.")
    print(f"Resultado guardado en {out_path}")


if __name__ == "__main__":
    main()
