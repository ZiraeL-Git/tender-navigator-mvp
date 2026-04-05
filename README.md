# Tender Navigator MVP

Прототип анализатора тендерной документации.

## Что умеет
- загрузка PDF и DOCX
- извлечение текста
- rule-based анализ
- поиск ключевых полей
- рекомендация по участию
- checklist участия
- сохранение анализа в SQLite

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py

#Альтернативный запуск для git bash

source /c/Users/Oleg/Documents/GitHub/TenderNavigator/tender_navigator_mvp/.venv/Scripts/activate


---

## Шаг 4. Сделай “облачную” правку в `app.py`

Поскольку локальный Ollama в облаке не поднимется, тебе нужно на время публикации сделать один из двух вариантов.

### Вариант А — временно отключить AI-кнопку
Самый безопасный вариант.

Например:

```python
DEPLOY_MODE = True
