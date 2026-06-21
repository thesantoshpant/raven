"use client";

import { useEffect, useRef, useState } from "react";
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

const svg = (children) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{children}</svg>
);
const ROLE_ICON = {
  restaurant: svg(<><path d="M4 3v8M7 3v8M5.5 3v8M5.5 11v10M18 3c-1.6 0-2.5 2.2-2.5 5.5S16.4 13 18 13v8" /></>),
  calendar: svg(<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 9h18M8 3v4M16 3v4" /></>),
  budget: svg(<><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M3 10h18M16 14.5h2" /></>),
  writer: svg(<><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" /></>),
};

function MemoryPane({ scenario, onUpload, uploading, uploadErr, uploadMsg }) {
  if (!scenario) return <div className="panel"><h2>User memory</h2><div className="muted">loading…</div></div>;
  const phrases = scenario.highlights || [];
  const hasGold = (t) => phrases.some((p) => t.toLowerCase().includes(p.toLowerCase()));
  return (
    <div className="panel">
      <h2>User memory <span className="count">{scenario.counts.items} items · {scenario.counts.facts} facts</span></h2>
      <div className="muted" style={{ marginBottom: 10 }}>Everything you&apos;d dump into an agent. The 5 decision-critical facts are buried (highlighted).</div>
      <div style={{ marginBottom: 10 }}>
        <label className="btn secondary" style={{ display: "inline-block", width: "auto", padding: "7px 12px", fontSize: 13, cursor: uploading ? "not-allowed" : "pointer" }}>
          {uploading ? <><span className="spinner" />ingesting…</> : "+ Upload a PDF / doc → memory"}
          <input type="file" accept=".pdf,.docx,.md,.txt,.html" style={{ display: "none" }} disabled={uploading}
            onChange={(e) => { const f = e.target.files && e.target.files[0]; if (f) onUpload(f); e.target.value = ""; }} />
        </label>
        {uploadErr && <div className="toast">⚠ {uploadErr}</div>}
        {uploadMsg && <div className="muted" style={{ marginTop: 6 }}>✓ {uploadMsg}</div>}
      </div>
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
            <span className="role">{ROLE_ICON[r.role] || null}{r.role}</span>
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
      <div className="meter-row"><span>Raw — full memory to all {n} agents</span><span className="v">{rawBroadcast.toLocaleString()} tok</span></div>
      <div className="bar raw" style={{ width: "100%" }} />
      <div className="meter-row"><span>RAVEN — tailored passports</span><span className="v">{ravenTotal.toLocaleString()} tok</span></div>
      <div className="bar raven" style={{ width: ravenW + "%" }} />
      <div style={{ marginTop: 16 }}>
        <div className="bigstat good">{savedPct}%</div>
        <div className="statline">fewer context tokens delivered across the workflow</div>
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
  const CONSTRAINT_LABEL = {
    vegetarian: "vegetarian", budget_under_40: "under $40", after_6pm: "after 6pm",
    not_loud: "not loud", confirm_before_pay: "confirm before paying",
  };
  const pretty = (m) => CONSTRAINT_LABEL[m] || m;
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
            const dots = Array.from({ length: d.total }, (_, i) => (
              <span key={i} className={i < d.constraints ? "on" : "miss"}>●</span>
            ));
            return (
              <div className={"cond" + (c === "raven" ? " raven" : "")} key={c}>
                <div>
                  <span className="name">{labels[c]}</span>
                  {d.missed.length > 0 && <div className="missed">missed: {d.missed.map(pretty).join(", ")}</div>}
                </div>
                <span>
                  <span className={"score " + (full ? "full" : "partial")}>{d.constraints}/{d.total}</span>{" "}
                  <span className="dots">{dots}</span>
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
      <h1 className="bighead">RELAY · agent → agent handoff compression</h1>
      <p className="subhead">
        Forward the latest message + a recipient-aware compressed passport of the back-context —
        instead of the whole growing transcript.
      </p>
      <div className="impact">
        <div>
          <div className="lbl">Compression impact</div>
          <div className="big">{t.saved_vs_full_pct}%</div>
          <div className="muted">token savings vs the full-transcript broadcast</div>
        </div>
        <div className="side">Total full context: {t.full.toLocaleString()} tok<br />RAVEN relay: {t.relay.toLocaleString()} tok</div>
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
    <div style={{ maxWidth: 760, margin: "0 auto" }}>
      <div className="panel">
        <h1 className="bighead">Compress anything for an agent</h1>
        <p className="subhead">Paste a memory blob, pick a recipient role, get its passport.</p>
        <div className="muted" style={{ marginBottom: 6 }}>Recipient role</div>
        <select value={role} onChange={(e) => setRole(e.target.value)} style={{ marginBottom: 14 }}>
          {(roles || ["restaurant", "calendar", "budget", "writer"]).map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <div className="muted" style={{ marginBottom: 6 }}>Memory blob</div>
        <textarea value={memory} onChange={(e) => setMemory(e.target.value)} />
        <button className="btn" style={{ marginTop: 14 }} onClick={run} disabled={loading}>
          {loading ? <><span className="spinner" />compressing…</> : "Compress"}
        </button>
        {err && <div className="toast">⚠ {err}</div>}
        {out && (
          <div style={{ marginTop: 16 }}>
            <div className="muted">facts kept: {out.stats.facts ?? 0} · {out.stats.relayed_tokens} tok (raw {out.stats.raw_tokens})</div>
            <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font-mono)", background: "var(--sunken)", color: "var(--ink)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, fontSize: 12.5, lineHeight: 1.55, marginTop: 8 }}>{out.reply}</pre>
          </div>
        )}
      </div>
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
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState(null);
  const [uploadMsg, setUploadMsg] = useState(null);
  const baseRef = useRef(null);

  useEffect(() => {
    api.scenario().then((s) => { baseRef.current = s; setScenario(s); }).catch((e) => setDown(e.message));
    api.passports().then(setPassports).catch((e) => setPErr(e.message));
    api.relay().then(setRelay).catch((e) => setRErr(e.message));
  }, []);

  const handleIngest = async (file) => {
    setUploading(true); setUploadErr(null); setUploadMsg(null);
    try {
      const res = await api.ingest(file);
      const base = baseRef.current;
      // The backend is stateless = base corpus + THIS doc. Rebuild from the base
      // (replace, not accumulate) so the memory list, counts, and passports stay in
      // sync on re-upload (a second upload replaces the first, like the backend).
      if (base) {
        setScenario({
          ...base,
          memory_items: [...base.memory_items, ...res.new_items],
          counts: { items: base.counts.items + res.added, facts: res.passports.n_facts },
        });
      }
      setPassports(res.passports);
      setUploadMsg(res.added > 0
        ? `+${res.added} items ingested → passports recomputed (replaces any previous upload)`
        : "No usable text found in that file.");
    } catch (e) { setUploadErr(e.message || "ingest failed"); }
    finally { setUploading(false); }
  };

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
          <MemoryPane scenario={scenario} onUpload={handleIngest} uploading={uploading} uploadErr={uploadErr} uploadMsg={uploadMsg} />
          <AgentsPane passports={passports} error={pErr} />
          <div className="panel">
            <h2>Token meter · live decision</h2>
            <Meter passports={passports} error={pErr} />
            <div className="muted" style={{ margin: "18px 0 10px", borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              Live decision benchmark — 3 decision agents (restaurant · calendar · budget)
            </div>
            <Benchmark />
          </div>
        </div>
      )}

      {tab === "relay" && <RelayView relay={relay} error={rErr} />}
      {tab === "compress" && <CompressBox roles={scenario?.roles} />}

      <footer className="foot">
        <span>Fetch.ai · ASI:One</span>
        <span><a href="#">Documentation</a><a href="#">Privacy</a><a href="#">Terms</a></span>
      </footer>
    </div>
  );
}
