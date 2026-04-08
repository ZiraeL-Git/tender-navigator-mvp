import { ReactNode } from "react";

import { DashboardShell } from "@/components/dashboard-shell";

export default function CabinetLayout({ children }: { children: ReactNode }) {
  return (
    <DashboardShell
      title="Рабочая панель поставщика"
      subtitle="Один контур для профиля компании, импорта закупок, фоновой обработки и ручной корректировки решения."
    >
      {children}
    </DashboardShell>
  );
}
