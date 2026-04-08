"use client";

import Link from "next/link";
import { useCallback } from "react";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { AnalysisListItem } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import { formatDate, isPendingAnalysisStatus } from "@/lib/utils";

export default function AnalysesPage() {
  const analyses = useLiveResource<AnalysisListItem[]>({
    loader: useCallback(() => api.listAnalyses(), []),
    refreshIntervalMs: 4000,
    shouldRefresh: (data) =>
      (data ?? []).some((analysis) => isPendingAnalysisStatus(analysis.status))
  });

  if (analyses.isLoading && !analyses.data) {
    return (
      <LoadingPanel
        title="Загружаем реестр анализов"
        description="Подготавливаем список кейсов, статусы и ссылки на подробные карточки."
      />
    );
  }

  const rows = analyses.data ?? [];
  const activeCount = rows.filter((analysis) => isPendingAnalysisStatus(analysis.status)).length;

  return (
    <section className="section panel">
      <div className="section-heading">
        <div className="section-copy">
          <p className="eyebrow">Реестр</p>
          <h3>Все анализы закупок</h3>
          <p className="muted">
            Пока есть активные задачи, список обновляется автоматически без очистки уже
            показанных данных.
          </p>
        </div>
        <LiveBadge isRefreshing={analyses.isRefreshing} lastUpdated={analyses.lastUpdated} />
      </div>

      {activeCount ? (
        <div className="status-banner subtle-banner">
          В обработке сейчас {activeCount} анализ(ов). Как только backend завершит задачу, статус
          здесь обновится автоматически.
        </div>
      ) : null}

      {analyses.error ? <p className="error-banner">{analyses.error}</p> : null}

      {rows.length ? (
        <div className="table-wrap">
          <table className="table-analyses">
            <thead>
              <tr>
                <th>ID</th>
                <th>Пакет</th>
                <th>Статус</th>
                <th>Закупка</th>
                <th className="date-column">Создан</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((analysis) => (
                <tr key={analysis.id}>
                  <td>#{analysis.id}</td>
                  <td>
                    <strong className="truncate-2" title={analysis.package_name}>
                      {analysis.package_name}
                    </strong>
                    <div
                      className="muted truncate-3"
                      title={analysis.object_name ?? "Наименование уточняется"}
                    >
                      {analysis.object_name ?? "Наименование уточняется"}
                    </div>
                  </td>
                  <td>
                    <StatusPill value={analysis.status} />
                  </td>
                  <td>{analysis.notice_number ?? "Без номера извещения"}</td>
                  <td className="date-column">{formatDate(analysis.created_at)}</td>
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
          title="Анализы еще не запускались"
          description="Создай профиль компании и импортируй закупку, чтобы здесь появился первый кейс."
          action={
            <Link className="button button-secondary" href="/inputs">
              Перейти к импорту
            </Link>
          }
        />
      )}
    </section>
  );
}
