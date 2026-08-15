# Evidencia de propagación W3C TraceContext (trace_id consistente)

Request de prueba: `POST /transfer` con `{"from_account":"acc-001","to_account":"acc-002","amount":150.50}`
contra `service-a` (puerto 8001), que internamente llama a `service-b` (dos veces: `/debit` y `/credit`,
cada una con acceso a Postgres).

**trace_id generado por el SDK de service-a**: `93f978301e5105373a8a0c7e9ee7eb2e`

## 1. Trazas (Jaeger) — mismo trace_id, 23 spans, 2 servicios

```
GET /api/traces?service=service-a&operation=POST%20%2Ftransfer
-> traceID: 93f978301e5105373a8a0c7e9ee7eb2e (23 spans)
   service-a: POST /transfer, validate_transfer_request, POST (x2, llamadas http salientes)
   service-b: apply_debit_business_rules, apply_credit_business_rules,
              connect / SELECT / UPDATE (x2, Postgres vía SQLAlchemy)
```

## 2. Logs (Loki) — mismo trace_id como structured metadata

Consulta: `{service_name=~".+"}` en la ventana del request de prueba. Extracto de 2 de los 7
registros devueltos (formato JSON de la API `query_range` de Loki):

```json
{
  "stream": {
    "service_name": "service-b",
    "otelTraceID": "93f978301e5105373a8a0c7e9ee7eb2e",
    "otelSpanID": "5e67827c664904ca",
    "trace_id": "93f978301e5105373a8a0c7e9ee7eb2e",
    "span_id": "5e67827c664904ca",
    "account_id": "acc-001",
    "amount": "150.5"
  },
  "values": [["1786827337963560448", "débito aplicado"]]
}
```

```json
{
  "stream": {
    "service_name": "service-a",
    "otelTraceID": "93f978301e5105373a8a0c7e9ee7eb2e",
    "otelSpanID": "884e1f339f12603e",
    "trace_id": "93f978301e5105373a8a0c7e9ee7eb2e",
    "span_id": "884e1f339f12603e",
    "from_account": "acc-001",
    "to_account": "acc-002",
    "amount": "150.5",
    "duration_seconds": "0.024048328399658203"
  },
  "values": [["1786827337971018946", "transferencia completada"]]
}
```

## 3. Métricas (Prometheus, vía Collector)

Las métricas no llevan `trace_id` (no es una dimensión de cardinalidad razonable para series
temporales), pero sí comparten las mismas etiquetas `service.name` que las trazas y logs
(`service_name="service-a"`, `service_name="service-b"`), permitiendo pivotar de un pico en una
métrica hacia las trazas/logs del mismo servicio y ventana de tiempo — el patrón exacto que
implementa el *derived field* configurado en el datasource de Loki hacia Jaeger
(`grafana/provisioning/datasources/datasources.yaml`).

## Conclusión

El mismo `trace_id` (`93f978301e5105373a8a0c7e9ee7eb2e`) aparece de forma nativa en las trazas
(Jaeger) y en los logs (Loki) de **ambos** microservicios para la misma solicitud, confirmando que
la propagación de contexto W3C TraceContext (cabecera `traceparent` inyectada automáticamente por
`opentelemetry-instrumentation-httpx` en las llamadas salientes de service-a y leída por
`opentelemetry-instrumentation-fastapi` en service-b) funciona correctamente de punta a punta.
