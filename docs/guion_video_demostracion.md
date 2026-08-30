# Guion para el video de demostración en vivo (≤ 10 minutos)

Guion con diálogo sugerido y los comandos exactos a ejecutar en cada minuto. Pensado para
grabarse con el stack ya corriendo (`docker compose up -d --build` ejecutado **antes** de
empezar a grabar, para no perder tiempo de video en la descarga/build de imágenes).

## Preparación (fuera de cámara, antes de grabar)

```bash
# 1. Levantar el stack completo
docker compose up -d --build

# 2. Verificar que todo está arriba
docker compose ps

# 3. Dejar accesos abiertos en el navegador (pestañas):
#    - http://localhost:3000/d/otel-observability-main   (Grafana - dashboard principal)
#    - http://localhost:3000/d/security-golden-signals    (Grafana - seguridad)
#    - http://localhost:16686                              (Jaeger UI)
#    - http://localhost:9090/alerts                        (Prometheus - reglas de alerta)
#    - http://localhost:9093                                (Alertmanager)
#    - http://localhost:8500/summary                        (resumen AIOps, se puede refrescar con F5)

# 4. (Opcional) generar algo de tráfico de fondo antes de grabar para que los paneles
#    no arranquen en "No data":
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8001/transfer -H "Content-Type: application/json" \
    -d '{"from_account":"acc-001","to_account":"acc-002","amount":10}' > /dev/null
done
```

---

## Minuto 0:00 – 0:40 | Introducción

**Diálogo:**
> "Hola, somos Leonardo Pérez, Iván Vera y Juan Felipe González. Este es el laboratorio
> integrador de Observabilidad: un sistema con tres microservicios, detección automática de
> anomalías con AIOps, observabilidad de red y seguridad, y dos experimentos de chaos
> engineering, todo corriendo en Docker y con el IaC completo para GCP y AWS documentado en
> el repositorio. Vamos a mostrar cada módulo con datos reales."

**Pantalla:** mostrar el `README.md` del repositorio (tabla de módulos A-E).

---

## Minuto 0:40 – 2:30 | Módulo A — Arquitectura de 3 microservicios

**Diálogo:**
> "Tenemos service-a, que orquesta transferencias; service-b, que maneja las cuentas en
> PostgreSQL; y el nuevo data-service, que audita cada transferencia en dos bases de datos
> que simulan Cloud SQL y RDS. Todo el tráfico entre servicios pasa por sidecars de Envoy,
> que hacen de service mesh local. Vamos a disparar una transferencia real."

**Comandos (en terminal, a la vista):**
```bash
curl -X POST http://localhost:8001/transfer \
  -H "Content-Type: application/json" \
  -d '{"from_account":"acc-001","to_account":"acc-002","amount":25.5}'
```

**Pantalla:** cambiar a Jaeger UI → buscar servicio `service-a` → abrir la traza más reciente.

**Diálogo:**
> "Aquí vemos una sola traza que atraviesa los tres microservicios: 31 spans, con el débito y
> crédito en service-b, y el registro de auditoría en data-service, incluyendo los atributos
> de OTel DB Semantic Conventions como `db.system` y `db.operation`."

---

## Minuto 2:30 – 4:00 | Dashboard principal de Grafana

**Pantalla:** Grafana → dashboard "Observabilidad OTel".

**Diálogo:**
> "Este dashboard muestra los SLIs de negocio: latencia p95/p99, tasa de errores, throughput
> y disponibilidad de los targets, además de la salud del propio OTel Collector. Todos estos
> paneles se alimentan de las métricas custom que exportamos desde los tres servicios vía
> OTLP."

*(Señalar en pantalla el panel de latencia y el de throughput mientras se refrescan.)*

---

## Minuto 4:00 – 5:30 | Módulo C — Network & Security Observability

**Comandos:**
```bash
python3 security/simulate_auth_traffic.py --target http://localhost:8003 --requests 100 --fail-rate 0.4
```

**Pantalla:** Grafana → dashboard "Golden Signals de Seguridad".

