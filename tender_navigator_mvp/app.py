import streamlit as st
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import re
import requests
import sqlite3
from datetime import datetime

DEPLOY_MODE = True


#Функция создания базы данных
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

#Запуск базы данных
init_db()

#Функция сохрания в базу данных
def save_analysis(
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
    ))

    conn.commit()
    conn.close()

#Функция просмотра последних записей
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

st.title("ТендерНавигатор MVP")
st.write("Загрузи PDF или DOCX с документацией закупки")

uploaded_file = st.file_uploader("Выбери файл", type=["pdf", "docx"])

#Нормализация данных
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

#Поиск извещения
def find_notice_number(text: str):
    flat = normalize_text(text)
    patterns = [
        r"Номер\s+извещения\s*[:\-]?\s*(\d{19})",
        r"для\s+закупки\s+№\s*(\d{19})",
    ]
    for pattern in patterns:
        m = re.search(pattern, flat, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

#Поиск наименования объекта закупки
def find_object_name(text: str):
    flat = normalize_text(text)
    patterns = [
        r"Наименование\s+объекта\s+закупки\s*[:\-]?\s*(.+?)(?=\s+Способ\s+определения\s+поставщика|\s+Размещение\s+осуществляет|\s+Контактная\s+информация)",
    ]
    for pattern in patterns:
        m = re.search(pattern, flat, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None

#Поиск цены/НМЦК
def find_price(text: str):
    flat = normalize_text(text)
    patterns = [
        r"Начальная\s*\(\s*максимальная\s*\)\s*цена\s+контракта\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
        r"НМЦК\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
        r"цена\s+контракта\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, flat, re.IGNORECASE)
        if m:
            return m.group(1).replace(" ", "").replace(",", ".")
    return None

#Поиск обеспечения заявки
def find_bid_security(text: str):
    flat = normalize_text(text)
    if re.search(r"Обеспечение\s+заявок\s+не\s+требуется", flat, re.IGNORECASE):
        return "Не требуется"
    if re.search(r"Требуется\s+обеспечение\s+заявки", flat, re.IGNORECASE):
        return "Требуется"
    return None

#Поиск обеспечения исполнения контракта
def find_contract_security(text: str):
    flat = normalize_text(text)

    if re.search(r"Требуется\s+обеспечение\s+исполнения\s+контракта", flat, re.IGNORECASE):
        percent = re.search(
            r"Размер\s+обеспечения\s+исполнения\s+контракта\s*[:\-]?\s*([\d.,]+)\s*%",
            flat,
            re.IGNORECASE
        )
        if percent:
            return f"{percent.group(1)}%"
        return "Требуется"
    return "Не требуется"

#Поиск сроков подачи заявок
def find_deadline(text: str):
    flat = normalize_text(text)
    patterns = [
        r"Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок\s*[:\-]?\s*([0-3]?\d\.[01]?\d\.\d{4}\s+[0-2]?\d:\d{2})",
        r"Дата\s+и\s+время\s+окончания\s+подачи\s+заявок\s*[:\-]?\s*([0-3]?\d\.[01]?\d\.\d{4}\s+[0-2]?\d:\d{2})",
        r"Дата\s+окончания\s+подачи\s+заявок\s*[:\-]?\s*([0-3]?\d\.[01]?\d\.\d{4}(?:\s+[0-2]?\d:\d{2})?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, flat, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None

#Требуется ли лицензия / допуск
def detect_license_requirement(text: str):
    flat = normalize_text(text).lower()
    keywords = [
        "лиценз",
        "допуск",
        "сро",
        "разрешени",
        "аккредитац",
    ]
    return any(k in flat for k in keywords)

#Поиск требований к опыту
def detect_experience_requirement(text: str):
    flat = normalize_text(text).lower()
    keywords = [
        "опыт исполнения",
        "аналогичн",
        "исполненных контрактов",
        "опыт поставки",
        "опыт оказания услуг",
    ]
    return any(k in flat for k in keywords)

#Поиск гарантии качества
def find_quality_guarantee(text: str):
    flat = normalize_text(text)
    m = re.search(
        r"Требуется\s+гарантия\s+качества\s+товара,\s*работы,\s*услуги\s*[:\-]?\s*(Да|Нет)",
        flat,
        re.IGNORECASE
    )
    if m:
        return m.group(1)
    return None

#Извлечение текста из pdf
def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)

    joined = "\n".join(parts).strip()

    if len(joined) < 50:
        # тут нужен OCR fallback
        return ""

    return joined

#Извлечение текста из Word
def extract_text_from_docx(file) -> str:
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

#Составление чек-листа
def build_checklist(need_license, need_experience, bid_security, contract_security, quality_guarantee):
    checklist = [
        "Проверить соответствие предмета закупки профилю компании",
        "Проверить срок окончания подачи заявки",
        "Проверить НМЦК и экономическую целесообразность участия",
        "Проверить полный состав обязательных документов"
    ]

    if need_license:
        checklist.append("Подтвердить наличие лицензии / допуска")

    if need_experience:
        checklist.append("Подготовить документы, подтверждающие релевантный опыт")

    if bid_security and "требуется" in bid_security.lower():
        checklist.append("Проверить необходимость и порядок предоставления обеспечения заявки")

    if contract_security and contract_security != "Не требуется":
        checklist.append(f"Проверить обеспечение исполнения контракта: {contract_security}")

    if quality_guarantee and quality_guarantee.lower() == "да":
        checklist.append("Проверить требования к гарантии качества товара / услуги")

    checklist.append("Проверить проект контракта и возможные риски по условиям исполнения")

    return checklist

#Логика принятия решения
def make_decision(need_license, need_experience, company_has_license, company_has_experience, company_can_prepare_fast):
    reasons = []

    if need_license and company_has_license == "Нет":
        reasons.append("Обнаружено требование лицензии/допуска, которого у компании нет.")
        return "НЕ ИДЕМ", reasons

    if need_experience and company_has_experience == "Нет":
        reasons.append("Обнаружено требование подтвержденного опыта, которого у компании нет.")
        return "НЕ ИДЕМ", reasons

    if company_can_prepare_fast == "Нет":
        reasons.append("Компания не готова быстро собрать и подать заявку.")
        return "РИСК / ПРОВЕРИТЬ", reasons

    reasons.append("Критических стоп-факторов не найдено.")
    return "ИДЕМ / ПРОВЕРИТЬ ВРУЧНУЮ", reasons

#Вызов локальной модели
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
        "model": "gemma3:4b",   # или твоя модель
        "messages": [
            {
                "role": "system",
                "content": "Ты — помощник по анализу тендерной документации. Всегда отвечай только на русском языке. Если ответ получился не на русском, перепиши его на русский полностью."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False
    }

    response = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=120
    )

    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]

#Логика
if uploaded_file is not None:

    st.sidebar.header("Профиль компании")

    company_name = st.sidebar.text_input("Название компании")
    company_has_license = st.sidebar.selectbox("Есть нужная лицензия / допуск?", ["Не знаю", "Да", "Нет"])
    company_has_experience = st.sidebar.selectbox("Есть релевантный опыт?", ["Не знаю", "Да", "Нет"])
    company_can_prepare_fast = st.sidebar.selectbox("Сможем быстро подготовить заявку?", ["Не знаю", "Да", "Нет"])

    if uploaded_file.name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_docx(uploaded_file)

    if len(text.strip()) < 50:
        st.warning("Похоже, PDF без текстового слоя. Нужен OCR fallback.")

    st.subheader("Диагностика")
    st.write(f"Длина извлеченного текста: {len(text)}")
    st.text_area("Первые 2000 символов", text[:2000], height=200)

    notice_number = find_notice_number(text)
    object_name = find_object_name(text)
    price = find_price(text)
    deadline = find_deadline(text)
    need_license = detect_license_requirement(text)
    need_experience = detect_experience_requirement(text)
    bid_security = find_bid_security(text)
    contract_security = find_contract_security(text)
    quality_guarantee = find_quality_guarantee(text)
    decision, reasons = make_decision(
    need_license,
    need_experience,
    company_has_license,
    company_has_experience,
    company_can_prepare_fast
    )


    st.subheader("Первичный разбор")
    st.write(f"**Номер извещения:** {notice_number or 'Не найдено'}")
    st.write(f"**Объект закупки:** {object_name or 'Не найдено'}")
    st.write(f"**НМЦК / цена:** {price or 'Не найдено'}")
    st.write(f"**Срок подачи:** {deadline or 'Не найдено'}")
    st.write(f"**Требуется лицензия / допуск:** {'Да' if need_license else 'Не обнаружено'}")
    st.write(f"**Есть требование к опыту:** {'Да' if need_experience else 'Не обнаружено'}")
    st.write(f"**Обеспечение заявки:** {bid_security or 'Не найдено'}")
    st.write(f"**Обеспечение исполнения контракта:** {contract_security or 'Не найдено'}")
    st.write(f"**Гарантия качества:** {quality_guarantee or 'Не найдено'}")

    st.subheader("Рекомендация")
    st.write(f"### {decision}")

    st.subheader("Причины")
    for reason in reasons:
        st.write(f"- {reason}")

    st.subheader("Checklist участия")
    checklist = build_checklist(
        need_license,
        need_experience,
        bid_security,
        contract_security,
        quality_guarantee
    )

    for item in checklist:
        st.write(f"- {item}")

    

    if "ai_summary" not in st.session_state:
        st.session_state.ai_summary = ""

    try:
        import requests
        OLLAMA_AVAILABLE = True
    except Exception:
        OLLAMA_AVAILABLE = False

    if OLLAMA_AVAILABLE and not DEPLOY_MODE:
        if st.button("Сделать AI-выжимку"):
            with st.spinner("Анализирую документ..."):
                try:
                    st.session_state.ai_summary = ask_ollama_for_summary(text)
                except Exception as e:
                    st.error(f"Ошибка AI-анализа: {e}")
        DATA_BASE_MODE = True
    else:
        st.info("AI-анализ в облачной версии временно отключен.")
        DATA_BASE_MODE = False


    if st.session_state.ai_summary:
        st.subheader("AI-выжимка")
        st.write(st.session_state.ai_summary)

    if DATA_BASE_MODE == True:
        if st.button("Сохранить анализ"):
            try:
                save_analysis(
                    filename=uploaded_file.name,
                    notice_number=notice_number or "",
                    object_name=object_name or "",
                    price=price or "",
                    deadline=deadline or "",
                    decision=decision or "",
                    bid_security=bid_security or "",
                    contract_security=contract_security or "",
                    quality_guarantee=quality_guarantee or "",
                    summary=st.session_state.ai_summary or ""
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