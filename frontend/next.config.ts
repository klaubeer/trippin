import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const comNextIntl = createNextIntlPlugin("./src/i18n.ts");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["69.62.94.19", "trippin.klauberfischer.online"],
  output: "standalone",
};

export default comNextIntl(nextConfig);
