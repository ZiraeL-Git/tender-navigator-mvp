import { formatStatus } from "@/lib/utils";

type StatusPillProps = {
  value: string | null | undefined;
};

export function StatusPill({ value }: StatusPillProps) {
  const normalized = (value ?? "unknown").toLowerCase();

  return <span className={`status-pill status-${normalized}`}>{formatStatus(value)}</span>;
}
