"use client";

import { FormEvent, useCallback, useMemo, useState } from "react";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { saveActiveProfileId } from "@/components/auth";
import { api } from "@/lib/api";
import { CompanyProfile, CompanyProfilePayload } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import { formatDate, toCommaSeparated } from "@/lib/utils";

const initialForm = {
  company_name: "",
  inn: "",
  region: "",
  categoriesText: "",
  has_license: false,
  has_experience: false,
  can_prepare_fast: true,
  notes: ""
};

type ProfileFormState = typeof initialForm;

export default function ProfilesPage() {
  const profiles = useLiveResource<CompanyProfile[]>({
    loader: useCallback(() => api.listCompanyProfiles(), [])
  });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ProfileFormState>(initialForm);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const payload = useMemo<CompanyProfilePayload>(
    () => ({
      company_name: form.company_name.trim(),
      inn: form.inn.trim(),
      region: form.region.trim(),
      categories: toCommaSeparated(form.categoriesText),
      has_license: form.has_license,
      has_experience: form.has_experience,
      can_prepare_fast: form.can_prepare_fast,
      notes: form.notes.trim()
    }),
    [form]
  );

  function fillForm(profile: CompanyProfile) {
    setEditingId(profile.id);
    setForm({
      company_name: profile.company_name,
      inn: profile.inn,
      region: profile.region,
      categoriesText: profile.categories.join(", "),
      has_license: profile.has_license,
      has_experience: profile.has_experience,
      can_prepare_fast: profile.can_prepare_fast,
      notes: profile.notes
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(initialForm);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    setIsSaving(true);

    try {
      const profile = editingId
        ? await api.updateCompanyProfile(editingId, payload)
        : await api.createCompanyProfile(payload);

      await profiles.refresh();
      saveActiveProfileId(profile.id);
      setMessage(
        editingId
          ? `Профиль #${profile.id} обновлен и выбран активным.`
          : `Профиль #${profile.id} создан и выбран активным.`
      );
      resetForm();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось сохранить профиль");
    } finally {
      setIsSaving(false);
    }
  }

  if (profiles.isLoading && !profiles.data) {
    return (
      <LoadingPanel
        title="Загружаем профили компаний"
        description="Подтягиваем карточки поставщиков, чтобы можно было выбрать активный профиль."
      />
    );
  }

  const rows = profiles.data ?? [];
  const visibleRows = rows.slice(0, 5);

  return (
    <div className="section-grid two-columns">
      <section className="panel section">
        <div className="section-heading">
          <div className="section-copy">
            <p className="eyebrow">Паспорт поставщика</p>
            <h3>{editingId ? `Редактирование профиля #${editingId}` : "Новый профиль компании"}</h3>
          </div>
          <LiveBadge isRefreshing={profiles.isRefreshing} lastUpdated={profiles.lastUpdated} />
        </div>

        <form className="field-grid" onSubmit={handleSubmit}>
          <label>
            <span>Название компании</span>
            <input
              value={form.company_name}
              onChange={(event) => setForm((current) => ({ ...current, company_name: event.target.value }))}
            />
          </label>

          <label>
            <span>ИНН</span>
            <input
              value={form.inn}
              onChange={(event) => setForm((current) => ({ ...current, inn: event.target.value }))}
            />
          </label>

          <label>
            <span>Регион</span>
            <input
              value={form.region}
              onChange={(event) => setForm((current) => ({ ...current, region: event.target.value }))}
            />
          </label>

          <label>
            <span>Категории через запятую</span>
            <input
              value={form.categoriesText}
              onChange={(event) =>
                setForm((current) => ({ ...current, categoriesText: event.target.value }))
              }
            />
          </label>

          <label className="checkbox-row">
            <input
              checked={form.has_license}
              type="checkbox"
              onChange={(event) =>
                setForm((current) => ({ ...current, has_license: event.target.checked }))
              }
            />
            <span>Есть лицензия</span>
          </label>

          <label className="checkbox-row">
            <input
              checked={form.has_experience}
              type="checkbox"
              onChange={(event) =>
                setForm((current) => ({ ...current, has_experience: event.target.checked }))
              }
            />
            <span>Подтвержден опыт</span>
          </label>

          <label className="checkbox-row">
            <input
              checked={form.can_prepare_fast}
              type="checkbox"
              onChange={(event) =>
                setForm((current) => ({ ...current, can_prepare_fast: event.target.checked }))
              }
            />
            <span>Можем быстро подготовить заявку</span>
          </label>

          <label>
            <span>Комментарий</span>
            <textarea
              rows={5}
              value={form.notes}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>

          <div className="inline-actions field-full">
            <button className="button" disabled={isSaving} type="submit">
              {isSaving ? "Сохраняем..." : editingId ? "Сохранить профиль" : "Создать профиль"}
            </button>
            {editingId ? (
              <button className="button button-secondary" type="button" onClick={resetForm}>
                Сбросить
              </button>
            ) : null}
          </div>
        </form>

        {message ? <p className="success-banner">{message}</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}
        {profiles.error ? <p className="error-banner">{profiles.error}</p> : null}
      </section>

      <section className="panel section">
        <div className="section-heading">
          <div className="section-copy">
            <p className="eyebrow">Справочник</p>
            <h3>Последние профили компаний</h3>
            <p className="muted">
              Показываем только 5 последних профилей, чтобы список не захламлялся.
            </p>
          </div>
        </div>

        {visibleRows.length ? (
          <div className="cards fresh-inputs-grid">
            {visibleRows.map((profile) => (
              <article className="card compact-card" key={profile.id}>
                <p className="eyebrow">Профиль #{profile.id}</p>
                <h4 className="truncate-2" title={profile.company_name || "Без названия"}>
                  {profile.company_name || "Без названия"}
                </h4>
                <span className="muted">ИНН: {profile.inn || "не заполнен"}</span>
                <span className="muted">Создан: {formatDate(profile.created_at)}</span>
                <span className="muted">
                  Категории: {profile.categories.length ? profile.categories.join(", ") : "не заданы"}
                </span>
                <div className="inline-actions">
                  <button className="button button-secondary" type="button" onClick={() => fillForm(profile)}>
                    Редактировать
                  </button>
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={() => {
                      saveActiveProfileId(profile.id);
                      setMessage(`Профиль #${profile.id} выбран активным.`);
                    }}
                  >
                    Сделать активным
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Профилей пока нет"
            description="Создай карточку компании, чтобы импортировать закупки и запускать анализ."
          />
        )}
      </section>
    </div>
  );
}
