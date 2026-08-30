"""security/scan_images.py — Módulo C: golden signal 'CVEs activos'.

Ejecuta Trivy (https://trivy.dev) contra las imágenes propias del stack y publica el
conteo de CVEs activos por severidad en el Prometheus Pushgateway local, para que
Prometheus lo scrapee y el dashboard "Golden Signals de Seguridad" lo muestre.

Requisitos: Trivy instalado (`brew install trivy` / `choco install trivy` / binario en PATH)
y el stack de docker-compose corriendo (para tener el Pushgateway disponible en :9091).

Uso:
    python security/scan_images.py
    python security/scan_images.py --images otel-microservices-service-a otel-microservices-service-b otel-microservices-data-service
"""
import argparse
import json
import shutil
import subprocess
import sys

import requests

DEFAULT_IMAGES = [
    "otel-microservices-service-a",
    "otel-microservices-service-b",
    "otel-microservices-data-service",
]
PUSHGATEWAY_URL = "http://localhost:9091"
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def scan_image(image: str) -> dict:
    result = subprocess.run(
        ["trivy", "image", "--format", "json", "--quiet", image],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(result.stdout)
    counts = {sev: 0 for sev in SEVERITIES}
    for result_entry in report.get("Results", []):
        for vuln in result_entry.get("Vulnerabilities", []) or []:
            sev = vuln.get("Severity", "UNKNOWN")
            if sev in counts:
                counts[sev] += 1
    return counts


def push_metrics(image: str, counts: dict):
    lines = []
    for sev, count in counts.items():
        lines.append(f'image_active_cves{{severity="{sev}"}} {count}')
    payload = "\n".join(lines) + "\n"
    resp = requests.post(f"{PUSHGATEWAY_URL}/metrics/job/security_scan/image/{image}", data=payload, timeout=10)
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs="*", default=DEFAULT_IMAGES)
    args = parser.parse_args()

    if not shutil.which("trivy"):
        print("Trivy no está instalado o no está en PATH. Instálalo desde https://trivy.dev/ y reintenta.")
        sys.exit(1)

    for image in args.images:
        print(f"Escaneando {image} con Trivy...")
        try:
            counts = scan_image(image)
        except subprocess.CalledProcessError as exc:
            print(f"  No se pudo escanear {image}: {exc.stderr}")
            continue
        print(f"  {image}: {counts}")
        push_metrics(image, counts)
        print(f"  Métricas publicadas en Pushgateway ({PUSHGATEWAY_URL}) para job=security_scan, image={image}")


if __name__ == "__main__":
    main()
