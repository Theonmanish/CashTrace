import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CashTrace",
  description: "Financial Dead Zone Detector",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
