// Home page — redirect to /dashboard (Phase 10-B)

import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/dashboard");
}
