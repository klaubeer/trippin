import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const comNextIntl = createNextIntlPlugin("./src/i18n.ts");

const nextConfig: NextConfig = {
  // Nenhuma config adicional necessária por ora
};

export default comNextIntl(nextConfig);
