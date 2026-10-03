import { useEffect, useState } from "react";

import { api } from "../api/client";

type HealthResponse = {
  status: string;
  service?: string;
};

export default function ServerPage() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadHealth() {
    setLoading(true);
    setError("");

    try {
      const response = await api.get<HealthResponse>("/api/server/health");
      setData(response.data);
    } catch {
      setError("Не удалось получить health-check main backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHealth();
  }, []);

  async function restartStub() {
    const confirmed = window.confirm(
      "Отправить тестовый запрос рестарта? Сейчас это заглушка.",
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await api.post("/api/server/restart");
      alert(response.data.message || "Запрос отправлен.");
    } catch {
      alert("Не удалось отправить запрос рестарта.");
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Сервер</h1>
          <p>Состояние main backend и административные операции.</p>
        </div>

        <button className="secondary-button" onClick={loadHealth}>
          Проверить
        </button>
      </header>

      {loading && <div className="loading-box">Проверяю сервис…</div>}

      {error && <div className="alert error">{error}</div>}

      {!loading && data && (
        <div className="panel server-card">
          <div>
            <span className="muted-label">Статус</span>
            <h2>{data.status}</h2>
            <p>Сервис: {data.service || "main-backend"}</p>
          </div>

          <span
            className={`status-badge ${
              data.status === "ok" ? "ok" : "stub"
            }`}
          >
            {data.status}
          </span>
        </div>
      )}

      <div className="panel danger-panel">
        <div>
          <h2>Рестарт backend</h2>
          <p>
            Сейчас endpoint работает как заглушка. Реальный restart не
            подключён и не должен принимать shell-команды от браузера.
          </p>
        </div>

        <button className="danger-button" onClick={restartStub}>
          Запросить рестарт
        </button>
      </div>
    </section>
  );
}
