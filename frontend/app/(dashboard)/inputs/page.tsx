"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { readActiveProfileId } from "@/components/auth";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { AnalysisListItem, TenderInputListItem } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import { formatDate, isPendingAnalysisStatus } from "@/lib/utils";

const importDefaults = {
  notice_number: "",
  source_url: "",
  title: "",
  customer_name: "",
  deadline: "",
  max_price: "",
  auto_analyze: true,
  include_ai_summary: false
};

type InputsPayload = {
  inputs: TenderInputListItem[];
  analyses: AnalysisListItem[];
};

export default function InputsPage() {
  const [companyProfileId, setCompanyProfileId] = useState<number | null>(null);
  const [importForm, setImportForm] = useState(importDefaults);
  const [manualFiles, setManualFiles] = useState<File[]>([]);
  const [includeAiSummary, setIncludeAiSummary] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmittingImport, setIsSubmittingImport] = useState(false);
  const [isSubmittingUpload, setIsSubmittingUpload] = useState(false);

  const inputsQuery = useLiveResource<InputsPayload>({
    loader: useCallback(
      () =>
        Promise.all([api.listTenderInputs(), api.listAnalyses()]).then(([inputs, analyses]) => ({
          inputs,
          analyses
        })),
      []
    ),
    refreshIntervalMs: 4000,
    shouldRefresh: (data) => (data?.analyses ?? []).some((analysis) => isPendingAnalysisStatus(analysis.status))
  });

  useEffect(() => {
    setCompanyProfileId(readActiveProfileId());
  }, []);

  const inputs = inputsQuery.data?.inputs ?? [];
  const analyses = inputsQuery.data?.analyses ?? [];
  const analysesById = useMemo(
    () => new Map(analyses.map((analysis) => [analysis.id, analysis])),
    [analyses]
  );
  const activeAnalysesCount = analyses.filter((analysis) => isPendingAnalysisStatus(analysis.status)).length;

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (!companyProfileId) {
      setError("Сначала выбери активный профиль компании на странице профилей.");
      return;
    }

    setIsSubmittingImport(true);
    try {
      const tenderInput = await api.importTenderInput({
        company_profile_id: companyProfileId,
        notice_number: importForm.notice_number || null,
        source_url: importForm.source_url || null,
        title: importForm.title || null,
        customer_name: importForm.customer_name || null,
        deadline: importForm.deadline || null,
        max_price: importForm.max_price || null,
        auto_analyze: importForm.auto_analyze,
        include_ai_summary: importForm.include_ai_summary
      });

      await inputsQuery.refresh();
      setImportForm(importDefaults);
      setMessage(
        tenderInput.latest_analysis_id
          ? `TenderInput #${tenderInput.id} создан, анализ #${tenderInput.latest_analysis_id} уже поставлен в очередь.`
          : `TenderInput #${tenderInput.id} создан.`
      );
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось импортировать закупку");
    } finally {
      setIsSubmittingImport(false);
    }
  }

  async function handleManualUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (!companyProfileId) {
      setError("Сначала выбери активный профиль компании на странице профилей.");
      return;
    }

    if (!manualFiles.length) {
      setError("Добавь хотя бы один файл для анализа.");
      return;
    }

    setIsSubmittingUpload(true);
    try {
      const analysis = await api.createAnalysisFromFiles(companyProfileId, manualFiles, includeAiSummary);

      await inputsQuery.refresh();
      setManualFiles([]);
      setIncludeAiSummary(false);
      setMessage(`Анализ #${analysis.id} поставлен в обработку. Карточка будет обновляться автоматически.`);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Не удалось загрузить пакет документов"
      );
    } finally {
      setIsSubmittingUpload(false);
    }
  }

  async function handleQueueAnalysis(tenderInputId: number) {
    setMessage(null);
    setError(null);

    try {
      const analysis = await api.queueAnalysisFromTenderInput(tenderInputId, {
        include_ai_summary: false
      });
      await inputsQuery.refresh();
      setMessage(`Для TenderInput #${tenderInputId} создан анализ #${analysis.id}.`);
    } catch (queueError) {
      setError(queueError instanceof Error ? queueError.message : "Не удалось поставить анализ в очередь");
    }
  }

  if (inputsQuery.isLoading && !inputsQuery.data) {
    return (
      <LoadingPanel
        title="Готовим экран импорта"
        description="Подтягиваем уже созданные TenderInput и связанные анализы, чтобы показать живые статусы."
      />
    );
  }

  return (
    <div className="stack">
      <div className="section-heading">
        <div className="section-copy">
          <p className="eyebrow">Ingestion</p>
          <h3>Импорт закупок и ручная загрузка документов</h3>
          <p className="muted">
            Пока анализ выполняется, очередь обновляется автоматически и не скрывает уже
            загруженные карточки.
          </p>
        </div>
        <LiveBadge isRefreshing={inputsQuery.isRefreshing} lastUpdated={inputsQuery.lastUpdated} />
      </div>

      {activeAnalysesCount ? (
        <section className="panel status-banner">
          <strong>Сейчас анализируется {activeAnalysesCount} кейс(ов).</strong>
          <span className="muted">
            Можно продолжать работу в интерфейсе: результаты подтянутся автоматически.
          </span>
        </section>
      ) : null}

      {companyProfileId ? null : (
        <section className="panel error-banner">
          Активный профиль компании не выбран. Сначала зайди на страницу профилей и нажми
          “Сделать активным”.
        </section>
      )}

      {message ? <section className="panel success-banner">{message}</section> : null}
      {error ? <section className="panel error-banner">{error}</section> : null}
      {inputsQuery.error ? <section className="panel error-banner">{inputsQuery.error}</section> : null}

      <div className="section-grid two-columns">
        <section className="panel section">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Импорт по номеру или ссылке</p>
              <h3>Создать TenderInput</h3>
            </div>
          </div>

          <form className="field-grid" onSubmit={handleImport}>
            <label>
              <span>Активный профиль компании</span>
              <input value={companyProfileId ?? ""} disabled />
            </label>

            <label>
              <span>Номер закупки</span>
              <input
                value={importForm.notice_number}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, notice_number: event.target.value }))
                }
              />
            </label>

            <label>
              <span>Ссылка на источник</span>
              <input
                value={importForm.source_url}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, source_url: event.target.value }))
                }
              />
            </label>

            <label>
              <span>Название закупки</span>
              <input
                value={importForm.title}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, title: event.target.value }))
                }
              />
            </label>

            <label>
              <span>Заказчик</span>
              <input
                value={importForm.customer_name}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, customer_name: event.target.value }))
                }
              />
            </label>

            <label>
              <span>Срок подачи</span>
              <input
                type="datetime-local"
                value={importForm.deadline}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, deadline: event.target.value }))
                }
              />
            </label>

            <label>
              <span>НМЦК</span>
              <input
                value={importForm.max_price}
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, max_price: event.target.value }))
                }
              />
            </label>

            <label className="checkbox-row">
              <input
                checked={importForm.auto_analyze}
                type="checkbox"
                onChange={(event) =>
                  setImportForm((current) => ({ ...current, auto_analyze: event.target.checked }))
                }
              />
              <span>Сразу запускать анализ</span>
            </label>

            <label className="checkbox-row">
              <input
                checked={importForm.include_ai_summary}
                type="checkbox"
                onChange={(event) =>
                  setImportForm((current) => ({
                    ...current,
                    include_ai_summary: event.target.checked
                  }))
                }
              />
              <span>Запрашивать AI summary</span>
            </label>

            <button className="button field-full" disabled={isSubmittingImport} type="submit">
              {isSubmittingImport ? "Создаем TenderInput..." : "Импортировать закупку"}
            </button>
          </form>
        </section>

        <section className="panel section">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Manual upload</p>
              <h3>Загрузить пакет файлов</h3>
            </div>
          </div>

          <form className="field-grid" onSubmit={handleManualUpload}>
            <label className="field-full">
              <span>Файлы закупки</span>
              <input
                multiple
                type="file"
                onChange={(event) => setManualFiles(Array.from(event.target.files ?? []))}
              />
            </label>

            <label className="checkbox-row field-full">
              <input
                checked={includeAiSummary}
                type="checkbox"
                onChange={(event) => setIncludeAiSummary(event.target.checked)}
              />
              <span>Добавить AI summary после анализа</span>
            </label>

            <button className="button field-full" disabled={isSubmittingUpload} type="submit">
              {isSubmittingUpload ? "Отправляем пакет..." : "Загрузить и отправить в очередь"}
            </button>
          </form>

          {manualFiles.length ? (
            <div className="upload-preview">
              <p className="eyebrow">Пакет документов</p>
              {manualFiles.map((file) => (
                <span className="break-anywhere" key={`${file.name}-${file.size}`} title={file.name}>
                  {file.name}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      </div>

      <section className="panel section">
        <div className="section-heading">
          <div className="section-copy">
            <p className="eyebrow">Очередь входных данных</p>
            <h3>TenderInput и связанные анализы</h3>
          </div>
        </div>

        {inputs.length ? (
          <div className="cards compact-cards">
            {inputs.map((item) => {
              const analysis = item.latest_analysis_id
                ? analysesById.get(item.latest_analysis_id) ?? null
                : null;

              return (
                <article className="card compact-card" key={item.id}>
                  <p className="eyebrow">#{item.id}</p>
                  <h4 className="truncate-3" title={item.title}>
                    {item.title}
                  </h4>
                  {analysis ? <StatusPill value={analysis.status} /> : <StatusPill value={item.status} />}
                  <span className="muted break-anywhere" title={item.source_value}>
                    Источник: {item.source_value}
                  </span>
                  <span className="muted">Создан: {formatDate(item.created_at)}</span>
                  <span className="muted">
                    Анализ: {analysis ? `#${analysis.id}` : "еще не создан"}
                  </span>

                  {analysis ? (
                    <Link href={`/analyses/${analysis.id}`}>Открыть анализ</Link>
                  ) : (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => void handleQueueAnalysis(item.id)}
                    >
                      Запустить анализ
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="Очередь пока пуста"
            description="Импортируй закупку по номеру или ссылке, либо загрузи пакет документов вручную."
          />
        )}
      </section>
    </div>
  );
}
