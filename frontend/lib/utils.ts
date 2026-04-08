const STATUS_LABELS: Record<string, string> = {
  queued: "В очереди",
  processing: "В обработке",
  analyzed: "Проанализировано",
  manual_reviewed: "Проверено вручную",
  failed: "Ошибка",
  imported: "Импортировано",
  go: "GO",
  risk: "RISK",
  manual_review: "Требует проверки",
  stop: "STOP",
  ok: "OK"
};

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat("ru-RU", {
      dateStyle: "medium",
      timeStyle: "short"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatStatus(status: string | null | undefined): string {
  if (!status) {
    return "Без статуса";
  }

  return STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

const EXTRACTED_FIELD_LABELS: Record<string, string> = {
  notice_number: "Номер извещения",
  object_name: "Объект закупки",
  customer_name: "Заказчик",
  price: "Цена",
  deadline: "Срок подачи",
  supply_term: "Срок поставки",
  bid_security: "Обеспечение заявки",
  contract_security: "Обеспечение контракта",
  quality_guarantee: "Гарантия качества",
  need_license: "Требуется лицензия",
  need_experience: "Требуется подтвержденный опыт"
};

export function toCommaSeparated(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

export function isPendingAnalysisStatus(status: string | null | undefined): boolean {
  return status === "queued" || status === "processing";
}

export function isFinishedAnalysisStatus(status: string | null | undefined): boolean {
  return !isPendingAnalysisStatus(status);
}

export function getAnalysisProgressLabel(status: string | null | undefined): string {
  if (status === "queued") {
    return "Задача поставлена в очередь и скоро начнет обработку.";
  }

  if (status === "processing") {
    return "Документы анализируются. Экран обновляется автоматически.";
  }

  if (status === "failed") {
    return "Анализ завершился с ошибкой.";
  }

  if (status === "manual_reviewed") {
    return "Результат подтвержден или скорректирован оператором.";
  }

  if (status === "analyzed") {
    return "Анализ завершен, можно изучать решение и чек-лист.";
  }

  return "Состояние обновляется автоматически.";
}

export function getExtractedFieldLabel(field: string): string {
  return EXTRACTED_FIELD_LABELS[field] ?? field;
}
