# Módulo D — Chaos Engineering Controlado

## Metodología

Cada experimento sigue el mismo protocolo, automatizado por `run_chaos_experiment.py`:

1. **Línea base** (10s): tráfico normal contra `service-a /transfer`, sin fallos.
2. **Inyección del fallo** vía el endpoint de chaos correspondiente (interruptor en runtime,
   sin reiniciar contenedores):
   - Experimento 1 — Latencia: `POST service-b:8000/chaos/latency {"enabled": true, "latency_ms": 200}`
   - Experimento 2 — Error rate: `POST data-service:8000/chaos/error-rate {"enabled": true, "error_rate": 0.1}`
3. **Detección**: se sondea la API de Alertmanager (`GET /api/v2/alerts`) hasta ver disparada
   la alerta de SLO correspondiente (`../otel-collector/alerting_rules.yml`, grupo
   `slo-chaos-experiments`), calculando `MTTD = t_alerta - t_inyección`.
4. **Rollback**: se desactiva el fallo inyectado y se detiene la carga.

## Cómo ejecutar

```bash
docker compose up -d --build
pip install -r chaos/requirements.txt

# Experimento 1: latencia +200ms en service-b
python chaos/run_chaos_experiment.py latency --duration 180 --mttd-target 120

# Experimento 2: error rate 10% en data-service
python chaos/run_chaos_experiment.py error-rate --duration 180 --mttd-target 120
```

Cada corrida guarda el resultado en `chaos/results/<experimento>_mttd.json`.

> **Nota de reproducibilidad**: los resultados de esta sección corresponden a una ejecución
> real de `run_chaos_experiment.py` contra el stack local (Docker corriendo sobre WSL2/Debian),
> el 2026-08-30. Los JSON completos están en `chaos/results/latency_mttd.json` y
> `chaos/results/error_rate_mttd.json`. Evidencia visual de las reglas de alerta cargadas en
> `../screenshots/16_prometheus_alerting_rules.png`.

## Experimento 1 — Latencia inyectada en service-b (+200ms)

| Campo | Valor |
|---|---|
| Alerta esperada | `TransferLatencySLOBreach` (p99 transferencias > 300ms) |
| MTTD medido | **26.7s** (inyectado 2026-08-30T20:42:48Z, detectado 2026-08-30T20:43:15Z) |
| ¿Cumple objetivo MTTD ≤ 2 min? | **Sí, con amplio margen** (26.7s vs. 120s objetivo, 4.5x más rápido de lo requerido) |
| ¿Se degradó el SLO? | Sí — el SLO de latencia p99 (300ms) se definió expresamente por debajo del incremento inyectado (200ms se suma a la latencia base de ~10-20ms de service-b más el HTTP round-trip), por lo que el experimento fuerza el incumplimiento. |
| ¿Se consumió error budget? | Este experimento afecta **latencia**, no error rate; no consume el error budget de disponibilidad, pero si el SLO combinado del servicio incluye un objetivo de latencia (p99 < 300ms, ventana de 30 días), cada minuto en incumplimiento consume el budget de ese SLO específico. _Completar con el % real de la ventana de evaluación afectado._ |
| ¿La alerta fue accionable? | Sí: incluye el nombre del servicio, el valor observado vs. el umbral del SLO, y el runbook implícito (revisar `service-b`, endpoint `/chaos/latency` como sospechoso conocido en el contexto del experimento). |

## Experimento 2 — Error rate 10% en data-service

| Campo | Valor |
|---|---|
| Alerta esperada | `DataServiceErrorRateSLOBreach` (error_rate > 8%) |
| MTTD medido | **139.3s** (inyectado 2026-08-30T20:43:36Z, detectado 2026-08-30T20:45:55Z) |
| ¿Cumple objetivo MTTD ≤ 2 min? | **No cumple** (139.3s vs. 120s objetivo, 19.3s por encima). Causa raíz: `data-service` solo recibe **una llamada de auditoría no crítica por transferencia** (baja tasa de requests/s), por lo que la ventana `rate(...[1m])` combinada con `for: 30s` tarda más en reflejar el 10% de error inyectado que en el experimento de latencia (que sí está en la ruta crítica de alto tráfico `/transfer`). Acción de mejora propuesta: reducir la ventana de `rate()` a 30s y/o aumentar la tasa de llamadas a `data-service` desde la carga de prueba. |
| ¿Se degradó el SLO? | Sí — con un 10% de error rate inyectado y un umbral de alerta al 8%, el SLO de disponibilidad de `data-service` se incumple mientras dura el experimento (`last_error_rate` observado = 10.6%, ver `curl http://localhost:8500/summary`). |
| ¿Se consumió error budget? | Sí. Para un SLO de disponibilidad del 99% (error budget mensual = 1%), un error rate sostenido del ~10.6% durante los ~139s que tardó en detectarse (más el resto del experimento, ~180s totales) consume `0.106 * 180 ≈ 19.1` segundos-error de los `0.01 * 30*86400 = 25920` segundos-error disponibles al mes, es decir **~0.07% del error budget mensual** por esta sola inyección de prueba. |
| ¿La alerta fue accionable? | Sí, y además vino enriquecida en la práctica: `aiops-anomaly-detector` emitió **7 alertas correlacionadas** (cada una con `trace_id` real de Jaeger, ej. `e78fe7869c5c06bfe5ff04ea9d75918b`, verificable en `http://localhost:16686/trace/<trace_id>`) frente a **21 alertas de umbral estático** durante la misma ventana — una **reducción de ruido del 66.7%** (`noise_reduction_pct` real reportado por `GET /summary`). |

## Comparación cualitativa MTTD vs. objetivo

El objetivo de la actividad es **MTTD ≤ 2 minutos**. Los componentes que determinan el MTTD
en este stack son, en orden:

1. `scrape_interval` de Prometheus (5s) + ventana de `rate()` (1m) → aporta hasta ~65s de
   retraso estructural en el peor caso.
2. `for: 30s` en las reglas de alerta (evita flapping por picos transitorios).
3. `group_wait: 5s` en Alertmanager antes de notificar.

Con esta configuración el MTTD teórico máximo es de ~100s, dentro del objetivo de 120s. La
validación empírica (2026-08-30, ver tabla arriba) confirmó esta estimación **solo
parcialmente**: el experimento de latencia (26.7s) la superó ampliamente porque afecta el
endpoint de alto tráfico `/transfer`; el experimento de error rate (139.3s) la incumplió
porque `data-service` recibe tráfico de baja frecuencia (solo la llamada de auditoría no
crítica de cada transferencia). **Conclusión accionable**: el MTTD real depende tanto de la
configuración de alertas como del volumen de tráfico que recibe el servicio afectado — un
hallazgo que solo se pudo confirmar ejecutando el experimento contra el stack real, no por
análisis teórico de la configuración.
