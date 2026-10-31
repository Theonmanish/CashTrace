import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CashTrace | Financial Dead Zone Detector",
  description:
    "Reconstruct liquidity, forecast cash crunches, and simulate capital interventions with CashTrace.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
