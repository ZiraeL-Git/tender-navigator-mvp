from schemas import (
    CompanyProfile,
    DecisionCode,
    DecisionReason,
    ReasonSeverity,
    TenderExtractedFields,
)


def make_decision(
    extracted: TenderExtractedFields,
    profile: CompanyProfile,
) -> tuple[DecisionCode, str, list[DecisionReason]]:
    reasons: list[DecisionReason] = []

    if extracted.need_license and not profile.has_license:
        reasons.append(
            DecisionReason(
                code="missing_license",
                severity=ReasonSeverity.stop,
                message="Обнаружено требование лицензии / допуска, которого нет у компании.",
            )
        )
        return DecisionCode.reject, "НЕ ИДЕМ", reasons

    if extracted.need_experience and not profile.has_experience:
        reasons.append(
            DecisionReason(
                code="missing_experience",
                severity=ReasonSeverity.stop,
                message="Обнаружено требование подтвержденного опыта, которого у компании нет.",
            )
        )
        return DecisionCode.reject, "НЕ ИДЕМ", reasons

    if not extracted.deadline:
        reasons.append(
            DecisionReason(
                code="deadline_not_found",
                severity=ReasonSeverity.warning,
                message="Не удалось надежно определить срок подачи заявки, требуется ручная проверка.",
            )
        )
        return DecisionCode.manual_review, "ПРОВЕРИТЬ ВРУЧНУЮ", reasons

    if not profile.can_prepare_fast:
        reasons.append(
            DecisionReason(
                code="slow_preparation_risk",
                severity=ReasonSeverity.risk,
                message="Компания не готова быстро подготовить и подать заявку.",
            )
        )
        return DecisionCode.risk_review, "РИСК / ПРОВЕРИТЬ", reasons

    reasons.append(
        DecisionReason(
            code="no_critical_stop_factors",
            severity=ReasonSeverity.info,
            message="Критических стоп-факторов не найдено.",
        )
    )
    return DecisionCode.go, "ИДЕМ", reasons


def build_checklist(
    extracted: TenderExtractedFields,
    profile: CompanyProfile,
) -> list[str]:
    checklist = [
        "Проверить соответствие предмета закупки профилю компании",
        "Проверить срок окончания подачи заявки",
        "Проверить НМЦК и экономическую целесообразность участия",
        "Проверить полный состав обязательных документов",
    ]

    if extracted.need_license:
        if profile.has_license:
            checklist.append("Подготовить подтверждение лицензии / допуска")
        else:
            checklist.append("Проверить возможность участия: отсутствует требуемая лицензия / допуск")

    if extracted.need_experience:
        if profile.has_experience:
            checklist.append("Подготовить документы, подтверждающие релевантный опыт")
        else:
            checklist.append("Проверить возможность участия: нет подтвержденного релевантного опыта")

    if extracted.bid_security and extracted.bid_security.lower() == "требуется":
        checklist.append("Проверить необходимость и порядок предоставления обеспечения заявки")

    if extracted.contract_security and extracted.contract_security != "Не требуется":
        checklist.append(f"Проверить обеспечение исполнения контракта: {extracted.contract_security}")

    if extracted.quality_guarantee and extracted.quality_guarantee.lower() == "да":
        checklist.append("Проверить требования к гарантии качества товара / услуги")

    if not profile.can_prepare_fast:
        checklist.append("Оценить, успеет ли команда подготовить заявку в требуемый срок")

    checklist.append("Проверить проект контракта и риски по исполнению")

    return checklist