**Diálogo:**
> "Este es el dashboard de seguridad: intentos de autenticación fallidos, tráfico
> norte-sur y este-oeste medido en los sidecars de Envoy, y CVEs activos por imagen,
> obtenidos con un escaneo real de Trivy. VPC Flow Logs y Security Command Center /
> Security Hub quedan documentados como IaC en Terraform, listos para aplicar contra un
> proyecto real de GCP o una cuenta de AWS."

---

## Minuto 5:30 – 7:00 | Módulo B — AIOps: detección de anomalías

**Comandos:**
```bash
curl -s http://localhost:8500/summary
```

**Diálogo:**
> "Este servicio compara en tiempo real dos estrategias de alerta: una regla clásica de
> umbral estático, y nuestra regla de AIOps, que calcula una banda dinámica de baseline más
> dos desviaciones estándar y solo alerta cuando también se incumple el SLO de latencia. En
> nuestra última corrida, la regla de AIOps generó 7 alertas correlacionadas frente a 21 de
> umbral estático: una reducción del 66.7% de alertas ruidosas. Y cada alerta viene con el
> trace_id real del request que falló."

**Pantalla:** abrir uno de los `trace_id` de `aiops/results/alerts_log.jsonl` directamente en
Jaeger (`http://localhost:16686/trace/<trace_id>`) para mostrar el span en rojo.

---

## Minuto 7:00 – 8:45 | Módulo D — Chaos Engineering (en vivo)

**Diálogo:**
> "Vamos a inyectar un fallo real: +200 milisegundos de latencia en service-b, y vamos a
> medir cuánto tarda nuestro sistema en detectarlo y alertar."

**Comandos:**
```bash
python3 chaos/run_chaos_experiment.py latency --duration 60 --mttd-target 120
```

**Pantalla:** mientras corre (tarda ~30-40s), cambiar a Alertmanager (`http://localhost:9093`)
y refrescar hasta ver aparecer la alerta `TransferLatencySLOBreach`.

**Diálogo (al terminar el script):**
> "El script confirma el MTTD real: en nuestra última corrida documentada fue de 26.7
> segundos, muy por debajo del objetivo de 2 minutos. También ejecutamos el experimento de
> error rate en data-service, donde encontramos un hallazgo real: el MTTD fue de 139
> segundos, por encima del objetivo, porque data-service recibe menos tráfico que
> service-b. Documentamos esa causa raíz y la acción de mejora en
> `chaos/chaos_experiments.md`."

---

## Minuto 8:45 – 9:45 | Módulo E — Madurez de observabilidad

**Pantalla:** abrir `docs/madurez_observabilidad.md` (o el PDF ejecutivo, sección 7).

**Diálogo:**
> "Nos autoevaluamos contra el Observability Foundation Blueprint en 8 dominios. Hoy estamos
> en un promedio de 2.9 sobre 5: fuertes en los tres pilares y en OpenTelemetry, pero con
> oportunidad de mejora en observabilidad de red/seguridad en la nube real y en cultura de
> procesos como runbooks y on-call. Definimos un roadmap accionable a 3 meses, priorizando
> justamente cerrar la brecha de MTTD que acabamos de mostrar."

---

## Minuto 9:45 – 10:00 | Cierre

**Diálogo:**
> "Todo el código, la infraestructura como código para GCP y AWS, los scripts de los
> experimentos y el reporte ejecutivo completo están en el repositorio de GitHub. Gracias."

**Pantalla:** volver al README del repositorio.

---

## Notas para la grabación

- Si algún panel muestra "No data", esperar 10-15s (el `refresh` del dashboard es de 10s) o
  volver a generar tráfico con el comando de `curl` de la sección de preparación.
- El experimento de chaos de latencia es el más rápido de mostrar en vivo (~30-40s hasta la
  alerta). El de error rate tarda más (~140s) — si el tiempo del video es ajustado, mencionarlo
  solo con los resultados ya guardados en `chaos/results/error_rate_mttd.json` en vez de
  correrlo en vivo.
- Después de cada experimento de chaos, recuerden que el script desactiva el fallo
  automáticamente al terminar; no es necesario hacer rollback manual.
- Para no exceder los 10 minutos, si algún módulo se extiende, recortar el minuto 8:45-9:45
  (Módulo E) a 30 segundos, mostrando solo la tabla de madurez sin leer cada dominio.
