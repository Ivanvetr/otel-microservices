# Módulo B — AIOps: Detección Automática de Anomalías

`anomaly_detector.py` implementa la regla de correlación pedida por la actividad:

```
error_rate(data-service) > baseline_móvil + 2σ   Y   latency_p99(data-service) > SLO
    -> alerta enriquecida con el trace_id de un request fallido reciente (Jaeger)
```

En paralelo evalúa una regla clásica de **umbral estático** (`error_rate > 2%` o
`latency_p99 > 150ms`) para poder comparar cuántas alertas "ruidosas" genera cada enfoque.

## Equivalente en la nube real

| Local (este servicio) | GCP | AWS |
|---|---|---|
| baseline móvil + 2σ sobre `error_rate`/`latency_p99` | Cloud Monitoring Anomaly Detection (`terraform/aiops.tf`) | DevOps Guru (`terraform/aiops.tf`) |
| Correlación con `trace_id` vía Jaeger API | Correlación con Cloud Trace | Correlación con AWS X-Ray |
| Alerta enriquecida -> Alertmanager | Notification Channel (email/Slack) | SNS Topic |

## Cómo probarlo

```bash
docker compose up -d --build
# generar carga normal
curl -X POST http://localhost:8001/transfer -H "Content-Type: application/json" \
  -d '{"from_account":"acc-001","to_account":"acc-002","amount":10}'

# inyectar el experimento de caos #2 (ver ../chaos/) para forzar error_rate alto
python ../chaos/run_chaos_experiment.py error-rate --duration 120

# ver el resumen de detección
curl http://localhost:8500/summary
```

`GET /summary` devuelve:
- `correlated_alerts_count`: alertas emitidas por la regla AIOps (baseline+2σ y SLO).
- `static_alerts_count`: alertas que un sistema de umbrales estáticos habría emitido.
- `noise_reduction_pct`: reducción porcentual de alertas de la regla AIOps vs. la estática.

El detalle de cada alerta (incluyendo `trace_id` y `jaeger_url`) queda en
`aiops/results/alerts_log.jsonl` (volumen `aiops-results` del contenedor). Evidencia real capturada
el 2026-08-30: `../screenshots/14_jaeger_trace_correlacionada_aiops.png` muestra en Jaeger el span
de error exacto (`data_service.write_audit_record`) al que apunta una de las alertas
correlacionadas. Ese día se registraron 7 alertas correlacionadas vs. 21 de umbral estático
(66.7% de reducción de ruido), ver `aiops/results/comparison_summary.json`.

## Parámetros configurables (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `AIOPS_TARGET_SERVICE` | `data-service` | Servicio monitoreado |
| `AIOPS_POLL_INTERVAL_SECONDS` | `10` | Frecuencia de evaluación |
| `AIOPS_BASELINE_WINDOW` | `30` | Tamaño de la ventana móvil para calcular media/σ |
| `AIOPS_SIGMA_MULTIPLIER` | `2` | Multiplicador de σ pedido por la actividad |
| `AIOPS_SLO_LATENCY_P99_SECONDS` | `0.3` | Umbral de SLO de latencia p99 |
| `AIOPS_STATIC_ERROR_RATE_THRESHOLD` | `0.02` | Umbral estático de comparación (error rate) |
| `AIOPS_STATIC_LATENCY_THRESHOLD_SECONDS` | `0.15` | Umbral estático de comparación (latencia) |
