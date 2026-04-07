import sqlite3
from datetime import datetime

import requests
import streamlit as st

from services.analysis import analyze_tender_package, build_company_profile
from services.document_io import build_tender_documents


if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = ""

if "last_uploaded_signature" not in st.session_state:
    st.session_state.last_uploaded_signature = ""

AI_MODE = True
DB_MODE = True


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def init_db():
    conn = sqlite3.connect("tender_history.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            filename TEXT,
            notice_number TEXT,
            object_name TEXT,
            price TEXT,
            deadline TEXT,
            decision TEXT,
            bid_security TEXT,
            contract_security TEXT,
            quality_guarantee TEXT,
            summary TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


def save_analysis(
    package_name,
    notice_number,
    object_name,
    price,
    deadline,
    decision,
    bid_security,
    contract_security,
    quality_guarantee,
    summary,
):
    conn = sqlite3.connect("tender_history.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analyses (
            created_at,
            filename,
            notice_number,
            object_name,
            price,
            deadline,
            decision,
            bid_security,
            contract_security,
            quality_guarantee,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        package_name,
        notice_number,
        object_name,
        price,
        deadline,
        decision,
        bid_security,
        contract_security,
        quality_guarantee,
        summary,
    ))

    conn.commit()
    conn.close()


def get_last_analyses(limit=5):
    conn = sqlite3.connect("tender_history.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT created_at, filename, decision, price, deadline
        FROM analyses
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows


def ask_ollama_for_summary(text: str):
    prompt = f"""
Ты анализируешь документацию по государственной закупке.

Ответь СТРОГО НА РУССКОМ ЯЗЫКЕ.
Не используй английский язык, кроме тех случаев, когда в самом документе есть официальные термины или названия.
Пиши ясно, кратко и по делу.

Сделай:
1. Краткую выжимку закупки.
2. Ключевые требования к поставщику.
3. Основные риски.
4. Что нужно проверить перед участием.
5. Короткий вывод: идти / не идти / проверить вручную.

Текст документа:
{text[:12000]}
"""

    payload = {
        "model": "gemma3:4b",
        "messages": [
            {
                "role": "system",
                "content": "Ты — помощник по анализу тендерной документации. Всегда отвечай только на русском языке. Если ответ получился не на русском, перепиши его на русский полностью.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
    }

    response = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


st.title("ТендерНавигатор MVP")
st.write("Загрузи PDF или DOCX с документацией закупки")

uploaded_files = st.file_uploader(
    "Загрузи пакет документов закупки",
    type=["pdf", "docx"],
    accept_multiple_files=True,
)

if uploaded_files:
    current_signature = "|".join(sorted([f.name for f in uploaded_files]))

    if current_signature != st.session_state.last_uploaded_signature:
        st.session_state.ai_summary = ""
        st.session_state.last_uploaded_signature = current_signature

    documents = build_tender_documents(uploaded_files)

    st.subheader("Загруженные документы")
    for doc in documents:
        st.write(f"- **{doc.filename}** ({doc.doc_type.value}) | символов: {doc.text_length}")

    st.sidebar.header("Профиль компании")

    company_name = st.sidebar.text_input("Название компании")
    company_inn = st.sidebar.text_input("ИНН")
    company_region = st.sidebar.text_input("Регион")
    company_categories_raw = st.sidebar.text_input("Категории / направления деятельности (через запятую)")

    company_has_license = st.sidebar.selectbox(
        "Есть нужная лицензия / допуск?",
        ["Нет", "Да"],
    )

    company_has_experience = st.sidebar.selectbox(
        "Есть релевантный опыт?",
        ["Нет", "Да"],
    )

    company_can_prepare_fast = st.sidebar.selectbox(
        "Сможем быстро подготовить заявку?",
        ["Нет", "Да"],
    )

    company_notes = st.sidebar.text_area("Заметки по компании")

    profile = build_company_profile(
        company_name=company_name,
        company_inn=company_inn,
        company_region=company_region,
        company_categories_raw=company_categories_raw,
        company_has_license=company_has_license,
        company_has_experience=company_has_experience,
        company_can_prepare_fast=company_can_prepare_fast,
        company_notes=company_notes,
    )

    result = analyze_tender_package(
        documents=documents,
        profile=profile,
        ai_summary=st.session_state.ai_summary,
    )

    if result.raw_text and len(result.raw_text.strip()) < 50:
        st.warning("Похоже, PDF без текстового слоя. Нужен OCR fallback.")

    st.subheader("Диагностика")
    st.write(f"Длина извлеченного текста: {len(result.raw_text or '')}")
    st.text_area("Первые 2000 символов", (result.raw_text or "")[:2000], height=200)

    st.subheader("Первичный разбор")
    st.write(f"**Номер извещения:** {result.extracted.notice_number or 'Не найдено'}")
    st.write(f"**Объект закупки:** {result.extracted.object_name or 'Не найдено'}")
    st.write(f"**Заказчик:** {result.extracted.customer_name or 'Не найдено'}")
    st.write(f"**НМЦК / цена:** {result.extracted.price or 'Не найдено'}")
    st.write(f"**Срок подачи:** {result.extracted.deadline or 'Не найдено'}")
    st.write(f"**Срок поставки / исполнения:** {result.extracted.supply_term or 'Не найдено'}")
    st.write(f"**Обеспечение заявки:** {result.extracted.bid_security or 'Не найдено'}")
    st.write(f"**Обеспечение исполнения контракта:** {result.extracted.contract_security or 'Не найдено'}")
    st.write(f"**Гарантия качества:** {result.extracted.quality_guarantee or 'Не найдено'}")
    st.write(f"**Требуется лицензия / допуск:** {'Да' if result.extracted.need_license else 'Не обнаружено'}")
    st.write(f"**Есть требование к опыту:** {'Да' if result.extracted.need_experience else 'Не обнаружено'}")

    st.subheader("Рекомендация")
    st.write(f"### {result.decision_label or 'Не определено'}")
    st.write(f"**Код решения:** {result.decision_code.value if result.decision_code else 'Не определен'}")

    st.subheader("Причины решения")
    if result.decision_reasons:
        for reason in result.decision_reasons:
            st.write(f"- [{reason.severity.value}] {reason.message}")
    else:
        st.write("Причины пока не зафиксированы")

    st.subheader("Checklist участия")
    if result.checklist:
        for item in result.checklist:
            st.write(f"- {item}")
    else:
        st.write("Checklist пока пуст")

    if result.warnings:
        st.subheader("Предупреждения")
        for warning in result.warnings:
            st.warning(warning)

    if AI_MODE:
        if st.button("Сделать AI-выжимку"):
            with st.spinner("Анализирую документ..."):
                try:
                    st.session_state.ai_summary = ask_ollama_for_summary(result.raw_text or "")
                    result.ai_summary = st.session_state.ai_summary
                except Exception as e:
                    st.error(f"Ошибка AI-анализа: {e}")
    else:
        st.info("AI-анализ в облачной версии временно отключен.")

    if st.session_state.ai_summary:
        result.ai_summary = st.session_state.ai_summary
        st.subheader("AI-выжимка")
        st.write(st.session_state.ai_summary)

    if DB_MODE:
        if st.button("Сохранить анализ"):
            try:
                save_analysis(
                    package_name=result.package_name,
                    notice_number=result.extracted.notice_number or "",
                    object_name=result.extracted.object_name or "",
                    price=result.extracted.price or "",
                    deadline=result.extracted.deadline or "",
                    decision=result.decision_label or "",
                    bid_security=result.extracted.bid_security or "",
                    contract_security=result.extracted.contract_security or "",
                    quality_guarantee=result.extracted.quality_guarantee or "",
                    summary=result.ai_summary or "",
                )
                st.success("Анализ сохранен в базу")
            except Exception as e:
                st.error(f"Ошибка сохранения: {e}")

        st.subheader("Последние сохраненные анализы")
        rows = get_last_analyses()

        if rows:
            for row in rows:
                st.write(f"- {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
        else:
            st.write("Пока нет сохраненных анализов")
    else:
        st.info("Сохранение AI-анализа в облачной версии временно отключено.")

    with st.expander("Отладка: объект результата"):
        st.json(model_to_dict(result))

    with st.expander("Отладка: профиль компании"):
        st.json(model_to_dict(profile))