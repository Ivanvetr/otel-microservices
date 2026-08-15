import os
import random
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import Status, StatusCode

from telemetry import tracer, meter, log

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://otel:otel@postgres:5432/otel_demo"
)

app = FastAPI(title="service-b")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- auto-instrumentación HTTP (servidor) y DB ---
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)

# --- métricas custom ---
request_counter = meter.create_counter(
    "service_b_requests_total", description="Total de requests recibidos por service-b"
)
error_counter = meter.create_counter(
    "service_b_errors_total", description="Total de errores de negocio en service-b"
)
db_latency_hist = meter.create_histogram(
    "service_b_db_query_duration_seconds", description="Duración de consultas a la base de datos"
)
debit_amount_hist = meter.create_histogram(
    "service_b_debit_amount", description="Monto de los débitos procesados"
)


def init_db():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id VARCHAR(32) PRIMARY KEY,
                    balance NUMERIC(14, 2) NOT NULL
                )
                """
            )
        )
        for acc_id, balance in [("acc-001", 5000.00), ("acc-002", 1200.00), ("acc-003", 300.00)]:
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (account_id, balance) VALUES (:id, :bal)
                    ON CONFLICT (account_id) DO NOTHING
                    """
                ),
                {"id": acc_id, "bal": balance},
            )


@app.on_event("startup")
def on_startup():
    init_db()
    log.info("service-b iniciado y base de datos lista")


class DebitRequest(BaseModel):
    account_id: str
    amount: float


class BalanceResponse(BaseModel):
    account_id: str
    balance: float
    fee_adjusted_balance: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "service-b"}


@app.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
def get_balance(account_id: str):
    request_counter.add(1, {"endpoint": "get_balance"})

    with tracer.start_as_current_span("calculate_balance_with_fees") as span:
        span.set_attribute("account.id", account_id)

        t0 = time.time()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT balance FROM accounts WHERE account_id = :id"),
                {"id": account_id},
            ).fetchone()
        db_latency_hist.record(time.time() - t0, {"query": "select_balance"})

        if row is None:
            span.set_status(Status(StatusCode.ERROR, "account not found"))
            error_counter.add(1, {"endpoint": "get_balance", "reason": "not_found"})
            log.warning("cuenta no encontrada", extra={"account_id": account_id})
            raise HTTPException(status_code=404, detail="account not found")

        balance = float(row[0])

        # --- lógica de negocio crítica: cálculo de comisión de mantenimiento ---
        fee_rate = 0.001 if balance > 1000 else 0.0
        fee_adjusted = round(balance * (1 - fee_rate), 2)
        span.set_attribute("account.balance", balance)
        span.set_attribute("account.fee_rate", fee_rate)

        log.info(
            "balance calculado",
            extra={"account_id": account_id, "balance": balance, "fee_adjusted": fee_adjusted},
        )
        return BalanceResponse(
            account_id=account_id, balance=balance, fee_adjusted_balance=fee_adjusted
        )


@app.post("/accounts/{account_id}/debit")
def debit_account(account_id: str, req: DebitRequest):
    request_counter.add(1, {"endpoint": "debit_account"})

    with tracer.start_as_current_span("apply_debit_business_rules") as span:
        span.set_attribute("account.id", account_id)
        span.set_attribute("debit.amount", req.amount)

        # simula variabilidad de carga real en la capa de negocio
        time.sleep(random.uniform(0.005, 0.02))

        t0 = time.time()
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT balance FROM accounts WHERE account_id = :id FOR UPDATE"),
                {"id": account_id},
            ).fetchone()

            if row is None:
                span.set_status(Status(StatusCode.ERROR, "account not found"))
                error_counter.add(1, {"endpoint": "debit_account", "reason": "not_found"})
                raise HTTPException(status_code=404, detail="account not found")

            balance = float(row[0])
            if balance < req.amount:
                span.set_status(Status(StatusCode.ERROR, "insufficient funds"))
                error_counter.add(1, {"endpoint": "debit_account", "reason": "insufficient_funds"})
                log.warning(
                    "fondos insuficientes",
                    extra={"account_id": account_id, "balance": balance, "amount": req.amount},
                )
                raise HTTPException(status_code=422, detail="insufficient funds")

            new_balance = balance - req.amount
            conn.execute(
                text("UPDATE accounts SET balance = :bal WHERE account_id = :id"),
                {"bal": new_balance, "id": account_id},
            )
        db_latency_hist.record(time.time() - t0, {"query": "debit_update"})
        debit_amount_hist.record(req.amount, {"account_id": account_id})

        log.info(
            "débito aplicado",
            extra={"account_id": account_id, "amount": req.amount, "new_balance": new_balance},
        )
        return {"account_id": account_id, "new_balance": new_balance}


@app.post("/accounts/{account_id}/credit")
def credit_account(account_id: str, req: DebitRequest):
    request_counter.add(1, {"endpoint": "credit_account"})

    with tracer.start_as_current_span("apply_credit_business_rules") as span:
        span.set_attribute("account.id", account_id)
        span.set_attribute("credit.amount", req.amount)

        t0 = time.time()
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT balance FROM accounts WHERE account_id = :id FOR UPDATE"),
                {"id": account_id},
            ).fetchone()

            if row is None:
                span.set_status(Status(StatusCode.ERROR, "account not found"))
                error_counter.add(1, {"endpoint": "credit_account", "reason": "not_found"})
                raise HTTPException(status_code=404, detail="account not found")

            new_balance = float(row[0]) + req.amount
            conn.execute(
                text("UPDATE accounts SET balance = :bal WHERE account_id = :id"),
                {"bal": new_balance, "id": account_id},
            )
        db_latency_hist.record(time.time() - t0, {"query": "credit_update"})

        log.info(
            "crédito aplicado",
            extra={"account_id": account_id, "amount": req.amount, "new_balance": new_balance},
        )
        return {"account_id": account_id, "new_balance": new_balance}
