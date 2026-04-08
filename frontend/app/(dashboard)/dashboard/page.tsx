"use client";

import Link from "next/link";
import { useCallback } from "react";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { AnalysisListItem, CompanyProfile, TenderInputListItem } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import { formatDate, isPendingAnalysisStatus } from "@/lib/utils";

type DashboardPayload = {
  profiles: CompanyProfile[];
  analyses: AnalysisListItem[];
  inputs: TenderInputListItem[];
};

export default function DashboardPage() {
  const loadDashboard = useCallback(
    () =>
      Promise.all([api.listCompanyProfiles(), api.listAnalyses(), api.listTenderInputs()]).then(
        ([profiles, analyses, inputs]) => ({
          profiles,
          analyses,
          inputs
        })
      ),
    []
  );

  const dashboard = useLiveResource<DashboardPayload>({
    loader: loadDashboard,
    refreshIntervalMs: 4000,
    shouldRefresh: (data) =>
      (data?.analyses ?? []).some((analysis) => isPendingAnalysisStatus(analysis.status))
  });

  if (dashboard.isLoading && !dashboard.data) {
    return (
      <LoadingPanel
        title="Собираем рабочую сводку"
        description="Подтягиваем профили компаний, импортированные закупки и последние анализы."
      />
    );
  }

  const profiles = dashboard.data?.profiles ?? [];
  const analyses = dashboard.data?.analyses ?? [];
  const inputs = dashboard.data?.inputs ?? [];
  const activeAnalyses = analyses.filter((analysis) => isPendingAnalysisStatus(analysis.status));

  return (
    <div className="stack">
      <div className="section-heading">
        <div className="section-copy">
          <p className="eyebrow">Операционная сводка</p>
          <h3>Текущий контур работы</h3>
          <p className="muted">
            Дашборд обновляется автоматически, пока в системе есть анализы в очереди или в
            обработке.
          </p>
        </div>
        <LiveBadge isRefreshing={dashboard.isRefreshing} lastUpdated={dashboard.lastUpdated} />
      </div>

      {activeAnalyses.length ? (
        <section className="panel status-banner">
          <strong>Сейчас обрабатывается {activeAnalyses.length} анализ(ов).</strong>
          <span className="muted">
            Данные на экране обновляются в фоне и больше не очищаются во время обработки.
          </span>
        </section>
      ) : null}

      {dashboard.error ? <section className="panel error-banner">{dashboard.error}</section> : null}

      <section className="cards metrics-grid">
        <article className="card metric-card">
          <p className="eyebrow">Профили</p>
          <strong className="card-value">{profiles.length}</strong>
          <span className="muted">Карточки компаний, доступные для анализа</span>
        </article>

        <article className="card metric-card">
          <p className="eyebrow">Анализы</p>
          <strong className="card-value">{analyses.length}</strong>
          <span className="muted">Все кейсы, прошедшие через backend pipeline</span>
        </article>

        <article className="card metric-card">
          <p className="eyebrow">В работе</p>
          <strong className="card-value">{activeAnalyses.length}</strong>
          <span className="muted">Очередь и текущая фоновая обработка документов</span>
        </article>
      </section>

      <div className="section-grid dashboard-main-grid">
        <section className="section panel">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Последние анализы</p>
              <h3>Что уже обработано</h3>
            </div>
            <Link className="button button-secondary" href="/analyses">
              Открыть реестр
            </Link>
          </div>

          {analyses.length ? (
            <div className="table-wrap">
              <table className="table-analyses">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Пакет</th>
                    <th>Статус</th>
                    <th>Срок подачи</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.slice(0, 5).map((analysis) => (
                    <tr key={analysis.id}>
                      <td>#{analysis.id}</td>
                      <td>
                        <strong className="truncate-2" title={analysis.package_name}>
                          {analysis.package_name}
                        </strong>
                        <div
                          className="muted truncate-3"
                          title={analysis.object_name ?? "Объект закупки уточняется"}
                        >
                          {analysis.object_name ?? "Объект закупки уточняется"}
                        </div>
                      </td>
                      <td>
                        <StatusPill value={analysis.status} />
                      </td>
                      <td>{analysis.deadline ?? "Еще не извлечен"}</td>
                      <td>
                        <Link href={`/analyses/${analysis.id}`}>Открыть</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="Анализов пока нет"
              description="После импорта закупки здесь появятся последние результаты и статусы обработки."
              action={
                <Link className="button button-secondary" href="/inputs">
                  Перейти к импорту
                </Link>
              }
            />
          )}
        </section>

        <section className="section panel">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Свежие закупки</p>
              <h3>Последние TenderInput</h3>
            </div>
            <Link className="button button-secondary" href="/inputs">
              Открыть импорт
            </Link>
          </div>

          {inputs.length ? (
            <div className="cards fresh-inputs-grid">
              {inputs.slice(0, 4).map((item) => (
                <article className="card compact-card" key={item.id}>
                  <p className="eyebrow">{item.notice_number ?? item.source_type}</p>
                  <h4 className="truncate-3" title={item.title}>
                    {item.title}
                  </h4>
                  <span className="muted">Создано: {formatDate(item.created_at)}</span>
                  <span className="muted">
                    Анализ: {item.latest_analysis_id ? `#${item.latest_analysis_id}` : "еще не создан"}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Импортов пока нет"
              description="Начни с номера закупки, ссылки на источник или ручной загрузки документов."
            />
          )}
        </section>
      </div>
    </div>
  );
}
