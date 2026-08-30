#!/usr/bin/env python3
"""Genera el reporte ejecutivo PDF (Actividad 3 - Lab integrador) a partir de los datos y
capturas reales generadas en este proyecto: arquitectura completa (3 microservicios + AIOps +
network/security + chaos), evidencia de los 3 pilares y análisis de madurez de observabilidad.
"""
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
OUT = ROOT / "docs" / "Reporte_Ejecutivo_Actividad3.pdf"

CHAOS_LATENCY = json.loads((ROOT / "chaos" / "results" / "latency_mttd.json").read_text())
CHAOS_ERROR_RATE = json.loads((ROOT / "chaos" / "results" / "error_rate_mttd.json").read_text())

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=20, leading=26, spaceAfter=6))
styles.add(ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=13, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#0B3D91")))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#0B3D91")))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.2, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("BodySmall", parent=styles["Normal"], fontSize=9, leading=12.5, alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=14))
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


def image_with_caption(path, caption, max_width=16 * cm, max_height=9 * cm):
    from PIL import Image as PILImage

    im = PILImage.open(path)
    w, h = im.size
    ratio = min(max_width / w, max_height / h)
    story.append(Image(str(path), width=w * ratio, height=h * ratio))
    story.append(Paragraph(caption, styles["Caption"]))


def data_table(header, rows, col_widths=None, keep_together=False):
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
story.append(Spacer(1, 3.5 * cm))
story.append(Paragraph("Sistema de Observabilidad End-to-End con AIOps y Resiliencia", styles["TitleBig"]))
story.append(Paragraph("Arquitectura de tres microservicios, service mesh, AIOps, observabilidad de red/seguridad y chaos engineering — GCP y AWS", styles["SubTitle"]))
story.append(Spacer(1, 1.5 * cm))
story.append(Paragraph("Universidad de La Sabana — Maestría en Arquitectura de Software", styles["SubTitle"]))
story.append(Paragraph("Observabilidad en ambientes productivos — Lab integrador (Actividad 3)", styles["SubTitle"]))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph("Leonardo Pérez Ramírez — Ivan Felipe Vera Triana — Juan Felipe Gonzalez Ortiz", styles["SubTitle"]))
story.append(Spacer(1, 2.5 * cm))
story.append(Paragraph("30 de agosto de 2026", styles["SubTitle"]))
story.append(PageBreak())

# ============================== RESUMEN EJECUTIVO ==============================
h1("1. Resumen ejecutivo")
p(
    "Este reporte documenta la extensión de un sistema de observabilidad de dos microservicios "
    "(laboratorio 2.2) hacia una arquitectura de nivel producción con <b>tres microservicios</b>, "
    "<b>AIOps</b> (detección de anomalías con correlación de trazas), <b>observabilidad de red y "
    "seguridad</b>, y <b>dos experimentos de chaos engineering</b> validados con MTTD real. Todo "
    "el código de instrumentación, la infraestructura como código (Terraform para GCP y AWS) y "
    "los scripts de validación fueron implementados; la evidencia cuantitativa presentada en las "
    "secciones 4 a 7 proviene de una ejecución real del stack completo en Docker (30 de agosto de "
    "2026), no de datos ilustrativos."
)
p(
    "<b>Alcance real vs. documentado</b>: todo lo que requiere una cuenta de nube activa (Cloud "
    "SQL, RDS, service mesh gestionado, Cloud Monitoring Anomaly Detection, DevOps Guru, VPC Flow "
    "Logs, Security Command Center, Security Hub) quedó implementado como IaC completo en "
    "<font face='Courier'>terraform/</font>, gated por variables booleanas (<font face='Courier'>"
    "enable_data_service_databases</font>, <font face='Courier'>enable_network_security</font>, "
    "<font face='Courier'>enable_aiops</font>, todas en <font face='Courier'>false</font> por "
    "defecto), sin aplicar contra un proyecto/cuenta real. La evidencia funcional de cada módulo "
    "se generó 100% en local con Docker, replicando los mismos algoritmos y convenciones que se "
    "usarían en la nube real."
)
data_table(
    ["Módulo", "Resultado clave"],
    [
        ["A — Arquitectura observable", "3 microservicios con trazas distribuidas end-to-end; service mesh L7 (Envoy) con métricas reales de tráfico"],
        ["B — AIOps", "66.7% de reducción de alertas ruidosas (7 correlacionadas con trace_id vs. 21 de umbral estático)"],
        ["C — Network & Security", "Dashboard de seguridad con datos reales: 76 intentos de auth fallidos, tráfico N-S/E-W del mesh, 3 CVEs críticos por imagen (Trivy)"],
        ["D — Chaos Engineering", "Experimento de latencia: MTTD 26.7s (cumple). Experimento de error rate: MTTD 139.3s (no cumple, causa raíz identificada)"],
        ["E — Madurez", "Madurez promedio actual 2.9/5 sobre 8 dominios; roadmap accionable a 3 meses"],
    ],
    col_widths=[4.2 * cm, 12.6 * cm],
)

