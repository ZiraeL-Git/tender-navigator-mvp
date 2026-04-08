import { ReactNode } from "react";

import { formatDate } from "@/lib/utils";

type LiveBadgeProps = {
  isRefreshing?: boolean;
  lastUpdated?: string | null;
};

export function LiveBadge({ isRefreshing = false, lastUpdated = null }: LiveBadgeProps) {
  return (
    <div className={`live-badge${isRefreshing ? " live-badge-active" : ""}`}>
      <span className="live-dot" />
      <span>{isRefreshing ? "Обновляем данные..." : "Данные загружены"}</span>
      {lastUpdated ? <span className="muted">Обновлено: {formatDate(lastUpdated)}</span> : null}
    </div>
  );
}

type LoadingPanelProps = {
  title: string;
  description: string;
};

export function LoadingPanel({ title, description }: LoadingPanelProps) {
  return (
    <section className="panel section loading-panel">
      <div className="section-copy">
        <p className="eyebrow">Загрузка</p>
        <h3>{title}</h3>
        <p className="muted">{description}</p>
      </div>

      <div className="skeleton-grid">
        <div className="skeleton-card" />
        <div className="skeleton-card" />
        <div className="skeleton-card" />
      </div>
    </section>
  );
}

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h4>{title}</h4>
      <p className="muted">{description}</p>
      {action ? <div className="inline-actions">{action}</div> : null}
    </div>
  );
}
