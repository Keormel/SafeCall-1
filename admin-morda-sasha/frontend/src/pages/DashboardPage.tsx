import { useEffect, useState } from "react";

import { api } from "../api/client";

type DashboardData = {
  active_users: number;
  active_numbers: number;
  high_risk_numbers: number;
  critical_risk_numbers: number;
  reports_pending: number;
  api_errors_24h: number;
  main_backend_status: "ok" | "degraded" | "down" | "stub";
  generated_at: string;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadDashboard() {
    setError("");
    setLoading(true);

    try {
      const response = await api.get<DashboardData>(
        "/api/dashboard/overview",
      );

      setData(response.data);
    } catch {
      setError("Не удалось загрузить статистику.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const cards = data
    ? [
        {
          label: "Активные пользователи",
          value: data.active_users,
          tone: "blue",
        },
        {
          label: "Активные номера",
          value: data.active_numbers,
          tone: "green",
        },
        {
          label: "Высокий риск",
          value: data.high_risk_numbers,
          tone: "orange",
        },
        {
          label: "Критический риск",
          value: data.critical_risk_numbers,
          tone: "red",
        },
        {
          label: "Жалоб ожидают проверки",
          value: data.reports_pending,
          tone: "purple",
        },
        {
          label: "Ошибки API за 24 часа",
          value: data.api_errors_24h,
          tone: "gray",
        },
      ]
    : [];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Дашборд</h1>
          <p>Общее состояние антифрод-системы.</p>
        </div>

        <button className="secondary-button" onClick={loadDashboard}>
          Обновить
        </button>
      </header>

      {loading && <div className="loading-box">Загружаю статистику…</div>}

      {error && <div className="alert error">{error}</div>}

      {!loading && data && (
        <>
          <div className="stats-grid">
            {cards.map((card) => (
              <article className="stat-card" key={card.label}>
                <span className={`stat-dot ${card.tone}`} />
                <span className="stat-label">{card.label}</span>
                <strong>{card.value.toLocaleString("ru-RU")}</strong>
              </article>
            ))}
          </div>

          <div className="panel dashboard-status">
            <div>
              <h2>Статус main backend</h2>
              <p>
                Последнее обновление:{" "}
                {new Date(data.generated_at).toLocaleString("ru-RU")}
              </p>
            </div>

            <span className={`status-badge ${data.main_backend_status}`}>
              {data.main_backend_status}
            </span>
          </div>

          {data.main_backend_status === "stub" && (
            <div className="alert warning">
              Сейчас включён MOCK_MODE: отображаются тестовые данные из
              <code> app/main_client.py</code>, а не данные main-софта.
            </div>
          )}
        </>
      )}
    </section>
  );
}
