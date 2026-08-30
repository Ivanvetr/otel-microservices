"""security/simulate_auth_traffic.py — genera tráfico de autenticación (éxitos y fallos)
contra data-service, para alimentar el golden signal 'intentos de autenticación fallidos'
del dashboard de seguridad (Módulo C).

Uso:
    python security/simulate_auth_traffic.py --target http://localhost:8003 --requests 200 --fail-rate 0.4
"""
import argparse
import random
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="http://localhost:8003")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--fail-rate", type=float, default=0.4)
    parser.add_argument("--sleep", type=float, default=0.1)
    args = parser.parse_args()

    ok, failed = 0, 0
    for _ in range(args.requests):
        use_valid = random.random() > args.fail_rate
        payload = {
            "username": "admin" if use_valid else "attacker",
            "password": "s3cret" if use_valid else "wrong-password",
        }
        resp = requests.post(f"{args.target}/auth/login", json=payload, timeout=5)
        if resp.status_code == 200:
            ok += 1
        else:
            failed += 1
        time.sleep(args.sleep)

    print(f"Autenticaciones exitosas: {ok} | fallidas: {failed} (fail-rate objetivo: {args.fail_rate})")


if __name__ == "__main__":
    main()
