import "./globals.css";
import type { ReactNode } from "react";
import Nav from "@/components/cockpit/Nav";

export const metadata = { title: "TrustLedger", description: "Product authenticity as a condition of payment" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
