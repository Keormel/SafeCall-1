// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'SafeCall';

  @override
  String get ok => 'OK';

  @override
  String get cancel => 'Отмена';

  @override
  String get close => 'Закрыть';

  @override
  String get retry => 'Повторить';

  @override
  String get done => 'Готово';

  @override
  String get yes => 'Да';

  @override
  String get no => 'Нет';

  @override
  String get errNoConnection => 'Нет связи, попробуйте позже';

  @override
  String get errGeneric => 'Что-то пошло не так. Попробуйте ещё раз';

  @override
  String get errRateLimited => 'Слишком много запросов. Попробуйте позже';

  @override
  String get errInvalidPhone => 'Проверьте номер телефона';

  @override
  String get errDuplicateReport => 'Вы уже сообщали об этом номере сегодня';

  @override
  String get errAssistantUnavailable =>
      'Помощник сейчас недоступен. Попробуйте позже';

  @override
  String get riskHigh => 'Опасно';

  @override
  String get riskHighHint =>
      'Возможное мошенничество. Не сообщайте коды и не переводите деньги';

  @override
  String get riskMedium => 'Осторожно';

  @override
  String get riskMediumHint =>
      'Есть признаки, похожие на известную мошенническую схему';

  @override
  String get riskLow => 'Мало жалоб';

  @override
  String get riskLowHint => 'На этот номер жаловались редко';

  @override
  String get riskUnknown => 'Неизвестный номер';

  @override
  String get riskUnknownHint =>
      'У нас пока недостаточно информации об этом номере. Не сообщайте коды из SMS и банковские данные';

  @override
  String get catBank => 'Банк';

  @override
  String get catPolice => 'Полиция';

  @override
  String get catDelivery => 'Доставка';

  @override
  String get catRelative => 'Родственник';

  @override
  String get catInvestment => 'Инвестиции';

  @override
  String get catOther => 'Другое';

  @override
  String get onb1Title => 'Мы не слушаем разговоры';

  @override
  String get onb1Body =>
      'SafeCall не записывает и не анализирует звук, не читает контакты и не узнаёт ваше имя.';

  @override
  String get onb2Title => 'Проверяем только номер';

  @override
  String get onb2Body =>
      'Номер звонящего сверяется с базой прямо на вашем телефоне — даже без интернета.';

  @override
  String get onb3Title => 'Включите защиту';

  @override
  String get onb3Body =>
      'Разрешите уведомления: так мы сможем предупредить вас во время звонка. Звонки никогда не блокируются — вы сами решаете, отвечать или нет.';

  @override
  String get onbNext => 'Далее';

  @override
  String get onbSkip => 'Пропустить';

  @override
  String get onbEnable => 'Включить защиту';

  @override
  String get onbLater => 'Позже';

  @override
  String get tabHome => 'Главная';

  @override
  String get tabAssistant => 'Помощник';

  @override
  String get tabHistory => 'История';

  @override
  String get tabSettings => 'Настройки';

  @override
  String get protectionOn => 'Защита включена';

  @override
  String get protectionOff => 'Включить защиту';

  @override
  String get protectionOnHint => 'Мы предупредим о подозрительных звонках';

  @override
  String get protectionOffHint => 'Нажмите, чтобы включить';

  @override
  String get protectionOffTitle => 'Как отключить защиту';

  @override
  String get protectionOffBody =>
      'Защиту можно отключить только в настройках телефона.';

  @override
  String get protectionIosTitle => 'Включите SafeCall в настройках';

  @override
  String get protectionIosBody =>
      'Откройте: Телефон → Блокировка и идентификация вызовов → включите SafeCall.';

  @override
  String get openSettings => 'Открыть настройки';

  @override
  String dbCount(int count) {
    return 'Номеров в базе: $count';
  }

  @override
  String dbUpdated(String when) {
    return 'Обновлено: $when';
  }

  @override
  String get dbNever => 'База ещё не загружена';

  @override
  String get justNow => 'только что';

  @override
  String minutesAgo(int n) {
    return '$n мин назад';
  }

  @override
  String hoursAgo(int n) {
    return '$n ч назад';
  }

  @override
  String daysAgo(int n) {
    return '$n дн назад';
  }

  @override
  String get updateNow => 'Обновить сейчас';

  @override
  String get updating => 'Обновляем…';

  @override
  String get assistantButton => 'ИИ-помощник';

  @override
  String get assistantButtonHint => 'Спросить совет, если сомневаетесь';

  @override
  String get recentCalls => 'Последние звонки';

  @override
  String get allHistory => 'Вся история';

  @override
  String get noCalls => 'Проверенных звонков пока не было';

  @override
  String get manualCheck => 'Проверить номер вручную';

  @override
  String get phoneHint => '+373 69 123 456';

  @override
  String get checkButton => 'Проверить';

  @override
  String reportsCount(int n) {
    return 'Жалоб: $n';
  }

  @override
  String schemeLabel(String name) {
    return 'Схема: $name';
  }

  @override
  String get fromLocalDb => 'Нет связи — ответ из базы на телефоне';

  @override
  String get reportNumber => 'Сообщить о номере';

  @override
  String get assistantTitle => 'ИИ-помощник';

  @override
  String get newChat => 'Новый чат';

  @override
  String get assistantWelcome =>
      'Здравствуйте! Расскажите, что случилось, или выберите вопрос ниже.';

  @override
  String get typing => 'Печатает…';

  @override
  String get messageHint => 'Напишите вопрос';

  @override
  String get send => 'Отправить';

  @override
  String get chipBank => 'Мне звонят из банка';

  @override
  String get chipCode => 'Я сообщил(а) код из SMS';

  @override
  String get chipUnknown => 'Что значит ⚪ Неизвестный номер?';

  @override
  String get chipTransfer => 'Что делать, если я уже перевёл деньги?';

  @override
  String get assistantDisclaimer =>
      'Помощник даёт общие советы. В сомнительной ситуации позвоните в банк по номеру на карте или на 112.';

  @override
  String get reportTitle => 'Сообщить о звонке';

  @override
  String get reportQuestion => 'Это был подозрительный звонок?';

  @override
  String get reportWhat => 'Что произошло? Отметьте всё, что было';

  @override
  String get optBank => 'Представились банком';

  @override
  String get optPolice => 'Представились полицией';

  @override
  String get optOtp => 'Просили SMS-код';

  @override
  String get optCard => 'Просили данные карты';

  @override
  String get optTransfer => 'Просили перевести деньги';

  @override
  String get optApp => 'Предлагали установить приложение';

  @override
  String get optOther => 'Другое';

  @override
  String get tellMore => 'Расскажите, что произошло';

  @override
  String get tellMoreHint => 'Необязательно. Текст не сохраняется';

  @override
  String get reportSend => 'Отправить';

  @override
  String get thanksTitle => 'Спасибо, вы помогли другим';

  @override
  String get thanksBody =>
      'Ваш сигнал поможет вовремя предупредить других людей.';

  @override
  String get thanksQueued =>
      'Сейчас нет связи — мы отправим сообщение, когда появится интернет.';

  @override
  String get historyTitle => 'История звонков';

  @override
  String get historyEmpty => 'Здесь появятся звонки, которые проверил SafeCall';

  @override
  String get reportAction => 'Сообщить';

  @override
  String get reportedLabel => 'Отправлено';

  @override
  String get settingsTitle => 'Настройки';

  @override
  String get sectionAbout => 'О SafeCall';

  @override
  String get howItWorks => 'Как это работает';

  @override
  String get howItWorksBody =>
      'Когда вам звонят, SafeCall получает только номер звонящего.\n\nНомер проверяется по базе, которая хранится на вашем телефоне. Интернет для этого не нужен, поэтому ответ приходит за доли секунды.\n\nЕсли на номер жаловались другие люди, вы увидите предупреждение. Звонок при этом не блокируется — вы сами решаете, отвечать или нет.\n\nПосле звонка можно сообщить, был ли он подозрительным. Так база становится точнее для всех.';

  @override
  String get privacy => 'Приватность';

  @override
  String get privacyStored => 'Что хранится';

  @override
  String get privacyStoredBody =>
      'База номеров с оценкой риска, история проверенных звонков (номер, время, статус) — только на вашем телефоне. Для связи с сервером используется случайный код устройства.';

  @override
  String get privacyNotStored => 'Что не хранится';

  @override
  String get privacyNotStoredBody =>
      'Звук разговоров, ваши контакты, имя и номер телефона. Переписка с помощником не сохраняется и удаляется кнопкой «Новый чат». Текст жалобы используется только для распознавания схемы и не хранится.';

  @override
  String get sectionDatabase => 'База номеров';

  @override
  String get updateDb => 'Обновить базу сейчас';

  @override
  String get sectionNotifications => 'Уведомления';

  @override
  String get notifications => 'Предупреждения о звонках';

  @override
  String get language => 'Язык';

  @override
  String get langRu => 'Русский';

  @override
  String get langRo => 'Română';

  @override
  String get version => 'Версия';

  @override
  String get server => 'Адрес сервера';

  @override
  String get serverHint => 'Для iPhone — IP компьютера в той же сети Wi-Fi';

  @override
  String get save => 'Сохранить';

  @override
  String get resetDefault => 'По умолчанию';

  @override
  String get sectionDemo => 'Для демо';

  @override
  String get simulateCall => 'Симулировать звонок';

  @override
  String get simulateTitle => 'Симуляция звонка';

  @override
  String get simulateHint =>
      'Введите номер или выберите пример. Приложение проверит его так же, как при настоящем звонке: мошенник из базы — предупреждение сразу, любой номер — вопрос после звонка.';

  @override
  String get channelWarnings => 'Предупреждения о звонках';

  @override
  String get channelReports => 'Вопросы после звонка';

  @override
  String get channelSync => 'Обновление базы';

  @override
  String get callerIdHigh => '⚠️ SafeCall: возможно мошенники';

  @override
  String get callerIdMedium => '⚠️ SafeCall: будьте осторожны';

  @override
  String get notifScamTitle => 'Осторожно, возможно вам позвонил мошенник';

  @override
  String get postCallScamBody => 'Нажмите, если это был мошенник';

  @override
  String get postCallUnknownBody =>
      'Был ли это мошенник? Нажмите, чтобы сообщить';

  @override
  String get actionScam => '❗ Это мошенник';

  @override
  String get actionYesScam => '❗ Да, мошенник';

  @override
  String get quickReportSending => 'Отправляем номер…';

  @override
  String get simulateInCall => 'Идёт звонок…';

  @override
  String get simulateEnd => 'Завершить звонок';

  @override
  String get simulateEnded => 'Звонок завершён — смотрите уведомление';

  @override
  String get simulateScamPreset => 'Мошенник из базы';

  @override
  String get simulateUnknownPreset => 'Новый номер';

  @override
  String get simulateCallButton => 'Позвонить';
}
