import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fixit | Modern Maintenance Solutions",
  description: "Professional maintenance and repair services powered by intelligent automation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
