import createMiddleware from "next-intl/middleware";
import { routing } from "./src/routing";

export function proxy(request: Request) {
  return createMiddleware(routing)(request as any);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
