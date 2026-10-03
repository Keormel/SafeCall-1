import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";

type Risk = "UNKNOWN" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
type Sort = "" | "score_desc" | "score_asc";

type NumberItem = {
  id: string;
  phone_e164: string;
  risk_level: Risk;
  score: number;
  reports_count: number;
  unique_reporters_count: number;
  campaign_id: number | null;
  is_removed: boolean;
  updated_at: string;
};

const RISKS: Risk[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

const riskLabel: Record<Risk, string> = {
  UNKNOWN: "Неизвестно",
  LOW: "Низкий",
  MEDIUM: "Средний",
  HIGH: "Высокий",
  CRITICAL: "Критический",
};

const NEXT_SORT: Record<Sort, Sort> = {
  "": "score_desc",
  score_desc: "score_asc",
  score_asc: "",
};

const SORT_ICON: Record<Sort, string> = {
  "": "↕",
  score_desc: "↓",
  score_asc: "↑",
};

const SORT_TITLE: Record<Sort, string> = {
  "": "Сортировать по убыванию",
  score_desc: "Сортировать по возрастанию",
  score_asc: "Сбросить сортировку",
};

// Должно совпадать с app/scoring.py
function riskFromScore(score: number): Risk {
  if (score <= 10) return "LOW";
  if (score <= 40) return "MEDIUM";
  if (score <= 80) return "HIGH";
  return "CRITICAL";
}

function sanitizeScore(value: string): string {
  let digits = value.replace(/\D/g, "").slice(0, 3);
  digits = digits.replace(/^0+(?=\d)/, "");
  if (digits !== "" && Number(digits) > 100) return "100";
  return digits;
}

function scoreNum(value: string): number {
  return value === "" ? 0 : Number(value);
}

const PAGE_SIZE = 50;
const PHONE_MAX_DIGITS = 19;

function normalizePhone(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, PHONE_MAX_DIGITS);
  return "+" + digits;
}

function isValidPhone(value: string) {
  return /^\+[1-9]\d{7,18}$/.test(value);
}

function errText(e: any) {
  const d = e?.response?.data?.detail;
  if (!d) return "Ошибка запроса";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x: any) => `${x.loc?.slice(-1)[0] ?? ""}: ${x.msg}`)
      .join("\n");
  }
  return JSON.stringify(d);
}

function pageList(current: number, last: number): (number | "...")[] {
  const pages: (number | "...")[] = [1];
  const from = Math.max(2, current - 2);
  const to = Math.min(last - 1, current + 2);

  if (from > 2) pages.push("...");
  for (let p = from; p <= to; p++) pages.push(p);
  if (to < last - 1) pages.push("...");
  if (last > 1) pages.push(last);

  return pages;
}

function RiskBadge({ level }: { level: Risk }) {
  return (
    <span className={`risk-badge ${level.toLowerCase()}`}>
      {riskLabel[level] ?? level}
    </span>
  );
}

function ScoreInput(props: {
  value: string;
  onChange: (v: string) => void;
  onEnter?: () => void;
  onEscape?: () => void;
  autoFocus?: boolean;
}) {
  return (
    <input
      type="text"
      inputMode="numeric"
      maxLength={3}
      placeholder="0–100"
      className="score-input"
      autoFocus={props.autoFocus}
      value={props.value}
      onFocus={(e) => e.target.select()}
      onChange={(e) => props.onChange(sanitizeScore(e.target.value))}
      onKeyDown={(e) => {
        if (e.key === "Enter" && props.onEnter) {
          e.preventDefault();
          props.onEnter();
        }
        if (e.key === "Escape" && props.onEscape) props.onEscape();
      }}
    />
  );
}

