import http from "k6/http";
import { check, sleep } from "k6";

// Carga realista pedida por la consigna: 50-100 usuarios concurrentes, 5 minutos.
export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "30s", target: 100 },
    { duration: "3m", target: 100 },
    { duration: "30s", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

const accounts = ["acc-001", "acc-002", "acc-003"];
const TARGET_URL = __ENV.TARGET_URL || "http://localhost:8001";

export default function () {
  const from = accounts[Math.floor(Math.random() * accounts.length)];
  let to = accounts[Math.floor(Math.random() * accounts.length)];
  while (to === from) {
    to = accounts[Math.floor(Math.random() * accounts.length)];
  }
  const amount = Math.round((Math.random() * 50 + 1) * 100) / 100;

  const payload = JSON.stringify({ from_account: from, to_account: to, amount: amount });
  const res = http.post(`${TARGET_URL}/transfer`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "status 200": (r) => r.status === 200 });
  sleep(0.1);
}
