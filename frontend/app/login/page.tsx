"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { readSession, saveSession } from "@/components/auth";
import { api } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [isBootstrapLoading, setIsBootstrapLoading] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [organizationName, setOrganizationName] = useState("ООО Тендер Навигатор");
  const [fullName, setFullName] = useState("Оператор тендерного отдела");
  const [email, setEmail] = useState("operator@tender-navigator.local");
  const [password, setPassword] = useState("TenderNavigator123");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (readSession()) {
      router.replace("/dashboard");
      return;
    }

    let isMounted = true;
    api
      .getBootstrapStatus()
      .then((status) => {
        if (!isMounted) {
          return;
        }
        setSetupRequired(status.setup_required);
        setMode(status.setup_required ? "register" : "login");
      })
      .catch((loadError) => {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Не удалось проверить состояние входа");
      })
      .finally(() => {
        if (isMounted) {
          setIsBootstrapLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [router]);

  const isValid = useMemo(() => {
    if (!email.trim() || password.trim().length < 8) {
      return false;
    }
    if (mode === "register") {
      return Boolean(organizationName.trim() && fullName.trim());
    }
    return true;
  }, [email, fullName, mode, organizationName, password]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const session =
        mode === "register"
          ? await api.register({
              organization_name: organizationName.trim(),
              full_name: fullName.trim(),
              email: email.trim(),
              password: password.trim()
            })
          : await api.login({
              email: email.trim(),
              password: password.trim()
            });

      saveSession(session);
      router.push("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось выполнить вход");
    } finally {
      setIsSubmitting(false);
    }
  }

  const heading =
    mode === "register" ? "Создать организацию и первый аккаунт" : "Войти в рабочий кабинет";
  const description =
    mode === "register"
      ? "Первый запуск создаст организацию, owner-пользователя и сразу откроет кабинет поставщика."
      : "Используй рабочий email и пароль, чтобы продолжить анализ закупок внутри своей организации.";

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <p className="eyebrow">Tender Navigator</p>
        <h1>Личный кабинет для анализа закупок по 44-ФЗ и 223-ФЗ</h1>
        <p className="muted">
          Rule engine, импорт закупок, explainability и ручная проверка решения теперь работают
          внутри организации и реальных пользовательских аккаунтов.
        </p>
      </section>

      <section className="panel auth-card">
        <div className="section-copy">
          <p className="eyebrow">Авторизация</p>
          <h2>{heading}</h2>
          <p className="muted">{description}</p>
        </div>

        {isBootstrapLoading ? (
          <p className="muted">Проверяем состояние системы...</p>
        ) : (
          <form className="field-grid" onSubmit={handleSubmit}>
            {mode === "register" ? (
              <>
                <label>
                  <span>Организация</span>
                  <input
                    value={organizationName}
                    onChange={(event) => setOrganizationName(event.target.value)}
                  />
                </label>

                <label>
                  <span>Имя пользователя</span>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
                </label>
              </>
            ) : null}

            <label>
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>

            <label>
              <span>Пароль</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            <button className="button field-full" disabled={!isValid || isSubmitting} type="submit">
              {isSubmitting
                ? "Подключаем кабинет..."
                : mode === "register"
                  ? "Создать организацию"
                  : "Войти в кабинет"}
            </button>
          </form>
        )}

        {!isBootstrapLoading && !setupRequired ? (
          <div className="inline-actions">
            <button
              className="button button-secondary"
              type="button"
              onClick={() => setMode((current) => (current === "login" ? "register" : "login"))}
            >
              {mode === "login" ? "Создать новую организацию" : "У меня уже есть аккаунт"}
            </button>
          </div>
        ) : null}

        {error ? <p className="error-banner">{error}</p> : null}
      </section>
    </main>
  );
}
