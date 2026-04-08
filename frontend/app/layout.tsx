import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Sans, Playfair_Display } from "next/font/google";

import "@/app/globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans"
});

const serif = Playfair_Display({
  subsets: ["latin", "cyrillic"],
  weight: ["600", "700"],
  variable: "--font-serif"
});

export const metadata: Metadata = {
  title: "Tender Navigator",
  description: "Личный кабинет поставщика для анализа закупок"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className={`${sans.variable} ${serif.variable}`}>{children}</body>
    </html>
  );
}
