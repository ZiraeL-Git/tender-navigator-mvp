"use client";

import Link from "next/link";
import type { Route } from "next";
import { FormEvent, useCallback, useMemo, useState } from "react";

import { EmptyState, LiveBadge, LoadingPanel } from "@/components/async-state";
import { readSession } from "@/components/auth";
import { api } from "@/lib/api";
import { AuditLog, AuthUser, Invitation } from "@/lib/types";
import { useLiveResource } from "@/lib/use-live-resource";
import { formatDate } from "@/lib/utils";

type TeamPayload = {
  users: AuthUser[];
  invitations: Invitation[];
  auditLogs: AuditLog[];
};

const initialInvite = {
  email: "",
  role: "operator" as "owner" | "operator" | "viewer"
};

function getRoleLabel(role: string): string {
  if (role === "owner") {
    return "Владелец";
  }
  if (role === "viewer") {
    return "Наблюдатель";
  }
  return "Оператор";
}

export default function TeamPage() {
  const session = readSession();
  const isOwner = session?.user.role === "owner";
  const [invite, setInvite] = useState(initialInvite);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadTeam = useCallback(
    () =>
      Promise.all([api.listOrganizationUsers(), api.listInvitations(), api.listAuditLogs(25)]).then(
        ([users, invitations, auditLogs]) => ({
          users,
          invitations,
          auditLogs
        })
      ),
    []
  );

  const team = useLiveResource<TeamPayload>({
    loader: loadTeam,
    refreshIntervalMs: 5000
  });

  const pendingInvitations = useMemo(
    () => (team.data?.invitations ?? []).filter((item) => item.status === "pending"),
    [team.data?.invitations]
  );

  async function handleInviteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!invite.email.trim()) {
      return;
    }

    setMessage(null);
    setError(null);
    setIsSubmitting(true);

    try {
      const created = await api.createInvitation({
        email: invite.email.trim(),
        role: invite.role
      });
      await team.refresh();
      setInvite(initialInvite);
      setMessage(`Приглашение для ${created.email} создано.`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось создать приглашение");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (team.isLoading && !team.data) {
    return (
      <LoadingPanel
        title="Открываем рабочую команду"
        description="Подтягиваем пользователей, приглашения и последние записи audit trail."
      />
    );
  }

  const users = team.data?.users ?? [];
  const auditLogs = team.data?.auditLogs ?? [];

  return (
    <div className="stack">
      <div className="section-heading">
        <div className="section-copy">
          <p className="eyebrow">Командный контур</p>
          <h3>Пользователи, приглашения и журнал действий</h3>
          <p className="muted">
            Этот экран помогает управлять доступом внутри организации и быстро разбирать, кто что
            делал в системе.
          </p>
        </div>
        <LiveBadge isRefreshing={team.isRefreshing} lastUpdated={team.lastUpdated} />
      </div>

      {message ? <section className="panel success-banner">{message}</section> : null}
      {error ? <section className="panel error-banner">{error}</section> : null}
      {team.error ? <section className="panel error-banner">{team.error}</section> : null}

      <section className="cards metrics-grid">
        <article className="card metric-card">
          <p className="eyebrow">Участники</p>
          <strong className="card-value">{users.length}</strong>
          <span className="muted">Все пользователи организации</span>
        </article>

        <article className="card metric-card">
          <p className="eyebrow">Ожидают входа</p>
          <strong className="card-value">{pendingInvitations.length}</strong>
          <span className="muted">Приглашения в статусе pending</span>
        </article>

        <article className="card metric-card">
          <p className="eyebrow">Audit trail</p>
          <strong className="card-value">{auditLogs.length}</strong>
          <span className="muted">Последние события команды и операционного контура</span>
        </article>
      </section>

      <div className="section-grid two-columns">
        <section className="panel section">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Пользователи</p>
              <h3>Кто уже работает внутри организации</h3>
            </div>
          </div>

          {users.length ? (
            <div className="cards fresh-inputs-grid">
              {users.map((user) => (
                <article className="card compact-card" key={user.id}>
                  <p className="eyebrow">{getRoleLabel(user.role)}</p>
                  <strong>{user.full_name ?? user.email}</strong>
                  <span className="muted">{user.email}</span>
                  <span className="muted">
                    Статус: {user.is_active ? "активен" : "отключен"}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Пользователей пока нет"
              description="После создания первого owner-аккаунта и принятия приглашений команда появится здесь."
            />
          )}
        </section>

        <section className="panel section">
          <div className="section-heading">
            <div className="section-copy">
              <p className="eyebrow">Приглашения</p>
              <h3>Новые участники команды</h3>
            </div>
          </div>

          {isOwner ? (
            <form className="field-grid" onSubmit={handleInviteSubmit}>
              <label>
                <span>Email</span>
                <input
                  type="email"
                  value={invite.email}
                  onChange={(event) => setInvite((current) => ({ ...current, email: event.target.value }))}
                />
              </label>

              <label>
                <span>Роль</span>
                <select
                  value={invite.role}
                  onChange={(event) =>
                    setInvite((current) => ({
                      ...current,
                      role: event.target.value as "owner" | "operator" | "viewer"
                    }))
                  }
                >
                  <option value="operator">Оператор</option>
                  <option value="viewer">Наблюдатель</option>
                  <option value="owner">Владелец</option>
                </select>
              </label>

              <button className="button field-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Создаем приглашение..." : "Пригласить участника"}
              </button>
            </form>
          ) : (
            <div className="empty-state">
              <strong>Приглашения доступны владельцу организации</strong>
              <p className="muted">
                Ты можешь видеть список пользователей и audit trail, но создавать новых участников
                может только owner.
              </p>
            </div>
          )}

          {team.data?.invitations?.length ? (
            <div className="cards fresh-inputs-grid">
              {team.data.invitations.slice(0, 6).map((invitation) => (
                <article className="card compact-card" key={invitation.id}>
                  <p className="eyebrow">{getRoleLabel(invitation.role)}</p>
                  <strong>{invitation.email}</strong>
                  <span className="muted">Статус: {invitation.status}</span>
                  <span className="muted">Создано: {formatDate(invitation.created_at)}</span>
                  <span className="muted">Действует до: {formatDate(invitation.expires_at)}</span>
                  {invitation.status === "pending" ? (
                    <Link className="button button-secondary" href={`/invite/${invitation.token}` as Route}>
                      Открыть ссылку приглашения
                    </Link>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Приглашений пока нет"
              description="Когда появятся новые участники, pending и accepted invitations будут показаны здесь."
            />
          )}
        </section>
      </div>

      <section className="panel section">
        <div className="section-heading">
          <div className="section-copy">
            <p className="eyebrow">Audit Trail</p>
            <h3>Последние действия в системе</h3>
          </div>
        </div>

        {auditLogs.length ? (
          <div className="timeline">
            {auditLogs.map((log) => (
              <div className="timeline-item" key={log.id}>
                <strong>{log.action}</strong>
                <div className="muted">
                  {log.actor_user?.full_name ?? log.actor_user?.email ?? "Системное действие"} ·{" "}
                  {formatDate(log.created_at)}
                </div>
                <div className="muted">
                  Сущность: {log.entity_type}
                  {log.entity_id ? ` #${log.entity_id}` : ""}
                </div>
                {Object.keys(log.payload).length ? (
                  <pre className="code-block">{JSON.stringify(log.payload, null, 2)}</pre>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Audit trail пока пуст"
            description="После действий команды и оператора здесь появится хронология изменений."
          />
        )}
      </section>
    </div>
  );
}
