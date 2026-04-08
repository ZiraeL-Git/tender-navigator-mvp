"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { clearSession, readActiveProfileId, readSession } from "@/components/auth";
import { AuthSession } from "@/lib/types";

const navigationItems = [
  { href: "/dashboard", label: "Сводка" },
  { href: "/profiles", label: "Профиль компании" },
  { href: "/inputs", label: "Импорт закупок" },
  { href: "/analyses", label: "Анализы" },
  { href: "/team", label: "Команда" }
];

type DashboardShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

function getRoleLabel(role: AuthSession["user"]["role"]): string {
  if (role === "owner") {
    return "Владелец организации";
  }
  if (role === "viewer") {
    return "Наблюдатель";
  }
  return "Оператор";
}

export function DashboardShell({ title, subtitle, children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
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

  const displayName = session.user.full_name ?? session.user.email;
  const roleLabel = getRoleLabel(session.user.role);

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Tender Navigator</p>
          <h1>Личный кабинет поставщика</h1>
          <p className="muted">
            Профиль компании, импорт закупок, фоновая обработка, командная работа и ручная
            проверка решения собраны в одном рабочем пространстве.
          </p>
        </div>

        <div className="profile-card profile-card-active">
          <strong>{displayName}</strong>
          <span>{session.user.email}</span>
          <span>{roleLabel}</span>
          <span>Организация: {session.user.organization.name}</span>
          <span>Активный профиль: {activeProfileId ? `#${activeProfileId}` : "не выбран"}</span>
        </div>

        <nav className="nav-list" aria-label="Основная навигация">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                className={`nav-link${isActive ? " active" : ""}`}
                href={item.href as any}
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
