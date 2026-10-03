import { NavLink, Outlet, useNavigate } from "react-router-dom";

const links = [
  { to: "/", label: "Дашборд", icon: "▦" },
  { to: "/numbers", label: "Номера", icon: "☎" },
  { to: "/server", label: "Сервер", icon: "●" },
];

export default function Layout() {
  const navigate = useNavigate();

  const rawUser = localStorage.getItem("admin_user");
  const user = rawUser
    ? JSON.parse(rawUser) as { username: string; role: string }
    : null;

  function logout() {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AF</div>
          <div>
            <strong>AntiFraud</strong>
            <span>Admin Panel</span>
          </div>
        </div>

        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <span className="nav-icon">{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="current-user">
            <div className="user-avatar">
              {user?.username?.slice(0, 1).toUpperCase() || "A"}
            </div>

            <div className="user-meta">
              <strong>{user?.username || "admin"}</strong>
              <span>{user?.role || "main_admin"}</span>
            </div>
          </div>

          <button className="logout-button" onClick={logout}>
            Выйти
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