# ============================== ARQUITECTURA ==============================
h1("2. Arquitectura completa de la solución")
p(
    "La arquitectura extiende el flujo <i>service-a → service-b → PostgreSQL</i> del laboratorio "
    "anterior con un tercer microservicio, <b>data-service</b>, que persiste auditoría de cada "
    "transferencia en dos bases de datos gestionadas simuladas (Cloud SQL vía el contenedor "
    "<font face='Courier'>postgres</font>, RDS vía <font face='Courier'>postgres-aws</font>), "
    "instrumentado con OTel DB Semantic Conventions (<font face='Courier'>db.system</font>, "
    "<font face='Courier'>db.operation</font>) y atributos de nube "
    "(<font face='Courier'>cloud.provider</font>, <font face='Courier'>cloud.platform</font>). "
    "Todo el tráfico entre servicios pasa por sidecars Envoy (service mesh L7 local, equivalente "
    "a Cloud Service Mesh/AWS App Mesh), cuyas métricas de requests, retries y tráfico N-S/E-W se "
    "scrapean directamente por Prometheus."
)
data_table(
    ["Componente", "Rol"],
    [
        ["service-a", "Orquestador de transferencias; cliente de service-b y data-service vía los sidecars Envoy"],
        ["service-b", "Lógica de cuentas + PostgreSQL; toggle de chaos (+200ms de latencia)"],
        ["data-service", "Auditoría en Cloud SQL/RDS simulados; autenticación; toggle de chaos (10% error rate)"],
        ["envoy-service-b / envoy-data-service", "Sidecars del service mesh: métricas L7, access logs, retries"],
        ["aiops-anomaly-detector", "Baseline móvil + 2σ, correlación con trace_id, comparación vs. umbral estático"],
        ["Prometheus + Alertmanager + Pushgateway", "Métricas, reglas de alerta (SLO/estático) y CVEs (Trivy)"],
        ["OTel Collector + Jaeger + Loki + Grafana", "Pipeline unificado de los 3 pilares (heredado del lab 2.2)"],
    ],
    col_widths=[6.4 * cm, 10.4 * cm],
)

# ============================== MODULO A ==============================
h1("3. Módulo A — Arquitectura observable completa")
p(
    "Se validó la traza distribuida end-to-end a través de los 3 microservicios: cada "
    "<font face='Courier'>POST /transfer</font> genera una única traza con spans en "
    "<font face='Courier'>service-a</font>, <font face='Courier'>service-b</font> y "
    "<font face='Courier'>data-service</font> (31 spans por transacción), confirmando la "
    "propagación W3C TraceContext de extremo a extremo a través de los sidecars del mesh."
)
image_with_caption(
    SCREENSHOTS / "13_jaeger_trace_transfer_3_servicios.png",
    "Figura 1. Jaeger UI — trazas reales con los 3 microservicios (service-a, service-b, data-service).",
)
p(
    "El service mesh local (Envoy) fue corregido durante la validación: inicialmente "
    "<font face='Courier'>service-a</font> llamaba directo a los servicios backend, dejando los "
    "sidecars fuera de la ruta de tráfico real. Tras enrutar "
    "<font face='Courier'>SERVICE_B_URL</font>/<font face='Courier'>DATA_SERVICE_URL</font> hacia "
    "los sidecars, Prometheus confirmó tráfico real (~1.2 req/s) en las métricas nativas de Envoy."
)
image_with_caption(
    SCREENSHOTS / "17_prometheus_targets_actualizado.png",
    "Figura 2. Targets de Prometheus — sidecars Envoy, OTel Collector y Pushgateway, todos UP.",
    max_height=6 * cm,
)