export default function NumbersPage() {
  const [items, setItems] = useState<NumberItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [jump, setJump] = useState("");

  const [q, setQ] = useState("");
  const [risk, setRisk] = useState("");
  const [status, setStatus] = useState("active");
  const [sort, setSort] = useState<Sort>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [newPhone, setNewPhone] = useState("+");
  const [newScore, setNewScore] = useState("");

  const [editId, setEditId] = useState<string | null>(null);
  const [editScore, setEditScore] = useState("");

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  async function load(p: number = page) {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/api/numbers", {
        params: {
          q: q || undefined,
          risk_level: risk || undefined,
          status: status || undefined,
          sort: sort || undefined,
          limit: PAGE_SIZE,
          offset: (p - 1) * PAGE_SIZE,
        },
      });

      const newLast = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
      if (p > newLast) {
        setPage(newLast);
        return;
      }

      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [page, status, risk, sort]);

  function changeRisk(value: string) {
    setRisk(value);
    setPage(1);
  }

  function changeStatus(value: string) {
    setStatus(value);
    setPage(1);
  }

  function toggleSort() {
    setSort(NEXT_SORT[sort]);
    setPage(1);
  }

  function search(e: FormEvent) {
    e.preventDefault();
    if (page === 1) void load(1);
    else setPage(1);
  }

  function goTo(p: number) {
    const target = Math.min(Math.max(1, p), lastPage);
    if (target !== page) setPage(target);
  }

  function submitJump(e: FormEvent) {
    e.preventDefault();
    const p = parseInt(jump, 10);
    if (!Number.isNaN(p)) goTo(p);
    setJump("");
  }

  async function create(e: FormEvent) {
    e.preventDefault();

    if (!isValidPhone(newPhone)) {
      alert("Номер: + и от 8 до 19 цифр, первая цифра не 0");
      return;
    }
    if (newScore === "") {
      alert("Укажи score от 0 до 100");
      return;
    }

    try {
      await api.post("/api/numbers", {
        phone_e164: newPhone,
        score: scoreNum(newScore),
      });
      setNewPhone("+");
      setNewScore("");
      setShowForm(false);
      if (page === 1) void load(1);
      else setPage(1);
    } catch (err) {
      alert(errText(err));
    }
  }

  function startEdit(n: NumberItem) {
    setEditId(n.id);
    setEditScore(String(n.score));
  }

  async function saveEdit(n: NumberItem) {
    if (editScore === "") {
      alert("Укажи score от 0 до 100");
      return;
    }

    const s = scoreNum(editScore);
    if (s === n.score) {
      setEditId(null);
      return;
    }

    const next = riskFromScore(s);
    const comment = prompt(
      `Score ${n.score} → ${s}, риск станет: ${riskLabel[next]}\n` +
        "Причина изменения (можно пусто):",
    );
    if (comment === null) return;

    try {
      await api.patch(`/api/numbers/${n.id}`, {
        score: s,
        comment: comment || undefined,
      });
      setEditId(null);
      void load();
    } catch (err) {
      alert(errText(err));
    }
  }

  async function archive(n: NumberItem) {
    if (!confirm(`Удалить ${n.phone_e164} (is_removed)?`)) return;
    try {
      await api.delete(`/api/numbers/${n.id}`);
      void load();
    } catch (err) {
      alert(errText(err));
    }
  }

  async function restore(n: NumberItem) {
    try {
      await api.post(`/api/numbers/${n.id}/restore`);
      void load();
    } catch (err) {
      alert(errText(err));
    }
  }

  const phoneInvalid = newPhone.length > 1 && !isValidPhone(newPhone);
  const fromRow = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const toRow = Math.min(page * PAGE_SIZE, total);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Номера</h1>
          <p>
            Всего по фильтру: {total.toLocaleString("ru-RU")} · Риск
            считается из score: 0–10 низкий, 11–40 средний, 41–80 высокий,
            81–100 критический
          </p>
        </div>
        <button
          className="primary-button"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "Закрыть" : "+ Добавить номер"}
        </button>
      </header>

      {showForm && (
        <form className="panel filters-panel filters" onSubmit={create}>
          <input
            required
            type="tel"
            inputMode="tel"
            maxLength={20}
            placeholder="+37369000004"
            value={newPhone}
            onChange={(e) => setNewPhone(normalizePhone(e.target.value))}
            className={phoneInvalid ? "input-invalid" : ""}
          />
          <span className="hint">
            {newPhone.length - 1}/{PHONE_MAX_DIGITS}
          </span>
          <ScoreInput value={newScore} onChange={setNewScore} />
          {newScore !== "" && (
            <>
              <span className="hint">→</span>
              <RiskBadge level={riskFromScore(scoreNum(newScore))} />
            </>
          )}
          <button
            className="primary-button"
            disabled={phoneInvalid || newScore === ""}
          >
            Сохранить
          </button>
        </form>
      )}

      <form className="panel filters-panel filters" onSubmit={search}>
        <input
          placeholder="Поиск по номеру"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={risk} onChange={(e) => changeRisk(e.target.value)}>
          <option value="">Любой риск</option>
          {RISKS.map((r) => (
            <option key={r} value={r}>
              {riskLabel[r]}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => changeStatus(e.target.value)}
        >
          <option value="active">Активные</option>
          <option value="archived">Удалённые</option>
          <option value="">Все</option>
        </select>
        <button className="secondary-button">Искать</button>
      </form>

      {error && <div className="alert error">{error}</div>}

      <div className="panel table-panel">
        <div className="table-topline">
          <strong>
            {fromRow}–{toRow} из {total.toLocaleString("ru-RU")}
          </strong>
          {loading && <span>Обновление…</span>}
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Номер</th>
                <th
                  className={`sortable ${sort ? "sorted" : ""}`}
                  title={SORT_TITLE[sort]}
                  onClick={toggleSort}
                >
                  Score <span className="sort-icon">{SORT_ICON[sort]}</span>
                </th>
                <th>Риск</th>
                <th>Жалобы</th>
                <th>Уник.</th>
                <th>Кампания</th>
                <th>Статус</th>
                <th>Обновлён</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={9} className="empty-cell">
                    Ничего не найдено
                  </td>
                </tr>
              )}
              {items.map((n) => {
                const editing = editId === n.id;
                return (
                  <tr key={n.id}>
                    <td>
                      <strong>{n.phone_e164}</strong>
                    </td>
                    <td>
                      {editing ? (
                        <ScoreInput
                          autoFocus
                          value={editScore}
                          onChange={setEditScore}
                          onEnter={() => void saveEdit(n)}
                          onEscape={() => setEditId(null)}
                        />
                      ) : (
                        `${n.score}/100`
                      )}
                    </td>
                    <td>
                      <RiskBadge
                        level={
                          editing && editScore !== ""
                            ? riskFromScore(scoreNum(editScore))
                            : n.risk_level
                        }
                      />
                    </td>
                    <td>{n.reports_count}</td>
                    <td>{n.unique_reporters_count}</td>
                    <td>{n.campaign_id ? `#${n.campaign_id}` : "—"}</td>
                    <td>
                      <span
                        className={`status-badge ${
                          n.is_removed ? "archived" : "active"
                        }`}
                      >
                        {n.is_removed ? "Удалён" : "Активен"}
                      </span>
                    </td>
                    <td>{new Date(n.updated_at).toLocaleString("ru-RU")}</td>
                    <td className="actions">
                      {editing ? (
                        <>
                          <button
                            className="primary-button"
                            onClick={() => saveEdit(n)}
                          >
                            OK
                          </button>
                          <button
                            className="secondary-button"
                            onClick={() => setEditId(null)}
                          >
                            ✕
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="secondary-button"
                            onClick={() => startEdit(n)}
                          >
                            Score
                          </button>
                          {n.is_removed ? (
                            <button
                              className="secondary-button"
                              onClick={() => restore(n)}
                            >
                              Вернуть
                            </button>
                          ) : (
                            <button
                              className="danger-button"
                              onClick={() => archive(n)}
                            >
                              Удалить
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {lastPage > 1 && (
          <div className="pagination">
            <button
              className="page-btn"
              disabled={page === 1 || loading}
              onClick={() => goTo(page - 1)}
            >
              ←
            </button>

            {pageList(page, lastPage).map((p, i) =>
              p === "..." ? (
                <span key={`dots-${i}`} className="page-dots">
                  …
                </span>
              ) : (
                <button
                  key={p}
                  className={`page-btn ${p === page ? "current" : ""}`}
                  disabled={loading}
                  onClick={() => goTo(p)}
                >
                  {p}
                </button>
              ),
            )}

            <button
              className="page-btn"
              disabled={page === lastPage || loading}
              onClick={() => goTo(page + 1)}
            >
              →
            </button>

            <form className="page-jump" onSubmit={submitJump}>
              <input
                type="number"
                min={1}
                max={lastPage}
                placeholder="стр."
                value={jump}
                onChange={(e) => setJump(e.target.value)}
              />
              <button className="page-btn">Перейти</button>
            </form>
          </div>
        )}
      </div>
    </section>
  );
}
