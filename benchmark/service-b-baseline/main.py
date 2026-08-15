"""
Versión SIN instrumentación OTel de service-b, usada únicamente como línea
base para el análisis de overhead de la Fase 4. Misma lógica de negocio que
service-b/main.py, sin auto-instrumentación HTTP/DB, sin spans, sin métricas
OTel y sin exportación de logs vía OTLP (solo logging estándar a stdout).
"""
import logging
import os
import random
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("service-b-baseline")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://otel:otel@localhost:5432/otel_bench_baseline"
)

app = FastAPI(title="service-b-baseline")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


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
        for acc_id, balance in [("acc-001", 10_000_000.00), ("acc-002", 10_000_000.00), ("acc-003", 10_000_000.00)]:
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (account_id, balance) VALUES (:id, :bal)
                    ON CONFLICT (account_id) DO UPDATE SET balance = :bal
                    """
                ),
                {"id": acc_id, "bal": balance},
            )


@app.on_event("startup")
def on_startup():
    init_db()
    log.info("service-b-baseline iniciado y base de datos lista")


class DebitRequest(BaseModel):
    account_id: str
    amount: float


class BalanceResponse(BaseModel):
    account_id: str
    balance: float
    fee_adjusted_balance: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "service-b-baseline"}


@app.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
def get_balance(account_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT balance FROM accounts WHERE account_id = :id"), {"id": account_id}
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="account not found")

    balance = float(row[0])
    fee_rate = 0.001 if balance > 1000 else 0.0
    fee_adjusted = round(balance * (1 - fee_rate), 2)
    return BalanceResponse(account_id=account_id, balance=balance, fee_adjusted_balance=fee_adjusted)


@app.post("/accounts/{account_id}/debit")
def debit_account(account_id: str, req: DebitRequest):
    time.sleep(random.uniform(0.005, 0.02))

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT balance FROM accounts WHERE account_id = :id FOR UPDATE"), {"id": account_id}
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="account not found")

        balance = float(row[0])
        if balance < req.amount:
            raise HTTPException(status_code=422, detail="insufficient funds")

        new_balance = balance - req.amount
        conn.execute(
            text("UPDATE accounts SET balance = :bal WHERE account_id = :id"),
            {"bal": new_balance, "id": account_id},
        )
    return {"account_id": account_id, "new_balance": new_balance}


@app.post("/accounts/{account_id}/credit")
def credit_account(account_id: str, req: DebitRequest):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT balance FROM accounts WHERE account_id = :id FOR UPDATE"), {"id": account_id}
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="account not found")

        new_balance = float(row[0]) + req.amount
        conn.execute(
            text("UPDATE accounts SET balance = :bal WHERE account_id = :id"),
            {"bal": new_balance, "id": account_id},
        )
    return {"account_id": account_id, "new_balance": new_balance}
