import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ro.dart';
import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ro'),
    Locale('ru'),
  ];

  /// No description provided for @appName.
  ///
  /// In ru, this message translates to:
  /// **'SafeCall'**
  String get appName;

  /// No description provided for @ok.
  ///
  /// In ru, this message translates to:
  /// **'OK'**
  String get ok;

  /// No description provided for @cancel.
  ///
  /// In ru, this message translates to:
  /// **'Отмена'**
  String get cancel;

  /// No description provided for @close.
  ///
  /// In ru, this message translates to:
  /// **'Закрыть'**
  String get close;

  /// No description provided for @retry.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get retry;

  /// No description provided for @done.
  ///
  /// In ru, this message translates to:
  /// **'Готово'**
  String get done;

  /// No description provided for @yes.
  ///
  /// In ru, this message translates to:
  /// **'Да'**
  String get yes;

  /// No description provided for @no.
  ///
  /// In ru, this message translates to:
  /// **'Нет'**
  String get no;

  /// No description provided for @errNoConnection.
  ///
  /// In ru, this message translates to:
  /// **'Нет связи, попробуйте позже'**
  String get errNoConnection;

  /// No description provided for @errGeneric.
  ///
  /// In ru, this message translates to:
  /// **'Что-то пошло не так. Попробуйте ещё раз'**
  String get errGeneric;

  /// No description provided for @errRateLimited.
  ///
  /// In ru, this message translates to:
  /// **'Слишком много запросов. Попробуйте позже'**
  String get errRateLimited;

  /// No description provided for @errInvalidPhone.
  ///
  /// In ru, this message translates to:
  /// **'Проверьте номер телефона'**
  String get errInvalidPhone;

  /// No description provided for @errDuplicateReport.
  ///
  /// In ru, this message translates to:
  /// **'Вы уже сообщали об этом номере сегодня'**
  String get errDuplicateReport;

  /// No description provided for @errAssistantUnavailable.
  ///
  /// In ru, this message translates to:
  /// **'Помощник сейчас недоступен. Попробуйте позже'**
  String get errAssistantUnavailable;

  /// No description provided for @riskHigh.
  ///
  /// In ru, this message translates to:
  /// **'Опасно'**
  String get riskHigh;

  /// No description provided for @riskHighHint.
  ///
  /// In ru, this message translates to:
  /// **'Возможное мошенничество. Не сообщайте коды и не переводите деньги'**
  String get riskHighHint;

  /// No description provided for @riskMedium.
  ///
  /// In ru, this message translates to:
  /// **'Осторожно'**
  String get riskMedium;

  /// No description provided for @riskMediumHint.
  ///
  /// In ru, this message translates to:
  /// **'Есть признаки, похожие на известную мошенническую схему'**
  String get riskMediumHint;

  /// No description provided for @riskLow.
  ///
  /// In ru, this message translates to:
  /// **'Мало жалоб'**
  String get riskLow;

  /// No description provided for @riskLowHint.
  ///
  /// In ru, this message translates to:
  /// **'На этот номер жаловались редко'**
  String get riskLowHint;

  /// No description provided for @riskUnknown.
  ///
  /// In ru, this message translates to:
  /// **'Неизвестный номер'**
  String get riskUnknown;

  /// No description provided for @riskUnknownHint.
  ///
  /// In ru, this message translates to:
  /// **'У нас пока недостаточно информации об этом номере. Не сообщайте коды из SMS и банковские данные'**
  String get riskUnknownHint;

  /// No description provided for @catBank.
  ///
  /// In ru, this message translates to:
  /// **'Банк'**
  String get catBank;

  /// No description provided for @catPolice.
  ///
  /// In ru, this message translates to:
  /// **'Полиция'**
  String get catPolice;

  /// No description provided for @catDelivery.
  ///
  /// In ru, this message translates to:
  /// **'Доставка'**
  String get catDelivery;

  /// No description provided for @catRelative.
  ///
  /// In ru, this message translates to:
  /// **'Родственник'**
  String get catRelative;

  /// No description provided for @catInvestment.
  ///
  /// In ru, this message translates to:
  /// **'Инвестиции'**
  String get catInvestment;

  /// No description provided for @catOther.
  ///
  /// In ru, this message translates to:
  /// **'Другое'**
  String get catOther;

  /// No description provided for @onb1Title.
  ///
  /// In ru, this message translates to:
  /// **'Мы не слушаем разговоры'**
  String get onb1Title;

  /// No description provided for @onb1Body.
  ///
  /// In ru, this message translates to:
  /// **'SafeCall не записывает и не анализирует звук, не читает контакты и не узнаёт ваше имя.'**
  String get onb1Body;

  /// No description provided for @onb2Title.
  ///
  /// In ru, this message translates to:
  /// **'Проверяем только номер'**
  String get onb2Title;

  /// No description provided for @onb2Body.
  ///
  /// In ru, this message translates to:
  /// **'Номер звонящего сверяется с базой прямо на вашем телефоне — даже без интернета.'**
  String get onb2Body;

  /// No description provided for @onb3Title.
  ///
  /// In ru, this message translates to:
  /// **'Включите защиту'**
  String get onb3Title;

  /// No description provided for @onb3Body.
  ///
  /// In ru, this message translates to:
  /// **'Разрешите уведомления: так мы сможем предупредить вас во время звонка. Звонки никогда не блокируются — вы сами решаете, отвечать или нет.'**
  String get onb3Body;

  /// No description provided for @onbNext.
  ///
  /// In ru, this message translates to:
  /// **'Далее'**
  String get onbNext;

  /// No description provided for @onbSkip.
  ///
  /// In ru, this message translates to:
  /// **'Пропустить'**
  String get onbSkip;

  /// No description provided for @onbEnable.
  ///
  /// In ru, this message translates to:
  /// **'Включить защиту'**
  String get onbEnable;

  /// No description provided for @onbLater.
  ///
  /// In ru, this message translates to:
  /// **'Позже'**
  String get onbLater;

  /// No description provided for @tabHome.
  ///
  /// In ru, this message translates to:
  /// **'Главная'**
  String get tabHome;

  /// No description provided for @tabAssistant.
  ///
  /// In ru, this message translates to:
  /// **'Помощник'**
  String get tabAssistant;

  /// No description provided for @tabHistory.
  ///
  /// In ru, this message translates to:
  /// **'История'**
  String get tabHistory;

  /// No description provided for @tabSettings.
  ///
  /// In ru, this message translates to:
  /// **'Настройки'**
  String get tabSettings;

  /// No description provided for @protectionOn.
  ///
  /// In ru, this message translates to:
  /// **'Защита включена'**
  String get protectionOn;

  /// No description provided for @protectionOff.
  ///
  /// In ru, this message translates to:
  /// **'Включить защиту'**
  String get protectionOff;

  /// No description provided for @protectionOnHint.
  ///
  /// In ru, this message translates to:
  /// **'Мы предупредим о подозрительных звонках'**
  String get protectionOnHint;

  /// No description provided for @protectionOffHint.
  ///
  /// In ru, this message translates to:
  /// **'Нажмите, чтобы включить'**
  String get protectionOffHint;

  /// No description provided for @protectionOffTitle.
  ///
  /// In ru, this message translates to:
  /// **'Как отключить защиту'**
  String get protectionOffTitle;

  /// No description provided for @protectionOffBody.
  ///
  /// In ru, this message translates to:
  /// **'Защиту можно отключить только в настройках телефона.'**
  String get protectionOffBody;

  /// No description provided for @protectionIosTitle.
  ///
  /// In ru, this message translates to:
  /// **'Включите SafeCall в настройках'**
  String get protectionIosTitle;

  /// No description provided for @protectionIosBody.
  ///
  /// In ru, this message translates to:
  /// **'Откройте: Телефон → Блокировка и идентификация вызовов → включите SafeCall.'**
  String get protectionIosBody;

  /// No description provided for @openSettings.
  ///
  /// In ru, this message translates to:
  /// **'Открыть настройки'**
  String get openSettings;

  /// No description provided for @dbCount.
  ///
  /// In ru, this message translates to:
  /// **'Номеров в базе: {count}'**
  String dbCount(int count);

  /// No description provided for @dbUpdated.
  ///
  /// In ru, this message translates to:
  /// **'Обновлено: {when}'**
  String dbUpdated(String when);

  /// No description provided for @dbNever.
  ///
  /// In ru, this message translates to:
  /// **'База ещё не загружена'**
  String get dbNever;

  /// No description provided for @justNow.
  ///
  /// In ru, this message translates to:
  /// **'только что'**
  String get justNow;

  /// No description provided for @minutesAgo.
  ///
  /// In ru, this message translates to:
  /// **'{n} мин назад'**
  String minutesAgo(int n);

  /// No description provided for @hoursAgo.
  ///
  /// In ru, this message translates to:
  /// **'{n} ч назад'**
  String hoursAgo(int n);

  /// No description provided for @daysAgo.
  ///
  /// In ru, this message translates to:
  /// **'{n} дн назад'**
  String daysAgo(int n);

  /// No description provided for @updateNow.
  ///
  /// In ru, this message translates to:
  /// **'Обновить сейчас'**
  String get updateNow;

  /// No description provided for @updating.
  ///
  /// In ru, this message translates to:
  /// **'Обновляем…'**
  String get updating;

  /// No description provided for @assistantButton.
  ///
  /// In ru, this message translates to:
  /// **'ИИ-помощник'**
  String get assistantButton;

  /// No description provided for @assistantButtonHint.
  ///
  /// In ru, this message translates to:
  /// **'Спросить совет, если сомневаетесь'**
  String get assistantButtonHint;

  /// No description provided for @recentCalls.
  ///
  /// In ru, this message translates to:
  /// **'Последние звонки'**
  String get recentCalls;

  /// No description provided for @allHistory.
  ///
  /// In ru, this message translates to:
  /// **'Вся история'**
  String get allHistory;

  /// No description provided for @noCalls.
  ///
  /// In ru, this message translates to:
  /// **'Проверенных звонков пока не было'**
  String get noCalls;

  /// No description provided for @manualCheck.
  ///
  /// In ru, this message translates to:
  /// **'Проверить номер вручную'**
  String get manualCheck;

  /// No description provided for @phoneHint.
  ///
  /// In ru, this message translates to:
  /// **'+373 69 123 456'**
  String get phoneHint;

  /// No description provided for @checkButton.
  ///
  /// In ru, this message translates to:
  /// **'Проверить'**
  String get checkButton;

  /// No description provided for @reportsCount.
  ///
  /// In ru, this message translates to:
  /// **'Жалоб: {n}'**
  String reportsCount(int n);

  /// No description provided for @schemeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Схема: {name}'**
  String schemeLabel(String name);

  /// No description provided for @fromLocalDb.
  ///
  /// In ru, this message translates to:
  /// **'Нет связи — ответ из базы на телефоне'**
  String get fromLocalDb;

  /// No description provided for @reportNumber.
  ///
  /// In ru, this message translates to:
  /// **'Сообщить о номере'**
  String get reportNumber;

  /// No description provided for @assistantTitle.
  ///
  /// In ru, this message translates to:
  /// **'ИИ-помощник'**
  String get assistantTitle;

  /// No description provided for @newChat.
  ///
  /// In ru, this message translates to:
  /// **'Новый чат'**
  String get newChat;

  /// No description provided for @assistantWelcome.
  ///
  /// In ru, this message translates to:
  /// **'Здравствуйте! Расскажите, что случилось, или выберите вопрос ниже.'**
  String get assistantWelcome;

  /// No description provided for @typing.
  ///
  /// In ru, this message translates to:
  /// **'Печатает…'**
  String get typing;

  /// No description provided for @messageHint.
  ///
  /// In ru, this message translates to:
  /// **'Напишите вопрос'**
  String get messageHint;

  /// No description provided for @send.
  ///
  /// In ru, this message translates to:
  /// **'Отправить'**
  String get send;

  /// No description provided for @chipBank.
  ///
  /// In ru, this message translates to:
  /// **'Мне звонят из банка'**
  String get chipBank;

  /// No description provided for @chipCode.
  ///
  /// In ru, this message translates to:
  /// **'Я сообщил(а) код из SMS'**
  String get chipCode;

  /// No description provided for @chipUnknown.
  ///
  /// In ru, this message translates to:
  /// **'Что значит ⚪ Неизвестный номер?'**
  String get chipUnknown;

  /// No description provided for @chipTransfer.
  ///
  /// In ru, this message translates to:
  /// **'Что делать, если я уже перевёл деньги?'**
  String get chipTransfer;

  /// No description provided for @assistantDisclaimer.
  ///
  /// In ru, this message translates to:
  /// **'Помощник даёт общие советы. В сомнительной ситуации позвоните в банк по номеру на карте или на 112.'**
  String get assistantDisclaimer;

  /// No description provided for @reportTitle.
  ///
  /// In ru, this message translates to:
  /// **'Сообщить о звонке'**
  String get reportTitle;

  /// No description provided for @reportQuestion.
  ///
  /// In ru, this message translates to:
  /// **'Это был подозрительный звонок?'**
  String get reportQuestion;

  /// No description provided for @reportWhat.
  ///
  /// In ru, this message translates to:
  /// **'Что произошло? Отметьте всё, что было'**
  String get reportWhat;

  /// No description provided for @optBank.
  ///
  /// In ru, this message translates to:
  /// **'Представились банком'**
  String get optBank;

  /// No description provided for @optPolice.
  ///
  /// In ru, this message translates to:
  /// **'Представились полицией'**
  String get optPolice;

  /// No description provided for @optOtp.
  ///
  /// In ru, this message translates to:
  /// **'Просили SMS-код'**
  String get optOtp;

  /// No description provided for @optCard.
  ///
  /// In ru, this message translates to:
  /// **'Просили данные карты'**
  String get optCard;

  /// No description provided for @optTransfer.
  ///
  /// In ru, this message translates to:
  /// **'Просили перевести деньги'**
  String get optTransfer;

  /// No description provided for @optApp.
  ///
  /// In ru, this message translates to:
  /// **'Предлагали установить приложение'**
  String get optApp;

  /// No description provided for @optOther.
  ///
  /// In ru, this message translates to:
  /// **'Другое'**
  String get optOther;

  /// No description provided for @tellMore.
  ///
  /// In ru, this message translates to:
  /// **'Расскажите, что произошло'**
  String get tellMore;

  /// No description provided for @tellMoreHint.
  ///
  /// In ru, this message translates to:
  /// **'Необязательно. Текст не сохраняется'**
  String get tellMoreHint;

  /// No description provided for @reportSend.
  ///
  /// In ru, this message translates to:
  /// **'Отправить'**
  String get reportSend;

  /// No description provided for @thanksTitle.
  ///
  /// In ru, this message translates to:
  /// **'Спасибо, вы помогли другим'**
  String get thanksTitle;

  /// No description provided for @thanksBody.
  ///
  /// In ru, this message translates to:
  /// **'Ваш сигнал поможет вовремя предупредить других людей.'**
  String get thanksBody;

  /// No description provided for @thanksQueued.
  ///
  /// In ru, this message translates to:
  /// **'Сейчас нет связи — мы отправим сообщение, когда появится интернет.'**
  String get thanksQueued;

  /// No description provided for @historyTitle.
  ///
  /// In ru, this message translates to:
  /// **'История звонков'**
  String get historyTitle;

  /// No description provided for @historyEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Здесь появятся звонки, которые проверил SafeCall'**
  String get historyEmpty;

  /// No description provided for @reportAction.
  ///
  /// In ru, this message translates to:
  /// **'Сообщить'**
  String get reportAction;

  /// No description provided for @reportedLabel.
  ///
  /// In ru, this message translates to:
  /// **'Отправлено'**
  String get reportedLabel;

  /// No description provided for @settingsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Настройки'**
  String get settingsTitle;

  /// No description provided for @sectionAbout.
  ///
  /// In ru, this message translates to:
  /// **'О SafeCall'**
  String get sectionAbout;

  /// No description provided for @howItWorks.
  ///
  /// In ru, this message translates to:
  /// **'Как это работает'**
  String get howItWorks;

  /// No description provided for @howItWorksBody.
  ///
  /// In ru, this message translates to:
  /// **'Когда вам звонят, SafeCall получает только номер звонящего.\n\nНомер проверяется по базе, которая хранится на вашем телефоне. Интернет для этого не нужен, поэтому ответ приходит за доли секунды.\n\nЕсли на номер жаловались другие люди, вы увидите предупреждение. Звонок при этом не блокируется — вы сами решаете, отвечать или нет.\n\nПосле звонка можно сообщить, был ли он подозрительным. Так база становится точнее для всех.'**
  String get howItWorksBody;

  /// No description provided for @privacy.
  ///
  /// In ru, this message translates to:
  /// **'Приватность'**
  String get privacy;

  /// No description provided for @privacyStored.
  ///
  /// In ru, this message translates to:
  /// **'Что хранится'**
  String get privacyStored;

  /// No description provided for @privacyStoredBody.
  ///
  /// In ru, this message translates to:
  /// **'База номеров с оценкой риска, история проверенных звонков (номер, время, статус) — только на вашем телефоне. Для связи с сервером используется случайный код устройства.'**
  String get privacyStoredBody;

  /// No description provided for @privacyNotStored.
  ///
  /// In ru, this message translates to:
  /// **'Что не хранится'**
  String get privacyNotStored;

  /// No description provided for @privacyNotStoredBody.
  ///
  /// In ru, this message translates to:
  /// **'Звук разговоров, ваши контакты, имя и номер телефона. Переписка с помощником не сохраняется и удаляется кнопкой «Новый чат». Текст жалобы используется только для распознавания схемы и не хранится.'**
  String get privacyNotStoredBody;

  /// No description provided for @sectionDatabase.
  ///
  /// In ru, this message translates to:
  /// **'База номеров'**
  String get sectionDatabase;

  /// No description provided for @updateDb.
  ///
  /// In ru, this message translates to:
  /// **'Обновить базу сейчас'**
  String get updateDb;

  /// No description provided for @sectionNotifications.
  ///
  /// In ru, this message translates to:
  /// **'Уведомления'**
  String get sectionNotifications;

  /// No description provided for @notifications.
  ///
  /// In ru, this message translates to:
  /// **'Предупреждения о звонках'**
  String get notifications;

  /// No description provided for @language.
  ///
  /// In ru, this message translates to:
  /// **'Язык'**
  String get language;

  /// No description provided for @langRu.
  ///
  /// In ru, this message translates to:
  /// **'Русский'**
  String get langRu;

  /// No description provided for @langRo.
  ///
  /// In ru, this message translates to:
  /// **'Română'**
  String get langRo;

  /// No description provided for @version.
  ///
  /// In ru, this message translates to:
  /// **'Версия'**
  String get version;

  /// No description provided for @server.
  ///
  /// In ru, this message translates to:
  /// **'Адрес сервера'**
  String get server;

  /// No description provided for @serverHint.
  ///
  /// In ru, this message translates to:
  /// **'Для iPhone — IP компьютера в той же сети Wi-Fi'**
  String get serverHint;

  /// No description provided for @save.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить'**
  String get save;

  /// No description provided for @resetDefault.
  ///
  /// In ru, this message translates to:
  /// **'По умолчанию'**
  String get resetDefault;

  /// No description provided for @sectionDemo.
  ///
  /// In ru, this message translates to:
  /// **'Для демо'**
  String get sectionDemo;

  /// No description provided for @simulateCall.
  ///
  /// In ru, this message translates to:
  /// **'Симулировать звонок'**
  String get simulateCall;

  /// No description provided for @simulateTitle.
  ///
  /// In ru, this message translates to:
  /// **'Симуляция звонка'**
  String get simulateTitle;

  /// No description provided for @simulateHint.
  ///
  /// In ru, this message translates to:
  /// **'Введите номер или выберите пример. Приложение проверит его так же, как при настоящем звонке: мошенник из базы — предупреждение сразу, любой номер — вопрос после звонка.'**
  String get simulateHint;

  /// No description provided for @channelWarnings.
  ///
  /// In ru, this message translates to:
  /// **'Предупреждения о звонках'**
  String get channelWarnings;

  /// No description provided for @channelReports.
  ///
  /// In ru, this message translates to:
  /// **'Вопросы после звонка'**
  String get channelReports;

  /// No description provided for @channelSync.
  ///
  /// In ru, this message translates to:
  /// **'Обновление базы'**
  String get channelSync;

  /// No description provided for @callerIdHigh.
  ///
  /// In ru, this message translates to:
  /// **'⚠️ SafeCall: возможно мошенники'**
  String get callerIdHigh;

  /// No description provided for @callerIdMedium.
  ///
  /// In ru, this message translates to:
  /// **'⚠️ SafeCall: будьте осторожны'**
  String get callerIdMedium;

  /// No description provided for @notifScamTitle.
  ///
  /// In ru, this message translates to:
  /// **'Осторожно, возможно вам позвонил мошенник'**
  String get notifScamTitle;

  /// No description provided for @postCallScamBody.
  ///
  /// In ru, this message translates to:
  /// **'Нажмите, если это был мошенник'**
  String get postCallScamBody;

  /// No description provided for @postCallUnknownBody.
  ///
  /// In ru, this message translates to:
  /// **'Был ли это мошенник? Нажмите, чтобы сообщить'**
  String get postCallUnknownBody;

  /// No description provided for @actionScam.
  ///
  /// In ru, this message translates to:
  /// **'❗ Это мошенник'**
  String get actionScam;

  /// No description provided for @actionYesScam.
  ///
  /// In ru, this message translates to:
  /// **'❗ Да, мошенник'**
  String get actionYesScam;

  /// No description provided for @quickReportSending.
  ///
  /// In ru, this message translates to:
  /// **'Отправляем номер…'**
  String get quickReportSending;

  /// No description provided for @simulateInCall.
  ///
  /// In ru, this message translates to:
  /// **'Идёт звонок…'**
  String get simulateInCall;

  /// No description provided for @simulateEnd.
  ///
  /// In ru, this message translates to:
  /// **'Завершить звонок'**
  String get simulateEnd;

  /// No description provided for @simulateEnded.
  ///
  /// In ru, this message translates to:
  /// **'Звонок завершён — смотрите уведомление'**
  String get simulateEnded;

  /// No description provided for @simulateScamPreset.
  ///
  /// In ru, this message translates to:
  /// **'Мошенник из базы'**
  String get simulateScamPreset;

  /// No description provided for @simulateUnknownPreset.
  ///
  /// In ru, this message translates to:
  /// **'Новый номер'**
  String get simulateUnknownPreset;

  /// No description provided for @simulateCallButton.
  ///
  /// In ru, this message translates to:
  /// **'Позвонить'**
  String get simulateCallButton;

  /// No description provided for @overlayTitle.
  ///
  /// In ru, this message translates to:
  /// **'Предупреждение поверх звонка'**
  String get overlayTitle;

  /// No description provided for @overlayOn.
  ///
  /// In ru, this message translates to:
  /// **'Включено'**
  String get overlayOn;

  /// No description provided for @overlayOff.
  ///
  /// In ru, this message translates to:
  /// **'Выключено — нажмите, чтобы включить'**
  String get overlayOff;

  /// No description provided for @xiaomiSetup.
  ///
  /// In ru, this message translates to:
  /// **'Настроить для Xiaomi'**
  String get xiaomiSetup;

  /// No description provided for @xiaomiSetupHint.
  ///
  /// In ru, this message translates to:
  /// **'Всплывающие окна, окна в фоне и экран блокировки'**
  String get xiaomiSetupHint;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ro', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ro':
      return AppLocalizationsRo();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
