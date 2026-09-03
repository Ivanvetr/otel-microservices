"""data-service: tercer microservicio del Módulo A.

Simula acceso a dos bases de datos gestionadas en dos nubes distintas:
- "GCP Cloud SQL"  -> engine `cloudsql_engine` (Postgres, contenedor `postgres`)
- "AWS RDS"        -> engine `rds_engine` (Postgres, contenedor `postgres-aws`)

Localmente ambas son instancias Postgres en Docker (no hay costo/cuenta en la nube real);
la separación de engines + los atributos `cloud.provider`/`cloud.platform` en los spans
dejan explícito qué llamada corresponde a cada proveedor, de cara al Terraform real en
`terraform/cloudsql.tf` y `terraform/rds.tf` que sí aprovisionaría las instancias gestionadas.

Expone además endpoints de autenticación (Módulo C, golden signals de seguridad) y un
interruptor de inyección de fallos (Módulo D, chaos engineering).
"""
import os
import random
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode

from telemetry import tracer, meter, log

CLOUDSQL_DATABASE_URL = os.getenv(
    "CLOUDSQL_DATABASE_URL", "postgresql+psycopg2://otel:otel@postgres:5432/otel_demo"
)
RDS_DATABASE_URL = os.getenv(
    "RDS_DATABASE_URL", "postgresql+psycopg2://otel:otel@postgres-aws:5432/rds_demo"
)
VALID_USER = os.getenv("DATA_SERVICE_VALID_USER", "admin")
VALID_PASSWORD = os.getenv("DATA_SERVICE_VALID_PASSWORD", "s3cret")

app = FastAPI(title="data-service")
cloudsql_engine = create_engine(CLOUDSQL_DATABASE_URL, pool_pre_ping=True)
rds_engine = create_engine(RDS_DATABASE_URL, pool_pre_ping=True)

# --- auto-instrumentación HTTP (servidor) y DB (una instrumentación por engine/nube) ---
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=cloudsql_engine)
SQLAlchemyInstrumentor().instrument(engine=rds_engine)

ENGINES = {"gcp": cloudsql_engine, "aws": rds_engine}
CLOUD_PLATFORM = {"gcp": "gcp_cloud_sql", "aws": "aws_rds"}

# --- métricas custom ---
request_counter = meter.create_counter("data_service_requests_total")
error_counter = meter.create_counter("data_service_errors_total")
request_latency_hist = meter.create_histogram("data_service_request_duration_seconds")
db_latency_hist = meter.create_histogram("data_service_db_query_duration_seconds")
auth_failed_counter = meter.create_counter(
    "data_service_auth_failed_total", description="Intentos de autenticación fallidos (golden signal de seguridad)"
)
auth_success_counter = meter.create_counter("data_service_auth_success_total")
chaos_injected_counter = meter.create_counter(
    "data_service_chaos_injected_errors_total", description="Errores inyectados artificialmente por el experimento de caos"
)

# --- estado del experimento de caos (Módulo D): error rate configurable en runtime ---
CHAOS_STATE = {"error_rate_enabled": False, "error_rate": 0.0}


