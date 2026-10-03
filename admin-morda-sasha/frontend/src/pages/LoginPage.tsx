import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { api } from "../api/client";

type LoginResponse = {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
};

export default function LoginPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("mainadmin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isLoggedIn = Boolean(localStorage.getItem("admin_token"));

  if (isLoggedIn) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);

      const response = await api.post<LoginResponse>(
        "/api/auth/login",
        body,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        },
      );

      localStorage.setItem("admin_token", response.data.access_token);
      localStorage.setItem(
        "admin_user",
        JSON.stringify({
          username: response.data.username,
          role: response.data.role,
        }),
      );

      navigate("/");
    } catch {
      setError("Не удалось войти. Проверь логин, пароль и доступность API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-logo">AF</div>

        <h1>Вход в админку</h1>
        <p>AntiFraud Phone Monitoring</p>

        {error && <div className="alert error">{error}</div>}

        <label>
          Логин
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            placeholder="mainadmin"
            required
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            placeholder="Введите пароль"
            required
          />
        </label>

        <button className="primary-button full-width" disabled={loading}>
          {loading ? "Входим..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
