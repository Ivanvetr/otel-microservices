"""Versión SIN instrumentación OTel de service-a (línea base para la Fase 4)."""
import logging
import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("service-a-baseline")

SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://localhost:8000")

app = FastAPI(title="service-a-baseline")
client = httpx.Client(base_url=SERVICE_B_URL, timeout=10.0)


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "service-a-baseline"}


@app.post("/transfer")
def transfer(req: TransferRequest):
    t0 = time.time()

    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    if req.from_account == req.to_account:
        raise HTTPException(status_code=400, detail="from_account and to_account must differ")

    try:
        debit_resp = client.post(
            f"/accounts/{req.from_account}/debit",
            json={"account_id": req.from_account, "amount": req.amount},
        )
        debit_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    try:
        credit_resp = client.post(
            f"/accounts/{req.to_account}/credit",
            json={"account_id": req.to_account, "amount": req.amount},
        )
        credit_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        client.post(
            f"/accounts/{req.from_account}/credit",
            json={"account_id": req.from_account, "amount": req.amount},
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    elapsed = time.time() - t0
    return {
        "status": "completed",
        "from_account": debit_resp.json(),
        "to_account": credit_resp.json(),
        "duration_seconds": elapsed,
    }
