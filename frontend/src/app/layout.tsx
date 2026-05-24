import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
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
    <ClerkProvider>
      <html lang="en" data-scroll-behavior="smooth" className="dark scroll-smooth">
        <body className="antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
