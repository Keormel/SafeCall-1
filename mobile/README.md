# SafeCall mobile (Flutter, iOS-first)

Anti-scam app for the SafeCall backend. iOS look (Cupertino, system font), large touch targets,
Russian and Romanian UI.

Tabs: **Главная** (protection button, number DB status, manual check, recent calls, AI assistant
shortcut), **Помощник** (AI chat), **История** (checked calls, masked numbers, "Сообщить"),
**Настройки** (how it works, privacy, DB update, notifications, language, server address, debug
"Симулировать звонок"). Onboarding runs once; the report screen opens from the after-call
notification or from history.

## Run

Start the backend first (`docker compose up -d --build` in the repo root, then
`docker compose exec api python -m scripts.seed --reset` for demo data).

```bash
cd mobile
flutter pub get
flutter run -d "iPhone 17 Pro"                                   # simulator, uses localhost:8000
flutter run -d "<your iPhone>" --dart-define=API_BASE_URL=http://<mac-wifi-ip>:8000
```

The server address can also be changed in **Настройки → Адрес сервера**.

The AI assistant needs `GEMINI_API_KEY` in the backend `.env`; without it the chat shows
"Помощник сейчас недоступен".

## Call scenarios

1. **Known scammer** (🔴/🟠 in the on-device DB): as soon as the number is checked —
   "Осторожно, возможно вам позвонил мошенник" + the number. After the call — a max-priority
   notification: the number, "Нажмите, если это был мошенник" and a red "!" on the right. Tapping it
   reports the number to the backend in one step (`POST /report`, scheme taken from the DB).
2. **Any other number**: nothing during the call. After it — "Был ли это мошенник?" with an orange
   "!". Tapping it opens the report form with the number filled in and the options already shown.

Press and hold the notification for the buttons ("❗ Это мошенник" / "Нет").

**Android** (real calls): SafeCall holds the *caller ID & spam* role (`CallScreeningService`).
The service gets the number before the phone rings, checks the on-device SQLite DB (no network),
always lets the call through, shows the warning, and the `PHONE_STATE` receiver posts the
post-call notification (custom layout with the round "!" on the right). Works without the Flutter
engine running. Code: `android/app/src/main/kotlin/com/safecall/safecall/`.

Emulator demo with a real incoming call:

```bash
flutter run -d emulator-5554                 # backend at 10.0.2.2:8000
adb emu gsm call +37367854919                # known scammer → warning during the call
adb emu gsm cancel +37367854919              # call ends → red "!" notification
adb emu gsm call +37369111222; adb emu gsm cancel +37369111222   # unknown → orange "!"
```

On Android 15+ "Notification cooldown" may mute repeated alerts during testing:
`adb shell settings put system notification_cooldown_enabled 0`.

On **iPhone** an app cannot see calls or the caller's number (iOS only lets the Call Directory
extension label the incoming-call screen), so both scenarios run from **Настройки → Симулировать
звонок** (debug builds).

## Tests

```bash
flutter test   # unit + UI tests (screens, navigation, keyboard, report/chat flows, large text, small phone)
```

For smooth scrolling on a phone run `flutter run --release` (debug builds are much slower).

## Layout

- `lib/core/` — API client (dio), auth (secure storage), SQLite DB (`numbers`, `call_events`,
  `outbox`), repositories, notifications, native bridge, Riverpod providers, theme and shared UI
- `lib/features/` — onboarding, home, assistant, report, history, settings, debug
- `lib/l10n/` — `app_ru.arb`, `app_ro.arb` (`flutter gen-l10n`)
- `ios/Runner/AppDelegate.swift` — `safecall/native` channel: Call Directory status, Settings,
  writing the caller-ID list to the App Group `group.com.akula.safecall`
- `ios/CallDirectory/` — CallKit Call Directory extension: labels 🔴/🟠 numbers on incoming calls
  (never blocks). Enable it in iOS Settings → Apps → Phone → Call Blocking & Identification → SafeCall.

## Not done yet

- Periodic background sync (workmanager); the DB updates on app start/resume and by button.
