"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { saveSession } from "@/components/auth";

const defaults = {
  name: "Оператор тендерного отдела",
  email: "operator@tender-navigator.local"
};

export default function LoginPage() {
  const router = useRouter();
  const [name, setName] = useState(defaults.name);
  const [email, setEmail] = useState(defaults.email);

  const isValid = useMemo(() => name.trim() && email.trim(), [email, name]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid) {
      return;
    }

    saveSession({
      name: name.trim(),
      email: email.trim()
    });
    router.push("/dashboard");
  }

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <p className="eyebrow">Tender Navigator</p>
        <h1>Локальный кабинет для анализа закупок</h1>
        <p className="muted">
          Это упрощенный локальный вход для тестирования продукта. После входа ты попадешь в
          рабочую панель, где можно создать профиль компании, импортировать закупку и
          отслеживать анализ в фоне.
        </p>
      </section>

      <section className="panel auth-card">
        <div className="section-copy">
          <p className="eyebrow">Вход</p>
          <h2>Оператор системы</h2>
        </div>

        <form className="field-grid" onSubmit={handleSubmit}>
          <label>
            <span>Имя</span>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>

          <label>
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <button className="button field-full" disabled={!isValid} type="submit">
            Открыть кабинет
          </button>
        </form>
      </section>
    </main>
  );
}
