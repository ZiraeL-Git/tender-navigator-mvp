# Tender Navigator

Интеллектуальный помощник поставщика в закупках по 44-ФЗ и 223-ФЗ.

Сейчас в проекте уже есть:
- rule-based decision engine с explainability
- FastAPI backend
- SQLAlchemy + Alembic
- фоновый pipeline анализа
- Next.js кабинет поставщика
- auth с пользователями и организациями
- roles, invitations и audit trail

## Самый простой локальный запуск

1. Установи:
   - Python `3.11+`
   - Node.js `20+`
2. Открой папку проекта:
   - `C:\Users\Oleg\Documents\GitHub\TenderNavigator`
3. Запусти:
   - [start-local.cmd](C:/Users/Oleg/Documents/GitHub/TenderNavigator/start-local.cmd)

Скрипт сам:
- создаст `.venv`, если его нет
- установит backend-зависимости
- установит frontend-зависимости
- поднимет backend на `127.0.0.1:8000`
- поднимет frontend на `127.0.0.1:3000`
- откроет страницу входа

## Что откроется после старта

- frontend: `http://127.0.0.1:3000/login`
- backend docs: `http://127.0.0.1:8000/docs`
- backend health: `http://127.0.0.1:8000/health`

## Как теперь устроен вход

При первом запуске страница `/login` показывает форму создания первой организации.

Ты заполняешь:
- название организации
- имя пользователя
- email
- пароль

После отправки система:
- создает организацию
- создает первого owner-пользователя
- выдает access token
- открывает кабинет

Если пользователь уже существует, `/login` работает как обычный вход по `email + пароль`.

## Базовый сценарий проверки

1. Открой `/login`
2. Если это первый запуск, создай организацию
3. Перейди в `/profiles` и создай профиль компании
4. Сделай профиль активным
5. Перейди в `/inputs` и импортируй закупку или загрузи файлы
6. Перейди в `/analyses` и открой карточку анализа
7. Перейди в `/team`, чтобы:
   - посмотреть участников организации
   - создать приглашение для нового пользователя
   - открыть ссылку приглашения
   - посмотреть последние записи audit trail

## Как проверить приглашения

1. Войди owner-пользователем.
2. Открой `/team`.
3. Создай приглашение для нового email.
4. Нажми `Открыть ссылку приглашения`.
5. На странице `/invite/{token}` задай имя и пароль.
6. После принятия приглашения новый пользователь попадет в кабинет своей организации.

## Полный сброс локальных данных

Если хочешь начать с нуля:
- [scripts/reset-local-data.cmd](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/reset-local-data.cmd)

После этого снова запусти:
- [start-local.cmd](C:/Users/Oleg/Documents/GitHub/TenderNavigator/start-local.cmd)

## Примеры env

Backend:
- [backend/.env.example](C:/Users/Oleg/Documents/GitHub/TenderNavigator/backend/.env.example)

Frontend:
- [frontend/.env.local.example](C:/Users/Oleg/Documents/GitHub/TenderNavigator/frontend/.env.local.example)

## Полезные скрипты

- [scripts/run-backend.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-backend.ps1)
- [scripts/run-frontend.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-frontend.ps1)
- [scripts/run-worker.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-worker.ps1)

## Если что-то не запустилось

Не закрывай окна `Tender Navigator Backend` и `Tender Navigator Frontend`.

Скопируй последние строки из окна, где появилась ошибка, и пришли их. По этим строкам проще всего быстро понять, где именно упал запуск.
