import { useEffect, useRef, useState } from "react";

const EXAMPLES = [
  "最近一个月工会的活动",
  "MySQL incident mitigation",
  "Azure DevOps pull request",
  "weekly automation report",
];

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function initials(name, fallback) {
  const source = (name || fallback || "?").trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Deterministic colour per sender for the avatar. Saturation/lightness are
// fixed in a readable range so white initials always have enough contrast.
function avatarColor(seed) {
  let hash = 0;
  for (let i = 0; i < seed.length; i++)
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 42%, 48%)`;
}

function SearchIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path
        d="M21 21l-4.3-4.3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function BrandMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect
        x="1.5"
        y="4.5"
        width="15.5"
        height="12"
        rx="2.6"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M2.5 6.5l6.75 4.25 6.75-4.25"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="17" cy="16.5" r="3.8" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M19.8 19.3L22.3 21.8"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M19.8 2.6l.55 1.55 1.55.55-1.55.55-.55 1.55-.55-1.55-1.55-.55 1.55-.55z"
        fill="currentColor"
      />
    </svg>
  );
}

function FilterChips({ parsed }) {
  if (!parsed) return null;
  const f = parsed.filters || {};
  const chips = [];
  if (f.sender_contains) chips.push(`From: ${f.sender_contains}`);
  if (f.date_from) chips.push(`After ${formatDate(f.date_from)}`);
  if (f.date_to) chips.push(`Before ${formatDate(f.date_to)}`);
  if (chips.length === 0 && !parsed.semantic_text) return null;
  return (
    <div className="chips">
      {parsed.semantic_text && (
        <span className="chip semantic" title="Semantic query">
          {parsed.semantic_text}
        </span>
      )}
      {chips.map((c) => (
        <span className="chip" key={c}>
          {c}
        </span>
      ))}
    </div>
  );
}

function Result({ hit }) {
  const { email } = hit;
  const name = email.sender_name || email.sender || "Unknown";
  const score = hit.rerank_score != null ? hit.rerank_score : hit.score;
  const open = () => {
    if (!email.id) return;
    fetch(`/api/open?id=${encodeURIComponent(email.id)}`, {
      method: "POST",
    }).catch(() => {});
  };
  return (
    <div
      className="result clickable"
      onClick={open}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") open();
      }}
    >
      <div className="avatar" style={{ background: avatarColor(name) }}>
        {initials(email.sender_name, email.sender)}
      </div>
      <div className="result-body">
        <div className="result-head">
          <span className="subject" title={email.subject || ""}>
            {email.subject || "(no subject)"}
          </span>
          <span className="head-right">
            {score != null && (
              <span className="score" title="Relevance score">
                {score.toFixed(3)}
              </span>
            )}
            <span className="open-hint">Open in Outlook ↗</span>
          </span>
        </div>
        <div className="meta">
          <span className="sender">{name}</span>
          <span className="dot">·</span>
          <span>{formatDate(email.date)}</span>
        </div>
        <p className="snippet">{(email.body || "").slice(0, 240)}</p>
        {email.attachments?.length > 0 && (
          <div className="attachments">
            {email.attachments.map((a) => (
              <span className="attachment" key={a}>
                📎 {a}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});
  }, []);

  async function runSearch(q) {
    const term = (q ?? query).trim();
    if (!term) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
      if (!r.ok) throw new Error(`Request failed (${r.status})`);
      setData(await r.json());
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span className="brand-name">Email Search</span>
        </div>
        {health && (
          <span className="badge">
            {health.emails.toLocaleString()} emails indexed
          </span>
        )}
      </header>

      <form
        className={`search-bar${loading ? " loading" : ""}`}
        onSubmit={(e) => {
          e.preventDefault();
          runSearch();
        }}
      >
        <span className="search-icon">
          <SearchIcon />
        </span>
        <input
          ref={inputRef}
          autoFocus
          placeholder="Search your emails in natural language…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && (
          <button
            type="button"
            className="clear-btn"
            aria-label="Clear"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
          >
            ✕
          </button>
        )}
      </form>

      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="example"
            onClick={() => {
              setQuery(ex);
              runSearch(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      {!data && !loading && !error && (
        <div className="hero">
          <div className="hero-icon">
            <SearchIcon />
          </div>
          <p className="hero-title">Find any email by what it's about</p>
          <p className="hero-sub">
            Describe it in your own words — a topic, a person, or a time
            range. Try the examples above to get started.
          </p>
        </div>
      )}

      {loading && (
        <div className="results" aria-busy="true">
          <div className="searching">
            <span className="spinner" />
            <span className="searching-text">Searching your emails…</span>
          </div>
          {Array.from({ length: 4 }).map((_, i) => (
            <div className="skeleton" key={i}>
              <div className="sk-avatar" />
              <div className="sk-body">
                <div className="sk-line sk-title" />
                <div className="sk-line sk-meta" />
                <div className="sk-line sk-text" />
                <div className="sk-line sk-text short" />
              </div>
            </div>
          ))}
        </div>
      )}

      {data && !loading && (
        <div className="results">
          <FilterChips parsed={data.parsed} />
          <div className="results-meta">
            {data.hits.length} result{data.hits.length === 1 ? "" : "s"}
          </div>
          {data.hits.map((h, i) => (
            <div
              className="result-wrap"
              key={h.email.id}
              style={{ animationDelay: `${Math.min(i, 8) * 0.04}s` }}
            >
              <Result hit={h} />
            </div>
          ))}
          {data.hits.length === 0 && (
            <div className="empty">No matching emails.</div>
          )}
        </div>
      )}
    </div>
  );
}

