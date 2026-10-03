import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="not-found">
      <h1>404</h1>
      <p>Такой страницы нет.</p>
      <Link to="/">Вернуться в админку</Link>
    </div>
  );
}
