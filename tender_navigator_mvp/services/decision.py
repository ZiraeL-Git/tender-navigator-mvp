from dataclasses import dataclass
from typing import Callable

from schemas import (
    CompanyProfile,
    DecisionCode,
    DecisionReason,
    ReasonSeverity,
    TenderExtractedFields,
)


@dataclass(frozen=True)
class DecisionContext:
    extracted: TenderExtractedFields
    profile: CompanyProfile


@dataclass(frozen=True)
class DecisionRule:
    rule_id: str
    code: str
    title: str
    decision_code: DecisionCode
    severity: ReasonSeverity
    predicate: Callable[[DecisionContext], bool]
    message_builder: Callable[[DecisionContext], str]


DECISION_PRIORITY = {
    DecisionCode.stop: 0,
    DecisionCode.manual_review: 1,
    DecisionCode.risk: 2,
    DecisionCode.go: 3,
}


DECISION_LABELS = {
    DecisionCode.stop: "СТОП",
    DecisionCode.manual_review: "ПРОВЕРИТЬ ВРУЧНУЮ",
    DecisionCode.risk: "РИСК",
    DecisionCode.go: "ИДЕМ",
}


DECISION_RULES = [
    DecisionRule(
        rule_id="stop.missing_license_requirement",
        code="missing_license",
        title="Нет обязательной лицензии",
        decision_code=DecisionCode.stop,
        severity=ReasonSeverity.stop,
        predicate=lambda ctx: ctx.extracted.need_license and not ctx.profile.has_license,
        message_builder=lambda ctx: (
            "Обнаружено обязательное требование лицензии или допуска, "
            "но в профиле компании это требование не закрыто."
        ),
    ),
    DecisionRule(
        rule_id="stop.missing_confirmed_experience",
        code="missing_experience",
        title="Нет подтвержденного опыта",
        decision_code=DecisionCode.stop,
        severity=ReasonSeverity.stop,
        predicate=lambda ctx: ctx.extracted.need_experience and not ctx.profile.has_experience,
        message_builder=lambda ctx: (
            "Обнаружено требование подтвержденного опыта, "
            "но в профиле компании релевантный опыт не подтвержден."
        ),
    ),
    DecisionRule(
        rule_id="manual_review.deadline_missing",
        code="deadline_not_found",
        title="Не найден точный срок подачи",
        decision_code=DecisionCode.manual_review,
        severity=ReasonSeverity.warning,
        predicate=lambda ctx: not ctx.extracted.deadline,
        message_builder=lambda ctx: (
            "Не удалось надежно определить срок подачи заявки, "
            "поэтому требуется ручная проверка документации."
        ),
    ),
    DecisionRule(
        rule_id="risk.company_not_ready_for_fast_preparation",
        code="slow_preparation_risk",
        title="Есть риск не успеть подготовить заявку",
        decision_code=DecisionCode.risk,
        severity=ReasonSeverity.risk,
        predicate=lambda ctx: not ctx.profile.can_prepare_fast,
        message_builder=lambda ctx: (
            "Компания отмечена как не готовая быстро подготовить "
            "и подать заявку в требуемые сроки."
        ),
    ),
]


def build_decision_reason(rule: DecisionRule, context: DecisionContext) -> DecisionReason:
    return DecisionReason(
        code=rule.code,
        severity=rule.severity,
        message=rule.message_builder(context),
        rule_id=rule.rule_id,
        rule_title=rule.title,
        decision_code=rule.decision_code,
    )


def get_decision_label(decision_code: DecisionCode) -> str:
    return DECISION_LABELS[decision_code]


def get_primary_decision_code(reasons: list[DecisionReason]) -> DecisionCode:
    return min(reasons, key=lambda reason: DECISION_PRIORITY[reason.decision_code]).decision_code


def make_decision(
    extracted: TenderExtractedFields,
    profile: CompanyProfile,
) -> tuple[DecisionCode, str, list[DecisionReason]]:
    context = DecisionContext(extracted=extracted, profile=profile)

    reasons = [
        build_decision_reason(rule, context)
        for rule in DECISION_RULES
        if rule.predicate(context)
    ]

    if not reasons:
        reasons = [
            DecisionReason(
                code="no_blockers_detected",
                severity=ReasonSeverity.info,
                message="Критических блокирующих факторов не найдено.",
                rule_id="go.no_blockers_detected",
                rule_title="Не найдено блокирующих факторов",
                decision_code=DecisionCode.go,
            )
        ]

    decision_code = get_primary_decision_code(reasons)
    return decision_code, get_decision_label(decision_code), reasons


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
            checklist.append("Подготовить подтверждение лицензии или допуска")
        else:
            checklist.append("Проверить возможность участия: отсутствует требуемая лицензия или допуск")

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
        checklist.append("Проверить требования к гарантии качества товара или услуги")

    if not profile.can_prepare_fast:
        checklist.append("Оценить, успеет ли команда подготовить заявку в требуемый срок")

    checklist.append("Проверить проект контракта и риски по исполнению")

    return checklist
