import "./globals.css";

export const metadata = {
  title: "SafeCall Admin",
  description: "Campaign and complaint administration",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
