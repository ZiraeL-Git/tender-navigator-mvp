"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { saveSession } from "@/components/auth";
import { api } from "@/lib/api";
import { Invitation } from "@/lib/types";

export default function InvitationPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const token = params.token;

  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("TenderNavigator123");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    api
      .getInvitation(token)
      .then((record) => {
        if (isMounted) {
          setInvitation(record);
        }
      })
      .catch((loadError) => {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : "Не удалось открыть приглашение");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!fullName.trim()) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const session = await api.acceptInvitation({
        token,
        full_name: fullName.trim(),
        password: password.trim()
      });
      saveSession(session);
      router.push("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось принять приглашение");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <p className="eyebrow">Приглашение</p>
        <h1>Подключение к рабочей организации</h1>
        <p className="muted">
          Заверши регистрацию по приглашению и открой кабинет для совместной работы с закупками.
        </p>
      </section>

      <section className="panel auth-card">
        {isLoading ? (
          <p className="muted">Проверяем приглашение...</p>
        ) : invitation ? (
          <>
            <div className="section-copy">
              <p className="eyebrow">{invitation.organization?.name ?? "Организация"}</p>
              <h2>{invitation.email}</h2>
              <p className="muted">
                Роль: {invitation.role}. Приглашение активно до {new Date(invitation.expires_at).toLocaleString("ru-RU")}.
              </p>
            </div>

            <form className="field-grid" onSubmit={handleSubmit}>
              <label>
                <span>Имя пользователя</span>
                <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
              </label>

              <label>
                <span>Пароль</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              <button className="button field-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Подключаем кабинет..." : "Принять приглашение"}
              </button>
            </form>
          </>
        ) : (
          <div className="empty-state">
            <strong>Приглашение недоступно</strong>
            <p className="muted">
              Возможно, ссылка устарела или уже была использована. Вернись к владельцу организации
              и попроси создать новое приглашение.
            </p>
            <Link className="button button-secondary" href="/login">
              Вернуться ко входу
            </Link>
          </div>
        )}

        {error ? <p className="error-banner">{error}</p> : null}
      </section>
    </main>
  );
}
