import { redirect } from "next/navigation";

// Fallback para quando o middleware não interceptar a raiz
export default function RootPage() {
  redirect("/pt-BR");
}
