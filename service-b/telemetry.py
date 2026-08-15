"""
Configuración centralizada de OpenTelemetry para service-b.

Emite los 3 pilares de la observabilidad:
  - Trazas -> OTLP gRPC -> OTel Collector -> Jaeger
  - Métricas -> endpoint /metrics en formato Prometheus (scrape directo)
  - Logs -> JSON estructurado a stdout (con trace_id/span_id) + OTLP -> Collector -> Loki
"""
import logging
import os
import sys

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pythonjsonlogger import jsonlogger

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "service-b")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "local")
OTEL_COLLECTOR_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

resource = Resource.create(
    {
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "deployment.environment": DEPLOYMENT_ENV,
    }
)


def setup_tracing() -> trace.Tracer:
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTEL_COLLECTOR_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


def setup_metrics() -> metrics.Meter:
    # Métricas -> OTLP -> OTel Collector -> exporter Prometheus (endpoint /metrics del Collector)
    exporter = OTLPMetricExporter(endpoint=OTEL_COLLECTOR_ENDPOINT, insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(SERVICE_NAME)


class OtelJsonFormatter(jsonlogger.JsonFormatter):
    """Formatter JSON que añade trace_id/span_id inyectados por LoggingInstrumentor."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["service.name"] = SERVICE_NAME
        log_record["level"] = record.levelname
        trace_id = getattr(record, "otelTraceID", "0")
        span_id = getattr(record, "otelSpanID", "0")
        # Formato hex de 32/16 chars, consistente con W3C trace-context,
        # para poder correlacionar directamente con Jaeger/Grafana.
        log_record["trace_id"] = trace_id
        log_record["span_id"] = span_id


def setup_logging():
    LoggingInstrumentor().instrument(set_logging_format=False)

    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=OTEL_COLLECTOR_ENDPOINT, insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    otlp_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(OtelJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(otlp_handler)
    root.addHandler(stdout_handler)

    return logging.getLogger(SERVICE_NAME)


tracer = setup_tracing()
meter = setup_metrics()
log = setup_logging()
