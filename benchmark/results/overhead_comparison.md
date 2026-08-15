# Resultados del benchmark de overhead (Fase 4)

Herramienta: k6 v0.53.0. Carga: rampa 0→50→100 VUs, sostenido en 100 VUs, 5 minutos totales,
contra el endpoint `POST /transfer` (service-a → service-b → Postgres), tal como pide la consigna
(50-100 usuarios concurrentes, 5 minutos). Mismo hardware, mismo `docker-compose`/proceso único
por servicio (`--workers 1`) en ambos casos, misma base de datos con saldos preseeded en 10,000,000
para evitar que el propio test degrade la latencia por errores de fondos insuficientes.

- **Baseline**: `benchmark/service-a-baseline` + `benchmark/service-b-baseline` (idéntica lógica de
  negocio, sin ningún import ni SDK de OpenTelemetry).
- **Instrumentado**: `service-a` + `service-b` (auto-instrumentación HTTP/DB, spans custom,
  métricas y logs OTLP hacia el Collector real, corriendo en paralelo).

## Tabla comparativa

| Métrica                                        | Sin instrumentación | Con instrumentación OTel | Delta            |
|-------------------------------------------------|---------------------|--------------------------|-------------------|
| Throughput sostenido                             | 157.25 req/s         | 88.16 req/s               | -43.9 %           |
| Latencia media (avg)                             | 407.63 ms            | 807.41 ms                 | +98.1 % (+399.8 ms)|
| Latencia p90                                     | 580.93 ms            | 1122.66 ms                | +93.3 %           |
| **Latencia p95**                                 | 612.82 ms            | 1172.05 ms                | +91.2 %           |
| **Latencia p99**                                 | 674.47 ms            | 1273.23 ms                | **+88.8 % (+598.8 ms)** |
| CPU combinado promedio (service-a + service-b)   | 107.6 %              | 111.4 %                   | +3.5 pp           |
| CPU máximo observado (proceso más cargado)       | 76.0 % (service-b)   | 81.0 % (service-b)        | +5.0 pp           |
| Memoria RSS combinada promedio                   | 158.6 MB             | 213.8 MB                  | **+34.8 % (+55.2 MB)** |
| Tasa de error HTTP                               | 0.008 % (4/47191)    | 0.00 % (0/26451)          | sin degradación funcional |
| Total de requests completados en 5 min           | 47,191                | 26,451                    | -43.9 %           |

## Interpretación

El overhead de latencia (p99 +88.8%) es considerablemente mayor que el overhead de CPU (+3.5 pp) o
memoria (+34.8%). Esto indica que el cuello de botella no es cómputo bruto sino **espera de I/O**
introducida por la instrumentación:

1. **Sampling al 100%** (`AlwaysOnSampler`, valor por defecto del SDK): cada request genera y
   exporta *todos* sus spans, sin muestreo. Una sola transferencia produce 23 spans (ver
   `screenshots/02_jaeger_trace_detail.png`), multiplicando por 23 el volumen de datos serializados
   y encolados por request frente al caso sin instrumentar.
2. **Auto-instrumentación de SQLAlchemy muy granular**: cada `SELECT`/`UPDATE`/`connect` genera un
   span propio, multiplicando el número de objetos creados en el hot path de la transacción.
3. **Logs también van vía OTLP** (`BatchLogRecordProcessor` + `OTLPLogExporter`) además de a stdout,
   duplicando la carga de serialización/red por cada línea de log de negocio.
4. **Un solo worker por servicio** (`--workers 1`, para que la comparación fuera limpia): al no
   paralelizar, la cola de exportación OTLP compite por el mismo hilo/loop de eventos que atiende
   requests entrantes, amplificando la latencia bajo 100 VUs concurrentes.

## Mitigaciones recomendadas para producción

- Bajar el sampling a un valor razonable (p.ej. `TraceIdRatioBased(0.1)` o sampling basado en
  cabeza/cola) en servicios de alto tráfico, reservando 100% solo para rutas críticas o errores.
- Aumentar `send_batch_size`/reducir `timeout` del processor `batch` en el Collector y en los SDKs
  para amortizar el costo de red por lote en vez de por span.
- Escalar horizontalmente los workers de uvicorn/gunicorn (el overhead relativo baja cuando el I/O
  de exportación se solapa con más capacidad de cómputo disponible).
- Evaluar exportar logs solo vía stdout + recolector de logs de la plataforma (Cloud
  Logging/CloudWatch vía agente) en lugar de duplicar por OTLP, si el volumen de logs es alto.
