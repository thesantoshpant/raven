const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

async function post(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json()).detail; } catch (_) {}
    throw new Error(detail || `${path} -> ${r.status}`);
  }
  return r.json();
}

export const api = {
  base: BASE,
  scenario: () => get("/api/scenario"),
  passports: () => get("/api/passports"),
  relay: () => get("/api/relay"),
  benchmark: () => post("/api/benchmark"),
  compress: (b) => post("/api/compress", b),
};