def init_db(engine, provider: str):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    record_id SERIAL PRIMARY KEY,
                    account_id VARCHAR(32) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    amount NUMERIC(14, 2),
                    cloud_provider VARCHAR(16) NOT NULL,
                    created_at TIMESTAMP DEFAULT now()
                )
                """
            )
        )
    log.info(f"data-service: tabla audit_log lista en {provider}")


@app.on_event("startup")
def on_startup():
    init_db(cloudsql_engine, "gcp-cloudsql-sim")
    init_db(rds_engine, "aws-rds-sim")
    log.info("data-service iniciado con dos backends de base de datos (gcp/aws)")


class AuditRecord(BaseModel):
    account_id: str
    event_type: str
    amount: float | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-service"}


def _maybe_inject_chaos_error():
    """Inyección de fallos controlada para el experimento de caos del Módulo D."""
    if CHAOS_STATE["error_rate_enabled"] and random.random() < CHAOS_STATE["error_rate"]:
        chaos_injected_counter.add(1)
        raise HTTPException(status_code=500, detail="chaos-injected: simulated data-service failure")


@app.post("/records/{provider}")
def create_record(provider: str, record: AuditRecord):
    if provider not in ENGINES:
        raise HTTPException(status_code=400, detail="provider must be 'gcp' or 'aws'")

    request_counter.add(1, {"provider": provider, "endpoint": "create_record"})
    t0 = time.time()

    with tracer.start_as_current_span("data_service.write_audit_record") as span:
        # --- OTel DB Semantic Conventions + atributos de nube (cloud.provider/cloud.platform) ---
        span.set_attribute(SpanAttributes.DB_SYSTEM, "postgresql")
        span.set_attribute(SpanAttributes.DB_NAME, "otel_demo" if provider == "gcp" else "rds_demo")
        span.set_attribute(SpanAttributes.DB_OPERATION, "INSERT")
        span.set_attribute("cloud.provider", provider)
        span.set_attribute("cloud.platform", CLOUD_PLATFORM[provider])
        span.set_attribute("account.id", record.account_id)

        try:
            _maybe_inject_chaos_error()

            db_t0 = time.time()
            with ENGINES[provider].begin() as conn:
                row = conn.execute(
                    text(
                        """
                        INSERT INTO audit_log (account_id, event_type, amount, cloud_provider)
                        VALUES (:account_id, :event_type, :amount, :provider)
                        RETURNING record_id
                        """
                    ),
                    {
                        "account_id": record.account_id,
                        "event_type": record.event_type,
                        "amount": record.amount,
                        "provider": provider,
                    },
                ).fetchone()
            db_latency_hist.record(time.time() - db_t0, {"provider": provider, "query": "insert_audit"})
        except HTTPException:
            span.set_status(Status(StatusCode.ERROR, "chaos-injected failure"))
            error_counter.add(1, {"provider": provider, "reason": "chaos_injected"})
            raise
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            error_counter.add(1, {"provider": provider, "reason": "db_error"})
            raise HTTPException(status_code=500, detail="database error") from exc

        request_latency_hist.record(time.time() - t0, {"provider": provider})
        log.info(
            "registro de auditoría creado",
            extra={"provider": provider, "account_id": record.account_id, "record_id": row[0]},
        )
        return {"record_id": row[0], "provider": provider}


@app.get("/records/{provider}/{record_id}")
def get_record(provider: str, record_id: int):
    if provider not in ENGINES:
        raise HTTPException(status_code=400, detail="provider must be 'gcp' or 'aws'")

    request_counter.add(1, {"provider": provider, "endpoint": "get_record"})

    with tracer.start_as_current_span("data_service.read_audit_record") as span:
        span.set_attribute(SpanAttributes.DB_SYSTEM, "postgresql")
        span.set_attribute(SpanAttributes.DB_OPERATION, "SELECT")
        span.set_attribute("cloud.provider", provider)
        span.set_attribute("cloud.platform", CLOUD_PLATFORM[provider])

        t0 = time.time()
        with ENGINES[provider].connect() as conn:
            row = conn.execute(
                text("SELECT record_id, account_id, event_type, amount, created_at FROM audit_log WHERE record_id = :id"),
                {"id": record_id},
            ).fetchone()
        db_latency_hist.record(time.time() - t0, {"provider": provider, "query": "select_audit"})

        if row is None:
            span.set_status(Status(StatusCode.ERROR, "record not found"))
            error_counter.add(1, {"provider": provider, "reason": "not_found"})
            raise HTTPException(status_code=404, detail="record not found")

        return {
            "record_id": row[0],
            "account_id": row[1],
            "event_type": row[2],
            "amount": float(row[3]) if row[3] is not None else None,
            "created_at": str(row[4]),
        }


@app.post("/auth/login")
def login(req: LoginRequest):
    """Endpoint sintético para alimentar el golden signal 'intentos de autenticación fallidos'."""
    with tracer.start_as_current_span("data_service.authenticate") as span:
        span.set_attribute("auth.username", req.username)

        if req.username == VALID_USER and req.password == VALID_PASSWORD:
            auth_success_counter.add(1)
            span.set_status(Status(StatusCode.OK))
            log.info("autenticación exitosa", extra={"username": req.username})
            return {"status": "authenticated"}

        auth_failed_counter.add(1, {"username": req.username})
        span.set_status(Status(StatusCode.ERROR, "invalid credentials"))
        log.warning("intento de autenticación fallido", extra={"username": req.username})
        raise HTTPException(status_code=401, detail="invalid credentials")


class ChaosConfig(BaseModel):
    enabled: bool
    error_rate: float = 0.1


@app.post("/chaos/error-rate")
def set_chaos_error_rate(config: ChaosConfig):
    """Interruptor del experimento de caos #2 (Módulo D): error rate configurable en data-service."""
    CHAOS_STATE["error_rate_enabled"] = config.enabled
    CHAOS_STATE["error_rate"] = config.error_rate
    log.warning("chaos toggle actualizado", extra=dict(CHAOS_STATE))
    return dict(CHAOS_STATE)


@app.get("/chaos/status")
def get_chaos_status():
    return dict(CHAOS_STATE)
