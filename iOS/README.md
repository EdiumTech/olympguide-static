# Мобильное приложение

Откройте `olympguide.xcodeproj` в Xcode 16 или новее, выберите схему
`olympguide` и запустите на симуляторе или устройстве. Для устройства нужна
команда разработчика с подходящим provisioning profile.

Debug и Release используют **https://api.olympguide.ru/api/v1**.
Адрес хранится в `Config/App.xcconfig`, попадает в `Info.plist` и читается
сетевым клиентом. В xcconfig он записан как
`https:/$()/api.olympguide.ru/api/v1`: пустая подстановка сохраняет оба слеша,
не превращая остаток адреса в комментарий. HTTP-исключений в приложении нет.

`URLSession.shared` сохраняет и отправляет сессионную cookie сервера;
вручную копировать токены или cookie со старого сервера не нужно.
После перехода на новый сервер потребуется заново войти в аккаунт.

## Google Sign-In и Xcode Cloud

Для локального Google Sign-In задайте `GOOGLE_CLIENT_ID` и
`GOOGLE_CLIENT_REVERSED_ID` в `Config/Secrets.xcconfig`.
Идентификаторы должны соответствовать iOS OAuth-клиенту приложения.
Этот файл не копируется в ресурсы приложения; нужные значения попадают
в соответствующие ключи `Info.plist`.

В Xcode Cloud задайте переменные `GOOGLE_CLIENT_ID` и
`GOOGLE_CLIENT_REVERSED_ID` в workflow. Скрипт
`ci_scripts/ci_post_clone.sh` создаёт файл **до** чтения настроек Xcode.
Переменная `BASE_URL` в workflow больше не нужна: адрес берётся из репозитория.
Не задавайте отдельный `BASE_URL` в Build Settings или аргументах `xcodebuild`,
чтобы не переопределить общий адрес.

Схема подготовки настроек следует
[документации Apple по скриптам Xcode Cloud](https://developer.apple.com/documentation/xcode/writing-custom-build-scripts).

## Проверка

На Mac из каталога `iOS`:

```sh
sh scripts/test-network.sh
xcodebuild -project olympguide.xcodeproj -scheme olympguide \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

Первая команда компилирует настоящие Swift-файлы конфигурации и обработки
ответов с тестами на построение URL, ошибки HTTP, пустые ответы и `null`.
Она не требует аккаунта, симулятора или сторонних зависимостей.
Для проверки Release повторите сборку с `-configuration Release`.

На 8 сентября 2026 года в развёрнутой базе ещё нет вузов и льгот из набора
2026 года, а SMTP не настроен. Поэтому список вузов будет пустым,
а регистрация через код из письма пока не завершится. Обновлённые данные
находятся в `../data_loader/admissions`; смена адреса приложения сама по себе
не импортирует их на сервер.
