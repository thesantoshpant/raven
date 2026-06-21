import "./globals.css";

export const metadata = {
  title: "RAVEN — Context Passports for the Agentic Web",
  description: "Recipient-aware, decision-preserving context compression for multi-agent systems.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
