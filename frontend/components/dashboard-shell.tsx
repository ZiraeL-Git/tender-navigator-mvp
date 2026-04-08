"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import {
  clearSession,
  readActiveProfileId,
  readSession,
  type OperatorSession
} from "@/components/auth";

const navigationItems = [
  { href: "/dashboard", label: "Сводка" },
  { href: "/profiles", label: "Профиль компании" },
  { href: "/inputs", label: "Импорт закупок" },
  { href: "/analyses", label: "Анализы" }
];

type DashboardShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function DashboardShell({ title, subtitle, children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<OperatorSession | null>(null);
  const [activeProfileId, setActiveProfileId] = useState<number | null>(null);

  useEffect(() => {
    const storedSession = readSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    setActiveProfileId(readActiveProfileId());
  }, [router, pathname]);

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

  if (!session) {
    return null;
  }

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Tender Navigator</p>
          <h1>Личный кабинет поставщика</h1>
          <p className="muted">
            Профиль компании, импорт закупок, фоновая обработка и ручная проверка решения
            собраны в одном рабочем пространстве.
          </p>
        </div>

        <div className="profile-card profile-card-active">
          <strong>{session.name}</strong>
          <span>{session.email}</span>
          <span>Активный профиль: {activeProfileId ? `#${activeProfileId}` : "не выбран"}</span>
        </div>

        <nav className="nav-list" aria-label="Основная навигация">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                className={`nav-link${isActive ? " active" : ""}`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button className="button button-secondary sidebar-action" type="button" onClick={handleLogout}>
          Выйти
        </button>
      </aside>

      <main className="content">
        <header className="topbar panel">
          <div className="section-copy">
            <p className="eyebrow">Рабочий контур</p>
            <h2>{title}</h2>
            <p className="muted">{subtitle}</p>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
