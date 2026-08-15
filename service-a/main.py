import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode

from telemetry import tracer, meter, log

SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://service-b:8000")

app = FastAPI(title="service-a")

# --- auto-instrumentación HTTP: servidor (FastAPI) + cliente saliente (httpx) ---
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

client = httpx.Client(base_url=SERVICE_B_URL, timeout=10.0)

# --- métricas custom ---
transfer_counter = meter.create_counter(
    "service_a_transfers_total", description="Total de transferencias procesadas"
)
transfer_error_counter = meter.create_counter(
    "service_a_transfer_errors_total", description="Total de transferencias fallidas"
)
transfer_latency_hist = meter.create_histogram(
    "service_a_transfer_duration_seconds", description="Duración total de una transferencia"
)


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "service-a"}


@app.post("/transfer")
def transfer(req: TransferRequest):
    t0 = time.time()

    # --- lógica de negocio crítica: validación de la transferencia ---
    with tracer.start_as_current_span("validate_transfer_request") as span:
        span.set_attribute("transfer.from_account", req.from_account)
        span.set_attribute("transfer.to_account", req.to_account)
        span.set_attribute("transfer.amount", req.amount)

        if req.amount <= 0:
            span.set_status(Status(StatusCode.ERROR, "invalid amount"))
            transfer_error_counter.add(1, {"reason": "invalid_amount"})
            raise HTTPException(status_code=400, detail="amount must be positive")
        if req.from_account == req.to_account:
            span.set_status(Status(StatusCode.ERROR, "same account"))
            transfer_error_counter.add(1, {"reason": "same_account"})
            raise HTTPException(status_code=400, detail="from_account and to_account must differ")

    log.info(
        "iniciando transferencia",
        extra={
            "from_account": req.from_account,
            "to_account": req.to_account,
            "amount": req.amount,
        },
    )

    # --- dependencia HTTP hacia service-b (propagación W3C TraceContext automática) ---
    try:
        debit_resp = client.post(
            f"/accounts/{req.from_account}/debit",
            json={"account_id": req.from_account, "amount": req.amount},
        )
        debit_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        transfer_error_counter.add(1, {"reason": "debit_failed"})
        log.error(
            "fallo al debitar la cuenta origen",
            extra={"from_account": req.from_account, "status_code": e.response.status_code},
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    try:
        credit_resp = client.post(
            f"/accounts/{req.to_account}/credit",
            json={"account_id": req.to_account, "amount": req.amount},
        )
        credit_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        # compensación simple: revertir el débito si el crédito falla
        client.post(
            f"/accounts/{req.from_account}/credit",
            json={"account_id": req.from_account, "amount": req.amount},
        )
        transfer_error_counter.add(1, {"reason": "credit_failed_rolled_back"})
        log.error(
            "fallo al acreditar la cuenta destino, transferencia revertida",
            extra={"to_account": req.to_account, "status_code": e.response.status_code},
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    elapsed = time.time() - t0
    transfer_counter.add(1)
    transfer_latency_hist.record(elapsed)

    log.info(
        "transferencia completada",
        extra={
            "from_account": req.from_account,
            "to_account": req.to_account,
            "amount": req.amount,
            "duration_seconds": elapsed,
        },
    )
    return {
        "status": "completed",
        "from_account": debit_resp.json(),
        "to_account": credit_resp.json(),
        "duration_seconds": elapsed,
    }
