#!/usr/bin/env python3
"""Genera el informe técnico PDF (Fases 1-4) a partir de los datos y capturas reales
generadas en este proyecto (ver README.md para cómo se obtuvieron)."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS = ROOT / "screenshots"
OUT = ROOT / "docs" / "Informe_Tecnico_Observabilidad_OTel.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=20, leading=26, spaceAfter=6))
styles.add(ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=13, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#0B3D91")))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#0B3D91")))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.2, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("BodySmall", parent=styles["Normal"], fontSize=9, leading=12.5, alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=14))
styles.add(ParagraphStyle("CodeBlock", parent=styles["Normal"], fontName="Courier", fontSize=8, leading=10.5, backColor=colors.HexColor("#F4F4F4"), spaceAfter=8))
styles.add(ParagraphStyle("TableCell", parent=styles["Normal"], fontSize=8.5, leading=11))
styles.add(ParagraphStyle("TableHeader", parent=styles["Normal"], fontSize=8.7, leading=11, textColor=colors.white, fontName="Helvetica-Bold"))

story = []


def h1(text):
    story.append(Paragraph(text, styles["H1"]))


def h2(text):
    story.append(Paragraph(text, styles["H2"]))


def p(text):
    story.append(Paragraph(text, styles["Body"]))


def bullets(items):
    story.append(
        ListFlowable(
            [ListItem(Paragraph(i, styles["Body"]), leftIndent=6) for i in items],
            bulletType="bullet",
            start="•",
            leftIndent=14,
        )
    )
    story.append(Spacer(1, 6))


def image_with_caption(path, caption, max_width=16 * cm, max_height=9.5 * cm):
    from PIL import Image as PILImage

    im = PILImage.open(path)
    w, h = im.size
    ratio = min(max_width / w, max_height / h)
    story.append(Image(str(path), width=w * ratio, height=h * ratio))
    story.append(Paragraph(caption, styles["Caption"]))


def data_table(header, rows, col_widths=None, font_size=8.5, keep_together=False):
    header_row = [Paragraph(f"<b>{c}</b>", styles["TableHeader"]) for c in header]
    body_rows = [[Paragraph(str(c), styles["TableCell"]) for c in row] for row in rows]
    t = Table([header_row] + body_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D91")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    if keep_together:
        story.append(KeepTogether([t, Spacer(1, 10)]))
    else:
        story.append(t)
        story.append(Spacer(1, 10))


# ============================== PORTADA ====================================
story.append(Spacer(1, 4 * cm))
story.append(Paragraph("Instrumentación de Extremo a Extremo con OpenTelemetry", styles["TitleBig"]))
story.append(Paragraph(
    "Trazas, métricas y logs correlacionados en una arquitectura de dos microservicios, "
    "despliegue del OTel Collector y análisis cuantitativo de overhead",
    styles["SubTitle"],
))
story.append(Spacer(1, 2 * cm))
story.append(Paragraph("Universidad de La Sabana — Maestría en Arquitectura de Software", styles["SubTitle"]))
story.append(Paragraph("Observabilidad en ambientes productivos", styles["SubTitle"]))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph("Leonardo Pérez — Juan Felipe González Iván Vera", styles["SubTitle"]))
story.append(Spacer(1, 3 * cm))
story.append(Paragraph("24 de agosto de 2026", styles["SubTitle"]))
story.append(PageBreak())

# ============================== 1. INTRODUCCIÓN ==============================
h1("1. Introducción y objetivo")
p(
    "Este informe documenta la implementación práctica de una arquitectura de observabilidad "
    "completa (trazas, métricas y logs) para dos microservicios con dependencia HTTP y acceso a "
    "base de datos, siguiendo las cuatro fases de la consigna: instrumentación con el SDK de "
    "OpenTelemetry (OTel), despliegue de un OTel Collector, integración con backends de "
    "visualización, y un análisis cuantitativo del overhead que introduce la instrumentación. "
    "Todo el código, la configuración de infraestructura (Terraform/Helm) y los resultados "
    "presentados en las secciones siguientes fueron ejecutados y verificados de extremo a "
    "extremo en un entorno de desarrollo real (no simulado): las trazas, logs, métricas y datos "
    "de benchmark que se muestran provienen de una ejecución real del stack completo, no de "
    "capturas ilustrativas."
)
p(
    "El repositorio que acompaña este informe contiene: el código de instrumentación de ambos "
    "servicios, la configuración del OTel Collector, los manifiestos de Terraform y Helm, el "
    "dashboard de Grafana (6 paneles), el script de carga de k6 y los resultados crudos del "
    "benchmark de overhead."
)

h2("1.1. Alcance y arquitectura objetivo")
p(
    "<b>service-a</b> expone <code>POST /transfer</code> y actúa como orquestador de una "
    "transferencia entre cuentas: valida la solicitud (span de negocio "
    "<font face='Courier'>validate_transfer_request</font>) y llama vía HTTP a "
    "<b>service-b</b> para debitar la cuenta origen y acreditar la cuenta destino. "
    "<b>service-b</b> expone <code>/accounts/{id}/balance</code>, <code>/debit</code> y "
    "<code>/credit</code>, con acceso a PostgreSQL vía SQLAlchemy y dos spans de negocio "
    "propios (<font face='Courier'>apply_debit_business_rules</font>, "
    "<font face='Courier'>apply_credit_business_rules</font>). Esta arquitectura reproduce "
    "exactamente la dependencia pedida por la consigna: <i>service-a → service-b (HTTP) → "
    "PostgreSQL (DB)</i>."
)

# ============================== 2. ARQUITECTURA ==============================
h1("2. Arquitectura de la solución")
p(
    "La Figura conceptual del pipeline de observabilidad es: cada servicio exporta sus tres "
    "señales vía OTLP (gRPC) al OTel Collector, que las procesa (<i>memory_limiter → resource → "
    "batch</i>) y las reparte a tres backends especializados — Jaeger para trazas, Prometheus "
    "para métricas y Loki para logs (equivalente local, en este entorno, de Cloud Logging/"
    "CloudWatch). Grafana consulta los tres backends y permite pivotar de una métrica anómala a "
    "los logs y trazas del mismo <code>trace_id</code>."
)
data_table(
    ["Componente", "Tecnología", "Rol"],
    [
        ["service-a", "Python 3.11 + FastAPI + OTel SDK", "Orquesta transferencias; cliente HTTP de service-b"],
        ["service-b", "Python 3.11 + FastAPI + SQLAlchemy + OTel SDK", "Lógica de cuentas; acceso a PostgreSQL"],
        ["PostgreSQL 16", "Base de datos relacional", "Persistencia de saldos de cuentas"],
        ["OTel Collector", "otel/opentelemetry-collector-contrib 0.110", "Receptor OTLP único; batching y fan-out a los 3 backends"],
        ["Jaeger 1.60", "Backend de trazas (OTLP nativo)", "Almacenamiento y UI de trazas distribuidas"],
        ["Prometheus 2.45", "Backend de métricas", "Scrape del exporter Prometheus del Collector"],
        ["Loki 3.1", "Backend de logs", "Ingesta OTLP nativa; equivalente a Cloud Logging/CloudWatch"],
        ["Grafana 11.2", "Visualización unificada", "Dashboards + Explore (correlación log↔traza vía trace_id)"],
    ],
    col_widths=[3.4 * cm, 6.6 * cm, 6.8 * cm],
)
p(
    "<b>Decisión de diseño — un único receiver OTLP</b>: en vez de que cada servicio hable un "
    "protocolo distinto con cada backend, todas las señales viajan como OTLP hacia un único "
    "punto (el Collector), que centraliza el procesamiento (límites de memoria, batching, "
    "enriquecimiento de atributos de recurso) y desacopla a las aplicaciones de los backends "
    "concretos: cambiar de Jaeger a Tempo, o de Loki a Cloud Logging, es un cambio de "
    "configuración del Collector, no del código de los servicios."
)

# ============================== 3. FASE 1 ==============================
h1("3. Fase 1 — Instrumentación con el SDK de OpenTelemetry")
h2("3.1. Los tres pilares")
data_table(
    ["Pilar", "Mecanismo", "Destino"],
    [
        ["Trazas", "Auto-instrumentación FastAPI/httpx/SQLAlchemy + spans custom de negocio", "OTLP gRPC → OTel Collector → Jaeger"],
        ["Métricas", "Counters e histograms del SDK de métricas de OTel (PeriodicExportingMetricReader)", "OTLP gRPC → OTel Collector → exporter Prometheus"],
        ["Logs", "logging estándar de Python + LoggingInstrumentor (inyecta trace_id/span_id) + formatter JSON", "stdout (JSON estructurado) y OTLP → OTel Collector → Loki"],
    ],
    col_widths=[2.6 * cm, 9.4 * cm, 4.8 * cm],
)

h2("3.2. Auto-instrumentación aplicada")
bullets(
    [
        "<b>HTTP entrante</b>: <font face='Courier'>opentelemetry-instrumentation-fastapi</font> en ambos servicios (crea el span raíz de cada request y decodifica la cabecera <font face='Courier'>traceparent</font> entrante).",
        "<b>HTTP saliente</b>: <font face='Courier'>opentelemetry-instrumentation-httpx</font> en service-a (inyecta automáticamente <font face='Courier'>traceparent</font> en cada llamada a service-b).",
        "<b>Base de datos</b>: <font face='Courier'>opentelemetry-instrumentation-sqlalchemy</font> en service-b (un span por <font face='Courier'>connect</font>/<font face='Courier'>SELECT</font>/<font face='Courier'>UPDATE</font>).",
        "<b>Logging</b>: <font face='Courier'>opentelemetry-instrumentation-logging</font> inyecta <font face='Courier'>otelTraceID</font>/<font face='Courier'>otelSpanID</font> en cada <font face='Courier'>LogRecord</font>, que un formatter JSON propio serializa como <font face='Courier'>trace_id</font>/<font face='Courier'>span_id</font>.",
    ]
)

h2("3.3. Spans custom de lógica de negocio crítica")
p(
    "Además de la auto-instrumentación, se crearon spans manuales alrededor de la lógica de "
    "negocio que no es visible para el instrumentador automático (reglas de negocio, no "
    "operaciones de I/O):"
)
data_table(
    ["Servicio", "Span custom", "Atributos capturados"],
    [
        ["service-a", "validate_transfer_request", "transfer.from_account, transfer.to_account, transfer.amount"],
        ["service-b", "apply_debit_business_rules", "account.id, debit.amount (marca error si fondos insuficientes)"],
        ["service-b", "apply_credit_business_rules", "account.id, credit.amount"],
        ["service-b", "calculate_balance_with_fees", "account.balance, account.fee_rate (comisión de mantenimiento)"],
    ],
    col_widths=[2.6 * cm, 6.4 * cm, 7.8 * cm],
)

# ============================== 4. FASE 2 ==============================
h1("4. Fase 2 — Despliegue del OTel Collector")
h2("4.1. Pipeline configurado")
p(
    "El archivo <font face='Courier'>otel-collector/otel-collector-config.yaml</font> define un "
    "único receiver OTLP (gRPC en 4317, HTTP en 4318) y tres pipelines (traces/metrics/logs) que "
    "comparten la misma cadena de procesadores:"
)
bullets(
    [
        "<b>memory_limiter</b> (primero en la cadena): protege al Collector de quedarse sin memoria bajo carga alta — relevante para el benchmark de la Fase 4, donde el Collector recibe tráfico de hasta 100 VUs concurrentes.",
        "<b>resource</b>: añade <font face='Courier'>deployment.environment</font> y <font face='Courier'>collector.name</font> de forma homogénea a las tres señales.",
        "<b>batch</b>: agrupa spans/métricas/logs antes de exportar (tamaño máximo 2048, timeout 5s), reduciendo el número de llamadas de red hacia los backends.",
    ]
)
p(
    "Exporters: <font face='Courier'>otlp/jaeger</font> (trazas, hacia el receiver OTLP nativo de "
    "Jaeger 1.35+), <font face='Courier'>prometheus</font> (métricas, expone "
    "<font face='Courier'>:8889/metrics</font> para scrape) y "
    "<font face='Courier'>otlphttp/loki</font> (logs, hacia el endpoint OTLP nativo de Loki 3.x). "
    "El propio Collector expone además sus métricas internas en "
    "<font face='Courier'>:8888</font> (CPU, memoria, spans/logs/métricas rechazados o "
    "fallidos), usadas en el panel 6 del dashboard de Grafana."
)

h2("4.2. Despliegue en la nube (GCP)")
p(
    "Se optó por <b>Cloud Run</b> para el Collector y <b>GKE Autopilot + Helm</b> para los "
    "backends con estado (Jaeger, Prometheus, Grafana), en vez de forzar todo a un único modelo "
    "de despliegue. El razonamiento se detalla en <font face='Courier'>terraform/README.md</font>: "
    "el Collector no conserva estado entre requests (es un pipeline de transformación), por lo "
    "que Cloud Run — que escala a cero y no requiere gestión de nodos — es la opción de menor "
    "costo operativo; Jaeger, Prometheus y Grafana sí requieren volúmenes persistentes "
    "(traces, series temporales, dashboards), un patrón que encaja mejor en GKE. El código "
    "Terraform (<font face='Courier'>terraform/</font>) provisiona las APIs de GCP necesarias, "
    "sube la configuración del Collector a Secret Manager, crea una Service Account de mínimo "
    "privilegio y despliega el servicio de Cloud Run; los archivos "
    "<font face='Courier'>helm/values-{jaeger,prometheus,grafana}.yaml</font> despliegan los "
    "backends sobre GKE reutilizando exactamente la misma configuración de datasources y el "
    "mismo dashboard JSON que el entorno local."
)
p(
    "<b>Nota de alcance</b>: este código Terraform/Helm no fue aplicado contra un proyecto real "
    "de GCP — el entorno de desarrollo de este informe no contaba con credenciales de nube (ver "
    "sección 7). Es código completo y sintácticamente válido, listo para <font face='Courier'>"
    "terraform apply</font> una vez se disponga de un proyecto y credenciales."
)

# ============================== 5. FASE 3 ==============================
h1("5. Fase 3 — Backends y visualización")

h2("5.1. Trazas en Jaeger UI")
p(
    "La siguiente captura muestra el listado de trazas reales generadas por el tráfico de prueba "
    "contra <code>service-a</code>, incluyendo tanto transferencias exitosas (23 spans, ~20-30ms) "
    "como transferencias fallidas por validación de negocio (5 spans, marcadas en rojo como "
    "\"1 Error\")."
)
image_with_caption(
    SCREENSHOTS / "01_jaeger_trace_list_cropped.png",
    "Figura 1. Jaeger UI — listado de trazas de service-a, con éxitos y errores de negocio reales.",
)
p(
    "La siguiente captura expande una traza completa de <code>POST /transfer</code>: 23 spans, "
    "profundidad 5, dos servicios. Se observa la jerarquía completa: el span raíz de service-a, "
    "el span custom <font face='Courier'>validate_transfer_request</font>, las dos llamadas HTTP "
    "salientes hacia service-b (débito y crédito), y dentro de cada una los spans custom de "
    "negocio (<font face='Courier'>apply_debit_business_rules</font>/"
    "<font face='Courier'>apply_credit_business_rules</font>) junto con los spans de "
    "auto-instrumentación de SQLAlchemy (<font face='Courier'>connect</font>, "
    "<font face='Courier'>SELECT</font>, <font face='Courier'>UPDATE</font>)."
)
image_with_caption(
    SCREENSHOTS / "02_jaeger_trace_detail.png",
    "Figura 2. Jaeger UI — traza completa de extremo a extremo (service-a → service-b → PostgreSQL).",
)

h2("5.2. Verificación de propagación de contexto W3C TraceContext")
p(
    "Para la misma solicitud de prueba, el <code>trace_id</code> "
    "<font face='Courier'>93f978301e5105373a8a0c7e9ee7eb2e</font> generado por service-a aparece "
    "de forma nativa, sin ninguna correlación manual, tanto en Jaeger (23 spans de ambos "
    "servicios) como en los logs estructurados almacenados en Loki (7 líneas de log de ambos "
    "servicios, cada una con <font face='Courier'>trace_id</font>/<font face='Courier'>span_id</font> "
    "como metadata estructurada). El detalle completo de esta verificación — incluyendo los "
    "JSON crudos devueltos por las APIs de Jaeger y Loki — está documentado en "
    "<font face='Courier'>docs/w3c_trace_context_evidence.md</font>. Esto confirma que la "
    "cabecera <font face='Courier'>traceparent</font> (W3C Trace Context) se propaga "
    "correctamente entre servicios vía <font face='Courier'>opentelemetry-instrumentation-httpx</font> "
    "(inyección en el cliente) y <font face='Courier'>opentelemetry-instrumentation-fastapi</font> "
    "(extracción en el servidor)."
)

h2("5.3. Métricas en Prometheus y dashboard de Grafana")
p(
    "El dashboard de Grafana (<font face='Courier'>grafana/provisioning/dashboards/json/"
    "observabilidad-dashboard.json</font>) define 6 paneles — 4 SLIs de negocio, CPU del "
    "Collector y errores del Collector — cuyas consultas PromQL fueron validadas contra el "
    "Prometheus real de este entorno (todas devuelven datos, ver "
    "<font face='Courier'>benchmark/results/</font>). Las siguientes capturas muestran esas "
    "mismas consultas ejecutándose en la UI nativa de Prometheus, como evidencia de que el "
    "pipeline de métricas end-to-end (SDK → OTLP → Collector → exporter Prometheus → scrape) "
    "funciona; el archivo JSON del dashboard está listo para importarse en cualquier instancia "
    "de Grafana (ver limitación de entorno en la sección 7)."
)
data_table(
    ["#", "Panel", "Consulta PromQL (resumen)"],
    [
        ["1", "SLI 1 — Latencia p95/p99 de transferencias", "histogram_quantile(0.95/0.99, service_a_transfer_duration_seconds_bucket)"],
        ["2", "SLI 2 — Tasa de errores de negocio (%)", "rate(*_errors_total) / rate(*_total)"],
        ["3", "SLI 3 — Throughput (req/s)", "rate(service_a_transfers_total[1m]), rate(service_b_requests_total[1m])"],
        ["4", "SLI 4 — Disponibilidad de targets", "avg(up{job=~\"otel-collector.*\"}) * 100"],
        ["5", "CPU del OTel Collector", "rate(otelcol_process_cpu_seconds[1m]), otelcol_process_memory_rss"],
        ["6", "Errores del OTel Collector", "otelcol_receiver_refused_spans, otelcol_exporter_send_failed_*"],
    ],
    col_widths=[0.8 * cm, 5.4 * cm, 10.6 * cm],
)
image_with_caption(SCREENSHOTS / "05_prometheus_throughput.png", "Figura 3. Panel 3 (Throughput) — datos reales del tráfico de prueba, por endpoint de service-b.")
image_with_caption(SCREENSHOTS / "03_prometheus_p95_latencia.png", "Figura 4. Panel 1 (Latencia p95/p99) — pico real durante ráfaga de transferencias.")
image_with_caption(SCREENSHOTS / "09_prometheus_targets.png", "Figura 5. Ambos targets del Collector (métricas de app e internas) en estado UP.", max_height=6.5 * cm)

p(
    "<b>Correlación en Grafana Explore</b>: el datasource de Loki "
    "(<font face='Courier'>grafana/provisioning/datasources/datasources.yaml</font>) define un "
    "<i>derived field</i> que detecta el patrón <font face='Courier'>trace_id\"?[:=]...</font> en "
    "cada línea de log y genera automáticamente un enlace hacia la traza correspondiente en el "
    "datasource de Jaeger — el mismo mecanismo que se verificó manualmente en la sección 5.2, "
    "automatizado dentro de la UI de Grafana."
)

# ============================== 6. FASE 4 ==============================
h1("6. Fase 4 — Análisis de overhead")
h2("6.1. Metodología")
p(
    "Se ejecutó el mismo script de carga de k6 (<font face='Courier'>k6/transfer-load-test.js</font>) "
    "dos veces: una vez contra una versión de service-a/service-b <b>sin ningún import de "
    "OpenTelemetry</b> (<font face='Courier'>benchmark/service-{a,b}-baseline</font>, misma "
    "lógica de negocio exacta) y otra vez contra la versión instrumentada, ambas con un único "
    "worker de uvicorn por servicio para que la comparación aisle el efecto de la "
    "instrumentación. La carga sigue el patrón pedido por la consigna: rampa 0→50→100 VUs, "
    "sostenida en 100 VUs, con una duración total de 5 minutos, contra <code>POST /transfer</code>."
)
p(
    "Las cuentas se pre-cargaron con saldos de 10.000.000 en ambos escenarios para evitar que la "
    "propia prueba de carga generara errores de \"fondos insuficientes\" que sesgaran la "
    "comparación. Durante cada corrida se muestreó CPU% y memoria RSS de ambos procesos cada "
    "1 segundo con <font face='Courier'>psutil</font> "
    "(<font face='Courier'>benchmark/results/*_resources.csv</font>)."
)

h2("6.2. Resultados")
data_table(
    ["Métrica", "Sin instrumentación", "Con OTel", "Delta"],
    [
        ["Throughput sostenido", "157.25 req/s", "88.16 req/s", "-43.9 %"],
        ["Latencia media", "407.63 ms", "807.41 ms", "+98.1 %"],
        ["Latencia p95", "612.82 ms", "1172.05 ms", "+91.2 %"],
        ["Latencia p99", "674.47 ms", "1273.23 ms", "+88.8 % (+598.8 ms)"],
        ["CPU combinado promedio (2 procesos)", "107.6 %", "111.4 %", "+3.5 pp"],
        ["CPU máximo (proceso más cargado)", "76.0 %", "81.0 %", "+5.0 pp"],
        ["Memoria RSS combinada promedio", "158.6 MB", "213.8 MB", "+34.8 % (+55.2 MB)"],
        ["Requests completados en 5 min", "47,191", "26,451", "-43.9 %"],
    ],
    col_widths=[6.2 * cm, 3.6 * cm, 3.4 * cm, 3.6 * cm],
    keep_together=True,
)

h2("6.3. Interpretación")
p(
    "El overhead de <b>latencia</b> (p99 +88.8%) es desproporcionadamente mayor que el overhead "
    "de <b>CPU</b> (+3.5 puntos porcentuales), lo que indica que el cuello de botella no es "
    "cómputo bruto sino <b>espera de I/O</b> introducida por la instrumentación:"
)
bullets(
    [
        "<b>Sampling al 100%</b> (AlwaysOnSampler, valor por defecto del SDK): cada transferencia genera y exporta sus 23 spans sin ningún muestreo, multiplicando por 23 el volumen de datos serializados y encolados por request frente al caso base.",
        "<b>Auto-instrumentación de SQLAlchemy muy granular</b>: cada <font face='Courier'>SELECT</font>/<font face='Courier'>UPDATE</font>/<font face='Courier'>connect</font> genera su propio span.",
        "<b>Logs duplicados por OTLP</b>: además de stdout, cada línea de log de negocio se serializa y exporta también vía <font face='Courier'>BatchLogRecordProcessor</font> + <font face='Courier'>OTLPLogExporter</font>.",
        "<b>Un solo worker por servicio</b> (necesario para una comparación limpia): la cola de exportación OTLP compite por el mismo hilo/loop de eventos que atiende requests entrantes bajo 100 VUs concurrentes, amplificando la latencia observada.",
    ]
)
p("<b>Mitigaciones recomendadas para producción</b>:")
bullets(
    [
        "Reducir el sampling (p.ej. <font face='Courier'>TraceIdRatioBased(0.1)</font> o sampling basado en cola) en rutas de alto tráfico, reservando 100% para rutas críticas o trazas con error.",
        "Aumentar <font face='Courier'>send_batch_size</font> y ajustar el <font face='Courier'>timeout</font> del processor <font face='Courier'>batch</font>, tanto en el Collector como en los SDKs, para amortizar el costo de red por lote en vez de por span.",
        "Escalar horizontalmente los workers de uvicorn/gunicorn: el overhead relativo baja cuando el I/O de exportación se solapa con más capacidad de cómputo disponible.",
        "Evaluar exportar logs solo vía stdout + un agente de la plataforma (Cloud Logging/CloudWatch), en vez de duplicar la exportación también por OTLP, si el volumen de logs es alto.",
    ]
)

# ============================== 7. LIMITACIONES ==============================
h1("7. Limitaciones del entorno de desarrollo y decisiones de reproducibilidad")
p(
    "El entorno donde se desarrolló y ejecutó este proyecto tiene salida de red restringida a "
    "PyPI, npm, los mirrors de Ubuntu y descargas de <i>releases</i> de GitHub — bloqueando "
    "Docker Hub, GCR, Quay y el CDN propio de Grafana. Esto impidió ejecutar "
    "<font face='Courier'>docker compose up</font> directamente en ese entorno. Para no "
    "sacrificar la autenticidad de los datos presentados en este informe, se optó por: "
    "(1) mantener <font face='Courier'>docker-compose.yml</font> como el entregable oficial y "
    "portable, basado en imágenes estándar de Docker Hub, totalmente funcional en cualquier "
    "máquina con Docker e internet normal; y (2) para este informe, levantar un stack "
    "equivalente con binarios nativos descargados directamente de GitHub Releases (Jaeger, "
    "OTel Collector Contrib, Loki, k6) más PostgreSQL y Prometheus vía <font face='Courier'>apt</font>, "
    "de forma que todas las trazas, logs, métricas y resultados de benchmark mostrados son datos "
    "reales de una ejecución real, no ilustraciones."
)
p(
    "La única pieza que no fue posible ejecutar en ese entorno es <b>Grafana</b>: no está "
    "disponible como paquete <font face='Courier'>apt</font> en Ubuntu, no publica binarios "
    "precompilados en GitHub Releases (solo distribuye tarballs desde su propio CDN, "
    "<font face='Courier'>dl.grafana.com</font>, bloqueado), y compilarlo desde el código fuente "
    "requiere acceso al proxy de módulos de Go (<font face='Courier'>proxy.golang.org</font>, "
    "también bloqueado) y una build de frontend con Webpack de varios minutos. Se entrega, en su "
    "lugar, el <i>provisioning</i> completo de datasources y el dashboard JSON de 6 paneles "
    "(<font face='Courier'>grafana/provisioning/</font>), con todas sus consultas PromQL "
    "validadas contra el Prometheus real de este proyecto (sección 6.2 y "
    "<font face='Courier'>benchmark/results/</font>). Levantar "
    "<font face='Courier'>docker compose up -d</font> en una máquina con Docker estándar "
    "renderiza ese mismo dashboard con datos reales en menos de dos minutos."
)

# ============================== 8. CONCLUSIONES ==============================
h1("8. Conclusiones")
bullets(
    [
        "La instrumentación con el SDK de OTel (auto + spans custom) permitió reconstruir de forma completa y verificable el camino real de una transferencia entre dos microservicios y una base de datos, con un único <font face='Courier'>trace_id</font> consistente entre trazas y logs — confirmando que la propagación W3C TraceContext funciona de extremo a extremo sin intervención manual.",
        "Centralizar las tres señales en un único OTel Collector (receiver OTLP) simplifica el despliegue de los servicios (un solo endpoint de exportación) y desacopla la elección de backends (Jaeger/Prometheus/Loki hoy; Tempo/Cloud Trace/CloudWatch mañana) de una decisión de infraestructura, sin tocar código de aplicación.",
        "El overhead medido (p99 +88.8%, throughput -43.9%) es significativo y debe tenerse en cuenta al dimensionar servicios en producción; sin embargo, su origen (I/O de exportación con sampling al 100%, no CPU) apunta a mitigaciones concretas y de bajo riesgo (sampling, batching, más workers) antes de descartar la instrumentación completa.",
        "Separar el Collector (stateless, Cloud Run) de los backends con estado (Jaeger/Prometheus/Grafana, GKE vía Helm) es una decisión de arquitectura que reduce costo operativo sin sacrificar funcionalidad, y es replicable en AWS con ECS Fargate + EKS.",
    ]
)

# ============================== REFERENCIAS ==============================
h1("Referencias")
refs = [
    "OpenTelemetry. (s.f.). <i>Python SDK</i>. https://opentelemetry-python.readthedocs.io/",
    "Jaeger. (s.f.). <i>Architecture Documentation</i>. https://www.jaegertracing.io/docs/architecture/",
    "Grafana Labs. (s.f.). <i>Unified Observability: Linking Traces, Logs and Metrics</i>. https://grafana.com/docs/grafana/latest/explore/trace-integration/",
    "k6 (Grafana Labs). (s.f.). <i>Load Testing Documentation</i>. https://k6.io/docs/",
    "W3C. (s.f.). <i>Trace Context Specification</i>. https://www.w3.org/TR/trace-context/",
    "OpenTelemetry. (s.f.). <i>Collector Documentation</i>. https://opentelemetry.io/docs/collector/",
    "Google Cloud. (s.f.). <i>Cloud Run Documentation</i>. https://cloud.google.com/run/docs",
    "HashiCorp. (s.f.). <i>Terraform Google Provider</i>. https://registry.terraform.io/providers/hashicorp/google/latest/docs",
]
for r in refs:
    story.append(Paragraph(r, styles["BodySmall"]))

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=2.2 * cm,
    rightMargin=2.2 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
    title="Informe Técnico - Observabilidad con OpenTelemetry",
    author="Iván Vera",
)
doc.build(story)
print(f"PDF generado en {OUT}")
