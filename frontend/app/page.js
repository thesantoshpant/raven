"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function Highlighted({ text, phrases }) {
  const list = (phrases || []).filter(Boolean).slice().sort((a, b) => b.length - a.length);
  if (!list.length) return <>{text}</>;
  const re = new RegExp(`(${list.map(escapeRe).join("|")})`, "gi");
  const low = new Set(list.map((p) => p.toLowerCase()));
  const parts = String(text).split(re);
  return (
    <>
      {parts.map((p, i) =>
        low.has(p.toLowerCase()) ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>
      )}
    </>
  );
}

function MemoryPane({ scenario }) {
  if (!scenario) return <div className="panel"><h2>User memory</h2><div className="muted">loading…</div></div>;
  const phrases = scenario.highlights || [];
  const hasGold = (t) => phrases.some((p) => t.toLowerCase().includes(p.toLowerCase()));
  return (
    <div className="panel">
      <h2>User memory <span className="count">{scenario.counts.items} items · {scenario.counts.facts} facts</span></h2>
      <div className="muted" style={{ marginBottom: 10 }}>Everything you&apos;d dump into an agent. The 5 decision-critical facts are buried (highlighted).</div>
      <div className="memlist">
        {scenario.memory_items.map((it) => (
          <div key={it.id} className={"memitem" + (hasGold(it.text) ? " gold" : "")}>
            <span className="kind">{it.kind}</span>{" · "}
            <Highlighted text={it.text} phrases={phrases} />
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentsPane({ passports, error }) {
  const [open, setOpen] = useState(null);
  if (!passports) return <div className="panel"><h2>Agents · passports</h2><div className="muted">{error ? "⚠ " + error : "loading…"}</div></div>;
  return (
    <div className="panel">
      <h2>Agents · recipient-aware passports</h2>
      <div className="muted" style={{ marginBottom: 10 }}>
        Raw: every agent gets all {passports.n_facts} facts (~{passports.full_tokens} tok). RAVEN: each gets only its slice.
      </div>
      {passports.roles.map((r) => (
        <div key={r.role} className={"agentcard" + (open === r.role ? " open" : "")} onClick={() => setOpen(open === r.role ? null : r.role)}>
          <div className="row">
            <span className="role">{r.role}</span>
            <span className="pill">{r.tokens} tok · −{r.saved_pct}%</span>
          </div>
          <div className="sub">sees {r.facts.length} facts · denied {r.excluded_count} · ~${r.est_usd_per_send}/send</div>
          {open === r.role && (
            <div className="passport">
              {r.facts.map((f, i) => (
                <div className="fact" key={i}><span className="ftype">{f.type}</span>{f.text}</div>
              ))}
              <pre style={{ marginTop: 8 }}>{r.passport_text}</pre>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Meter({ passports, error }) {
  if (!passports) return <div className="muted">{error ? "⚠ " + error : "loading…"}</div>;
  const n = passports.roles.length || 1;
  const rawBroadcast = passports.full_tokens * n;
  const ravenTotal = passports.roles.reduce((a, r) => a + r.tokens, 0);
  const savedPct = rawBroadcast ? Math.round((1 - ravenTotal / rawBroadcast) * 100) : 0;
  const ravenW = Math.max(6, Math.round((ravenTotal / rawBroadcast) * 100));
  return (
    <div className="meter">
      <div className="bar label">Raw — full memory to all {n} agents (incl. summarizer)</div>
      <div className="bar raw" style={{ width: "100%" }}>{rawBroadcast.toLocaleString()} tok</div>
      <div className="bar label" style={{ marginTop: 10 }}>RAVEN — tailored passports</div>
      <div className="bar raven" style={{ width: ravenW + "%" }}>{ravenTotal.toLocaleString()} tok</div>
      <div style={{ marginTop: 14 }}>
        <span className="bigstat good">{savedPct}%</span>
        <span className="statline"> fewer context tokens delivered across the workflow</span>
      </div>
    </div>
  );
}

function Benchmark() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const run = async () => {
    setLoading(true); setErr(null);
    try { setData(await api.benchmark()); }
    catch (e) { setErr(e.message || "benchmark failed"); }
    finally { setLoading(false); }
  };

  const order = ["raw", "generic", "raven"];
  const labels = { raw: "raw (full)", generic: "generic", raven: "RAVEN" };
  return (
    <div>
      <button className="btn" onClick={run} disabled={loading}>
        {loading ? <><span className="spinner" />agents deciding…</> : "▶ Run decision benchmark (live)"}
      </button>
      {err && <div className="toast">⚠ {err}</div>}
      {data && (
        <div className="result">
          {order.map((c) => {
            const d = data.conditions[c];
            if (!d) return null;
            const full = d.constraints === d.total;
            return (
              <div className={"cond" + (c === "raven" ? " raven" : "")} key={c}>
                <span className="name">{labels[c]}</span>
                <span>
                  <span className={"score " + (full ? "full" : "partial")}>{d.constraints}/{d.total}</span>
                  {d.missed.length > 0 && <div className="missed">missed: {d.missed.join(", ")}</div>}
                </span>
                <span className="toks">{d.agent_tokens.toLocaleString()} tok<br />~${d.est_usd}</span>
              </div>
            );
          })}
          <div className="note">
            RAVEN matches raw&apos;s decision quality at a fraction of the recurring cost; generic, at the
            same per-agent budget ({data.per_agent_budget} tok), drops the standing &quot;confirm before paying&quot; rule.
            <br />$ is a rough estimate; tokens are the real metric.
          </div>
        </div>
      )}
    </div>
  );
}

function RelayView({ relay, error }) {
  if (!relay) return <div className="panel"><div className="muted">{error ? "⚠ " + error : "loading…"}</div></div>;
  const t = relay.totals;
  const pr = relay.preservation;
  return (
    <div className="panel">
      <h2>RELAY — agent → agent handoff compression</h2>
      <div className="muted" style={{ marginBottom: 12 }}>
        At each handoff, forward the upstream message + a recipient-aware compressed passport of the
        back-context — instead of the whole growing transcript.
      </div>
      <table className="relay">
        <thead><tr><th>hop</th><th>full transcript</th><th>last message</th><th>RAVEN relay</th><th>vs full</th></tr></thead>
        <tbody>
          {relay.hops.map((h) => (
            <tr key={h.to_role}>
              <td>→ {h.to_role}</td>
              <td>{h.full.toLocaleString()}</td>
              <td>{h.last_message.toLocaleString()}</td>
              <td>{h.relay.toLocaleString()}</td>
              <td>{h.saved_vs_full_pct}%</td>
            </tr>
          ))}
          <tr className="total">
            <td>TOTAL</td>
            <td>{t.full.toLocaleString()}</td>
            <td>{t.last_message.toLocaleString()}</td>
            <td>{t.relay.toLocaleString()}</td>
            <td>{t.saved_vs_full_pct}%</td>
          </tr>
        </tbody>
      </table>
      <div style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <span className="badge good">RAVEN keeps &quot;{pr.probe}&quot; on {pr.relay_keeps}/{pr.hops} hops</span>
        <span className="badge bad">last-message keeps it on only {pr.last_keeps}/{pr.hops}</span>
      </div>
      <div className="note">
        RELAY costs a little more than last-message-only, but preserves the standing back-context
        constraints that last-message silently drops — at {t.saved_vs_full_pct}% below the naive
        full-transcript broadcast. Single illustrative scenario; savings are scale-driven.
      </div>
    </div>
  );
}

function CompressBox({ roles }) {
  const [role, setRole] = useState("budget");
  const [memory, setMemory] = useState(
    "Maya is vegetarian and eats no meat. Keep dinners under $40 this month. Always confirm before paying. The weather has been nice. Concert tickets are $65."
  );
  const [out, setOut] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const run = async () => {
    setLoading(true); setErr(null);
    try { setOut(await api.compress({ role, task: "plan a friday dinner", memory })); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="panel">
      <h2>Compress anything for an agent</h2>
      <div className="muted" style={{ marginBottom: 8 }}>Paste a memory blob, pick a recipient role, get its passport.</div>
      <select value={role} onChange={(e) => setRole(e.target.value)} style={{ marginBottom: 10 }}>
        {(roles || ["restaurant", "calendar", "budget", "writer"]).map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
      <textarea value={memory} onChange={(e) => setMemory(e.target.value)} />
      <button className="btn" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
        {loading ? <><span className="spinner" />compressing…</> : "Compress"}
      </button>
      {err && <div className="toast">⚠ {err}</div>}
      {out && (
        <div style={{ marginTop: 12 }}>
          <div className="muted">facts kept: {out.stats.facts ?? 0} · {out.stats.relayed_tokens} tok (raw {out.stats.raw_tokens})</div>
          <pre style={{ whiteSpace: "pre-wrap", background: "#070b12", border: "1px solid var(--border)", borderRadius: 8, padding: 10, fontSize: 12, marginTop: 6 }}>{out.reply}</pre>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [tab, setTab] = useState("dashboard");
  const [scenario, setScenario] = useState(null);
  const [passports, setPassports] = useState(null);
  const [relay, setRelay] = useState(null);
  const [down, setDown] = useState(null);
  const [pErr, setPErr] = useState(null);
  const [rErr, setRErr] = useState(null);

  useEffect(() => {
    api.scenario().then(setScenario).catch((e) => setDown(e.message));
    api.passports().then(setPassports).catch((e) => setPErr(e.message));
    api.relay().then(setRelay).catch((e) => setRErr(e.message));
  }, []);

  return (
    <div className="wrap">
      <header className="top">
        <h1><span className="r">RAVEN</span> — Context Passports for the Agentic Web</h1>
        <span className="tag">recipient-aware, decision-preserving context compression</span>
      </header>

      <div className="tabs">
        {["dashboard", "relay", "compress"].map((t) => (
          <button key={t} className={"tab" + (tab === t ? " active" : "")} onClick={() => setTab(t)}>
            {t === "dashboard" ? "Dashboard" : t === "relay" ? "RELAY (agent→agent)" : "Compress anything"}
          </button>
        ))}
      </div>

      {down && <div className="toast">⚠ Backend not reachable at {api.base} — start it with <code>uvicorn raven.web.api:app --port 8000</code>. ({down})</div>}

      {tab === "dashboard" && (
        <div className="grid3">
          <MemoryPane scenario={scenario} />
          <AgentsPane passports={passports} error={pErr} />
          <div className="panel">
            <h2>Token meter · live decision</h2>
            <Meter passports={passports} error={pErr} />
            <div className="muted" style={{ margin: "14px 0 8px", borderTop: "1px dashed var(--border)", paddingTop: 12 }}>
              Live decision benchmark — 3 decision agents (restaurant · calendar · budget)
            </div>
            <Benchmark />
          </div>
        </div>
      )}

      {tab === "relay" && <RelayView relay={relay} error={rErr} />}
      {tab === "compress" && <CompressBox roles={scenario?.roles} />}
    </div>
  );
}