# ============================== MODULO B ==============================
h1("4. Módulo B — AIOps: detección de anomalías y correlación")
p(
    "<font face='Courier'>aiops-anomaly-detector</font> implementa la regla pedida: "
    "<font face='Courier'>error_rate &gt; baseline_móvil + 2σ</font> Y "
    "<font face='Courier'>latency_p99 &gt; SLO</font> dispara una alerta enriquecida con el "
    "<font face='Courier'>trace_id</font> de un request fallido reciente (consultado vía la API "
    "de Jaeger), en paralelo a una regla de umbral estático clásica usada como comparación."
)
data_table(
    ["Métrica", "Valor real medido (30-ago-2026)"],
    [
        ["Alertas correlacionadas (AIOps)", "7"],
        ["Alertas de umbral estático (comparación)", "21"],
        ["Reducción de alertas ruidosas", "66.7 %"],
        ["Ejemplo de trace_id correlacionado", "e78fe7869c5c06bfe5ff04ea9d75918b"],
    ],
    col_widths=[8.4 * cm, 8.4 * cm],
)
image_with_caption(
    SCREENSHOTS / "14_jaeger_trace_correlacionada_aiops.png",
    "Figura 3. Traza con el span de error exacto (data_service.write_audit_record) al que apunta la alerta correlacionada del Módulo B.",
)

# ============================== MODULO C ==============================
h1("5. Módulo C — Network & Security Observability")
p(
    "El dashboard \"Golden Signals de Seguridad\" agrega tres señales con datos reales: intentos "
    "de autenticación fallidos (76 de 200 generados con "
    "<font face='Courier'>security/simulate_auth_traffic.py</font>), tráfico N-S/E-W medido en "
    "los sidecars Envoy del mesh, y CVEs activos por imagen obtenidos con un escaneo real de "
    "Trivy contra las 3 imágenes propias del proyecto."
)
data_table(
    ["Severidad", "CVEs por imagen (base python:3.11-slim)"],
    [
        ["CRITICAL", "3"],
        ["HIGH", "22"],
        ["MEDIUM", "68"],
        ["LOW", "77"],
    ],
    col_widths=[8.4 * cm, 8.4 * cm],
)
image_with_caption(
    SCREENSHOTS / "18_grafana_security_cves_completo.png",
    "Figura 4. Dashboard Golden Signals de Seguridad — auth, tráfico N-S/E-W y CVEs activos (datos reales).",
)
p(
    "VPC Flow Logs (GCP/AWS), Security Command Center y Security Hub quedan documentados como "
    "IaC completo en <font face='Courier'>terraform/network_security.tf</font> (gated por "
    "<font face='Courier'>enable_network_security</font>), pendientes de aplicar contra un "
    "proyecto/cuenta real."
)

# ============================== MODULO D ==============================
h1("6. Módulo D — Chaos Engineering controlado")
p(
    "Se ejecutaron los dos experimentos pedidos con <font face='Courier'>chaos/"
    "run_chaos_experiment.py</font>: inyección de fallo, generación de carga concurrente y "
    "medición del MTTD como el tiempo entre la inyección y la alerta de SLO correspondiente en "
    "Alertmanager."
)
data_table(
    ["Experimento", "Alerta esperada", "MTTD medido", "¿Cumple ≤120s?"],
    [
        ["1. Latencia +200ms en service-b", "TransferLatencySLOBreach", f"{CHAOS_LATENCY['mttd_seconds']:.1f}s", "Sí"],
        ["2. Error rate 10% en data-service", "DataServiceErrorRateSLOBreach", f"{CHAOS_ERROR_RATE['mttd_seconds']:.1f}s", "No (+19.3s)"],
    ],
    col_widths=[6.6 * cm, 6.2 * cm, 2.8 * cm, 2.6 * cm],
)
p(
    "<b>Análisis de la causa raíz del incumplimiento (experimento 2)</b>: "
    "<font face='Courier'>data-service</font> solo recibe una llamada de auditoría no crítica "
    "por cada transferencia, un volumen de tráfico bajo frente al endpoint "
    "<font face='Courier'>/transfer</font> de alto tráfico usado en el experimento 1. La ventana "
    "de <font face='Courier'>rate(...[1m])</font> combinada con <font face='Courier'>for: 30s</font> "
    "tarda más en reflejar el error inyectado cuando el volumen de requests es bajo. Se documentó "
    "como acción de mejora (Módulo E, roadmap mes 1) reducir la ventana de agregación o aumentar "
    "el tráfico sintético hacia data-service."
)
image_with_caption(
    SCREENSHOTS / "16_prometheus_alerting_rules.png",
    "Figura 5. Reglas de alerta de SLO y umbral estático cargadas en Prometheus.",
    max_height=7 * cm,
)
p(
    "Tanto el SLO de latencia como el de error rate se degradaron durante cada experimento "
    "(por diseño), consumiendo error budget mensual de forma medible: el experimento de error "
    "rate consumió aproximadamente 0.07% del error budget mensual de un SLO de disponibilidad "
    "del 99%, para una inyección de ~180 segundos. El detalle completo de esta cuantificación "
    "está en <font face='Courier'>chaos/chaos_experiments.md</font>."
)

