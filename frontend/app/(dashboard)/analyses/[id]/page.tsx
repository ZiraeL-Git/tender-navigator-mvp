"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { Analysis } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import {
  formatDate,
  getExtractedFieldLabel,
  getAnalysisProgressLabel,
  isFinishedAnalysisStatus,
  isPendingAnalysisStatus
} from "@/lib/utils";

type ManualCorrectionState = {
  decisionCode: string;
  decisionLabel: string;
  aiSummary: string;
  checklistText: string;
  comment: string;
};

const initialForm: ManualCorrectionState = {
  decisionCode: "",
  decisionLabel: "",
  aiSummary: "",
  checklistText: "",
  comment: ""
};

export default function AnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const analysisId = Number(params.id);
  const [form, setForm] = useState<ManualCorrectionState>(initialForm);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const analysisQuery = useLiveResource<Analysis>({
    loader: useCallback(() => api.getAnalysis(analysisId), [analysisId]),
    enabled: Number.isFinite(analysisId),
    refreshIntervalMs: 3000,
    shouldRefresh: (analysis) => isPendingAnalysisStatus(analysis?.status)
  });

  useEffect(() => {
    if (!analysisQuery.data || isDirty) {
      return;
    }

    setForm({
      decisionCode: analysisQuery.data.decision_code ?? "",
      decisionLabel: analysisQuery.data.decision_label ?? "",
      aiSummary: analysisQuery.data.ai_summary ?? "",
      checklistText: analysisQuery.data.checklist.join("\n"),
      comment: ""
    });
  }, [
    analysisQuery.data,
    analysisQuery.data?.ai_summary,
    analysisQuery.data?.checklist,
    analysisQuery.data?.decision_code,
    analysisQuery.data?.decision_label,
    isDirty
  ]);

  useEffect(() => {
    setIsDirty(false);
    setMessage(null);
    setError(null);
  }, [analysisId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!analysisQuery.data) {
      return;
    }

    setMessage(null);
    setError(null);
    setIsSaving(true);

    try {
      const updated = await api.patchManualCorrection(analysisQuery.data.id, {
        decision_code: form.decisionCode || null,
        decision_label: form.decisionLabel || null,
        ai_summary: form.aiSummary || null,
        checklist: form.checklistText
          .split("\n")
          .map((item: string) => item.trim())
          .filter(Boolean),
        extracted: analysisQuery.data.extracted,
        comment: form.comment
      });

      analysisQuery.replaceData(updated);
      setMessage("Ручная корректировка сохранена.");
      setIsDirty(false);
      setForm((current) => ({ ...current, comment: "" }));
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Не удалось сохранить корректировку"
      );
    } finally {
      setIsSaving(false);
    }
  }

  if (!Number.isFinite(analysisId)) {
    return <section className="panel error-banner">Некорректный идентификатор анализа.</section>;
  }

  if (analysisQuery.isLoading && !analysisQuery.data) {
    return (
      <LoadingPanel
        title="Открываем карточку анализа"
        description="Подтягиваем статус обработки, извлеченные поля, причины решения и ленту событий."
      />
    );
  }

  if (!analysisQuery.data) {
    return (
      <section className="panel section">
        <EmptyState
          title="Анализ не найден"
          description="Похоже, карточка была удалена или идентификатор указан неверно."
        />
      </section>
    );
  }

  const analysis = analysisQuery.data;

  return (
    <div className="stack">
      <div className="section-heading">
        <div className="section-copy">
          <p className="eyebrow">Анализ #{analysis.id}</p>
          <h3 className="break-anywhere" title={analysis.package_name}>
            {analysis.package_name}
          </h3>
          <p className="muted">{getAnalysisProgressLabel(analysis.status)}</p>
        </div>
        <LiveBadge isRefreshing={analysisQuery.isRefreshing} lastUpdated={analysisQuery.lastUpdated} />
      </div>

      <section className="panel status-banner">
        <div className="status-banner-row">
          <StatusPill value={analysis.status} />
          <span className="muted">
            {analysis.decision_label
              ? `Итоговое решение: ${analysis.decision_label}`
              : "Решение появится после завершения обработки."}
          </span>
        </div>
      </section>

      {analysis.failure_reason ? (
        <section className="panel error-banner">Ошибка анализа: {analysis.failure_reason}</section>
      ) : null}

      {analysisQuery.error ? <section className="panel error-banner">{analysisQuery.error}</section> : null}
      {message ? <section className="panel success-banner">{message}</section> : null}
      {error ? <section className="panel error-banner">{error}</section> : null}

      <div className="detail-grid">
        <section className="stack">
          <article className="panel section">
            <div className="cards">
              <div className="card compact-card">
                <p className="eyebrow">Создан</p>
                <strong>{formatDate(analysis.created_at)}</strong>
              </div>
              <div className="card compact-card">
                <p className="eyebrow">Старт</p>
                <strong>{formatDate(analysis.started_at)}</strong>
              </div>
              <div className="card compact-card">
                <p className="eyebrow">Завершен</p>
                <strong>{formatDate(analysis.completed_at)}</strong>
              </div>
            </div>
          </article>

          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">Explainability</p>
                <h3>Причины решения</h3>
              </div>
            </div>

            {analysis.decision_reasons.length ? (
              <div className="cards compact-cards">
                {analysis.decision_reasons.map((reason) => (
                  <div className="card compact-card" key={`${reason.rule_id}-${reason.code}`}>
                    <StatusPill value={reason.decision_code} />
                    <strong className="break-anywhere">{reason.message}</strong>
                    <span className="muted">Правило: {reason.rule_id}</span>
                    <span className="muted">{reason.rule_title}</span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Причины решения пока не сформированы"
                description="Если анализ еще выполняется, rule engine заполнит этот блок автоматически."
              />
            )}
          </article>

          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">Извлеченные поля</p>
                <h3>Нормализованные данные</h3>
              </div>
            </div>

            <div className="detail-list">
              {Object.entries(analysis.extracted).map(([key, value]) => (
                <div className="detail-row" key={key}>
                  <span>{getExtractedFieldLabel(key)}</span>
                  <strong className="detail-value break-anywhere">
                    {value === null ? "Не найдено" : String(value)}
                  </strong>
                </div>
              ))}
            </div>
          </article>

          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">Результат</p>
                <h3>AI summary и checklist</h3>
              </div>
            </div>

            <div className="content-block">
              <strong>AI summary</strong>
              <p className="prewrap-text">
                {analysis.ai_summary ?? "AI summary пока не сформирован или не запрашивался."}
              </p>
            </div>

            <div className="content-block">
              <strong>Checklist</strong>
              {analysis.checklist.length ? (
                <ol className="checklist-list">
                  {analysis.checklist.map((item, index) => (
                    <li className="break-anywhere" key={`${item}-${index}`}>
                      {item}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="muted">Checklist пока не сформирован.</p>
              )}
            </div>
          </article>

          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">События</p>
                <h3>Лента обработки</h3>
              </div>
            </div>

            {analysis.events.length ? (
              <div className="timeline">
                {analysis.events.map((event, index) => (
                  <div className="timeline-item" key={`${event.event_type}-${event.created_at}-${index}`}>
                    <strong>{event.event_type}</strong>
                    <div className="muted">{formatDate(event.created_at)}</div>
                    {Object.keys(event.payload).length ? (
                      <pre className="code-block">{JSON.stringify(event.payload, null, 2)}</pre>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Событий пока нет"
                description="Лента заполнится по мере прохождения анализа через backend pipeline."
              />
            )}
          </article>
        </section>

        <section className="stack">
          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">Документы</p>
                <h3>Что попало в пакет</h3>
              </div>
            </div>

            {analysis.documents.length ? (
              <div className="cards compact-cards">
                {analysis.documents.map((document) => (
                  <div className="card compact-card" key={document.filename}>
                    <strong className="break-anywhere" title={document.filename}>
                      {document.filename}
                    </strong>
                    <span className="muted">Тип: {document.doc_type}</span>
                    <span className="muted">Символов текста: {document.text_length}</span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Документы еще не отображаются"
                description="Если анализ только стартовал, список документов появится после записи результата."
              />
            )}

            {analysis.warnings.length ? (
              <div className="notice warning">
                <strong>Warnings</strong>
                <ul className="list-clean">
                  {analysis.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {analysis.errors.length ? (
              <div className="notice danger">
                <strong>Errors</strong>
                <ul className="list-clean">
                  {analysis.errors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>

          <article className="panel section">
            <div className="section-heading">
              <div className="section-copy">
                <p className="eyebrow">Ручная корректировка</p>
                <h3>Подтверждение результата оператором</h3>
              </div>
            </div>

            {isFinishedAnalysisStatus(analysis.status) ? (
              <form className="field-grid" onSubmit={handleSubmit}>
                <label>
                  <span>Decision code</span>
                  <select
                    value={form.decisionCode}
                    onChange={(event) => {
                      setIsDirty(true);
                      setForm((current) => ({ ...current, decisionCode: event.target.value }));
                    }}
                  >
                    <option value="">Не менять</option>
                    <option value="go">GO</option>
                    <option value="risk">RISK</option>
                    <option value="manual_review">MANUAL_REVIEW</option>
                    <option value="stop">STOP</option>
                  </select>
                </label>

                <label>
                  <span>Заголовок решения</span>
                  <input
                    value={form.decisionLabel}
                    onChange={(event) => {
                      setIsDirty(true);
                      setForm((current) => ({ ...current, decisionLabel: event.target.value }));
                    }}
                  />
                </label>

                <label className="field-full">
                  <span>Checklist, по одному пункту на строку</span>
                  <textarea
                    rows={6}
                    value={form.checklistText}
                    onChange={(event) => {
                      setIsDirty(true);
                      setForm((current) => ({ ...current, checklistText: event.target.value }));
                    }}
                  />
                </label>

                <label className="field-full">
                  <span>AI summary</span>
                  <textarea
                    rows={7}
                    value={form.aiSummary}
                    onChange={(event) => {
                      setIsDirty(true);
                      setForm((current) => ({ ...current, aiSummary: event.target.value }));
                    }}
                  />
                </label>

                <label className="field-full">
                  <span>Комментарий оператора</span>
                  <textarea
                    rows={4}
                    value={form.comment}
                    onChange={(event) => {
                      setIsDirty(true);
                      setForm((current) => ({ ...current, comment: event.target.value }));
                    }}
                  />
                </label>

                <button className="button field-full" disabled={isSaving} type="submit">
                  {isSaving ? "Сохраняем..." : "Сохранить корректировку"}
                </button>
              </form>
            ) : (
              <EmptyState
                title="Форма откроется после завершения анализа"
                description="Пока задача в очереди или в обработке, карточка автоматически обновляется и ждет итогового результата."
              />
            )}
          </article>
        </section>
      </div>
    </div>
  );
}
