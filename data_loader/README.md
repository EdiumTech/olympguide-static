# Данные вузов и олимпиад

Актуальный набор для приёма **2026 года** находится в [`admissions`](admissions/README.md).
Он включает НИУ ВШЭ, ИТМО, МГТУ им. Баумана, МФТИ, НИЯУ МИФИ, МАИ и МГЮА:
7 891 запись, 94 официальных источника, в том числе 82 PDF. Дата сбора — 6 сентября 2026 года.

Из этой папки, Python 3.10+:

```console
python -m admissions download
python -m admissions validate
python -m admissions load --database admissions_2026.sqlite3
python -m admissions search --university msal --text Кутафинская
python -m admissions export-sql --output admissions_2026.sql
```

Первый запуск `download` получает архив из GitHub Release и проверяет SHA-256
архива и каждого файла по `admissions/releases/2026.json`.
Остальные команды работают офлайн и используют только стандартную библиотеку Python.
Загрузчик сохраняет полные условия в новых таблицах `admission_*`.
Совместимость со старым API, область покрытия, обновление источников и проверки описаны
в [документации каталога](admissions/README.md).

`hse_loader`, `itmo_loader` и `rsr_loader` — исторические загрузчики непосредственно в API.
Их запуск требует настроенного API и может изменять сервер. Новый каталог не использует
зашитые ID вузов, не обращается к API и не требует токена.