# ============================== MODULO E ==============================
h1("7. Módulo E — Reporte de madurez de observabilidad")
p(
    "Autoevaluación contra el Observability Foundation Blueprint (8 dominios, escala 1-5). El "
    "detalle completo de la evidencia por dominio y el roadmap a 3 meses está en "
    "<font face='Courier'>docs/madurez_observabilidad.md</font>."
)
data_table(
    ["Dominio", "Nivel (1-5)"],
    [
        ["1. Tres pilares (traces/metrics/logs)", "4"],
        ["2. OpenTelemetry / instrumentación", "4"],
        ["3. AIOps (detección de anomalías)", "3"],
        ["4. Network Observability", "2"],
        ["5. Security Observability", "2"],
        ["6. DataOps", "3"],
        ["7. SRE (SLOs / error budgets / MTTD)", "3"],
        ["8. Cultura/Procesos", "2"],
    ],
    col_widths=[12 * cm, 4.8 * cm],
)
p("<b>Madurez promedio actual: 2.9 / 5.</b> Roadmap priorizado a 3 meses:")
bullets(
    [
        "<b>Mes 1</b>: cerrar la brecha de MTTD del experimento de error rate; aplicar Terraform de network/security contra un proyecto GCP y cuenta AWS de sandbox reales; escribir runbooks por alerta.",
        "<b>Mes 2</b>: reemplazar el baseline media+2σ por un modelo con estacionalidad (Holt-Winters/STL); implementar burn-rate alerting multiventana y política formal de error budget.",
        "<b>Mes 3</b>: versionar el esquema de métricas custom con retención diferenciada; sampling basado en cola (tail-based) en el Collector priorizando trazas con error/latencia alta.",
    ]
)

# ============================== CONCLUSIONES ==============================
h1("8. Conclusiones")
bullets(
    [
        "La arquitectura de 3 microservicios con service mesh local es completamente observable end-to-end: una sola traza permite reconstruir el camino de una transferencia a través de 2 saltos HTTP y 2 bases de datos, incluyendo los sidecars del mesh.",
        "La regla de correlación de AIOps (baseline+2σ + SLO + trace_id) demostró cuantitativamente su valor frente a umbrales estáticos: 66.7% menos alertas, cada una accionable con un enlace directo a la traza del fallo.",
        "Los experimentos de chaos engineering no solo validaron el sistema de alertas — revelaron un hallazgo real y accionable: el MTTD depende del volumen de tráfico del servicio afectado, no solo de la configuración de las reglas, un aprendizaje que solo pudo confirmarse ejecutando el experimento contra el stack real.",
        "Los dominios de observabilidad de red/seguridad en la nube real y de cultura/procesos organizacionales son los de menor madurez actual y los de mayor prioridad en el roadmap a 3 meses, ya que dependen de acceso a proyectos GCP/AWS reales más que de desarrollo adicional de código.",
    ]
)

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=2.2 * cm,
    rightMargin=2.2 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
    title="Reporte Ejecutivo - Sistema de Observabilidad con AIOps y Resiliencia (Actividad 3)",
    author="Leonardo Pérez Ramírez, Ivan Felipe Vera Triana, Juan Felipe Gonzalez Ortiz",
)
doc.build(story)
print(f"PDF generado en {OUT}")
