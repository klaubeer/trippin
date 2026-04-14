import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { Geist } from "next/font/google";
import type { Metadata } from "next";
import "../globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });

export const metadata: Metadata = {
  title: "Trippin' — Planejamento de viagens com IA",
  description:
    "Informe o destino e as datas. Nossa IA gera 3 roteiros completos para você.",
};

const locales = ["pt-BR", "en"];

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LayoutLocale({
  children,
  params,
}: LayoutProps<"/[locale]">) {
  const { locale } = await params;

  if (!locales.includes(locale)) notFound();

  const mensagens = await getMessages();

  return (
    <html lang={locale} className={geist.variable}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <NextIntlClientProvider messages={mensagens}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
