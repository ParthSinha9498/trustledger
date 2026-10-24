import "./globals.css";
import type { ReactNode } from "react";
import HeaderSwitcher from "@/components/checkout/HeaderSwitcher";

export const metadata = { title: "TrustLedger", description: "Product authenticity as a condition of payment" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <HeaderSwitcher />
        {children}
      </body>
    </html>
  );
}
