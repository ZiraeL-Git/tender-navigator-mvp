# Tender Navigator

Интеллектуальный помощник поставщика в закупках по 44-ФЗ и 223-ФЗ.

## Самый простой локальный запуск

Теперь для локального тестирования есть один сценарий без ручной возни:

1. Установи:
   - Python `3.11+`
   - Node.js `20+`
2. Открой папку проекта:
   - `C:\Users\Oleg\Documents\GitHub\TenderNavigator`
3. Запусти файл:
   - [start-local.cmd](C:/Users/Oleg/Documents/GitHub/TenderNavigator/start-local.cmd)

Что делает этот скрипт сам:

- создает `.venv`, если его нет
- ставит backend-зависимости, если они еще не установлены
- ставит frontend-зависимости, если они еще не установлены
- запускает backend на `127.0.0.1:8000`
- запускает frontend на `127.0.0.1:3000`
- открывает браузер на странице логина

## Что должно открыться

После запуска должны появиться:

- окно backend
- окно frontend
- страница логина: `http://127.0.0.1:3000/login`

Дополнительно:

- backend docs: `http://127.0.0.1:8000/docs`
- backend health: `http://127.0.0.1:8000/health`

## Как тестировать после запуска

1. Войти в кабинет
2. На странице `/profiles` создать профиль компании
3. Сделать профиль активным
4. На странице `/inputs` импортировать закупку или загрузить файл
5. На странице `/analyses` открыть результат

## Если не заработало

Не закрывай окна `Tender Navigator Backend` и `Tender Navigator Frontend`.

Скопируй последние строки из того окна, где появилась ошибка, и пришли их мне. По ним уже можно быстро понять, что именно сломалось.

## Дополнительные скрипты

Если понадобится ручной режим:

- [scripts/run-backend.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-backend.ps1)
- [scripts/run-frontend.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-frontend.ps1)
- [scripts/run-worker.ps1](C:/Users/Oleg/Documents/GitHub/TenderNavigator/scripts/run-worker.ps1)
