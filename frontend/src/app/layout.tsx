import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets:  ["latin"] });

export const metadata: Metadata = {
  title: "Smart Asset Allocator",
  description: "Optimizacion de portafolios con IA - Black-Litterman + FinBERT + Monte Carlo",
};

export default function RootLayout({
  children,
}:  Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
