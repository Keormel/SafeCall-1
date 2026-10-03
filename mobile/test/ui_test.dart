import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:safecall/app.dart';
import 'package:safecall/core/api_client.dart';
import 'package:safecall/core/db/app_database.dart';
import 'package:safecall/core/models.dart';
import 'package:safecall/core/notifications.dart';
import 'package:safecall/core/providers.dart';
import 'package:safecall/core/repositories.dart';
import 'package:safecall/core/settings_store.dart';
import 'package:safecall/core/theme.dart';
import 'package:safecall/core/ui.dart';
import 'package:safecall/features/assistant/chat_screen.dart';
import 'package:safecall/features/home/home_screen.dart';
import 'package:safecall/features/onboarding/onboarding_screen.dart';
import 'package:safecall/features/report/report_controller.dart';
import 'package:safecall/features/report/report_screen.dart';
import 'package:safecall/l10n/app_localizations.dart';

// --- fakes ---

class FakeLookupDb implements AppDatabase {
  @override
  Future<SyncItem?> lookup(String phone) async => SyncItem(
    phone: phone,
    riskLevel: RiskLevel.high,
    riskScore: 90,
    campaignType: 'BANK',
    updatedAt: '',
    removed: false,
  );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeSettings extends SettingsController {
  FakeSettings({this.onboardingDone = true});

  final bool onboardingDone;

  @override
  AppSettings build() => AppSettings(
    onboardingDone: onboardingDone,
    languageCode: 'ru',
    notificationsEnabled: true,
    apiBaseUrl: 'http://test',
  );

  @override
  Future<void> completeOnboarding() async =>
      state = state.copyWith(onboardingDone: true);
}

class FakeSync extends SyncController {
  @override
  SyncState build() => SyncState(count: 90, lastSync: DateTime.now());

  @override
  Future<void> sync() async {}

  @override
  Future<void> syncIfStale({
    Duration maxAge = const Duration(hours: 1),
  }) async {}

  @override
  Future<void> updateCallerId() async {}
}

class FakeProtection extends ProtectionController {
  @override
  Future<bool> build() async => false;

  @override
  Future<void> refresh() async {}

  @override
  Future<void> request() async {}

  @override
  Future<void> openSettings() async {}
}

class FakeNumbers implements NumbersRepository {
  FakeNumbers(this.result);

  final CheckResult result;
  final checked = <String>[];

  @override
  Future<CheckResult> check(String rawPhone) async {
    checked.add(rawPhone);
    return result;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeReports implements ReportsRepository {
  final reports = <({ScamCategory category, Set<ScamAction> actions})>[];
  final feedback = <bool>[];

  @override
  Future<bool> sendReport({
    required String phone,
    required ScamCategory category,
    required Set<ScamAction> actions,
    String? freeText,
    int? eventId,
  }) async {
    reports.add((category: category, actions: actions));
    return true;
  }

  @override
  Future<bool> sendFeedback({
    required String phone,
    required bool wasCorrect,
    int? eventId,
  }) async {
    feedback.add(wasCorrect);
    return true;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeApi implements ApiClient {
  FakeApi({this.fail = false});

  bool fail;
  final sent = <List<ChatMessage>>[];

  @override
  Future<String> chat(List<ChatMessage> messages) async {
    sent.add(messages);
    if (fail) throw const ApiException(503, 'ASSISTANT_UNAVAILABLE', '');
    return 'Положите трубку и позвоните в банк сами.';
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeNotifications implements Notifications {
  @override
  String? launchLocation;

  @override
  void Function(String location)? onOpen;

  int permissionRequests = 0;

  @override
  Future<bool> requestPermission() async {
    permissionRequests++;
    return true;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

final _events = [
  CallEvent(
    id: 1,
    phone: '+37379903529',
    level: RiskLevel.high,
    time: DateTime(2026, 10, 3, 12),
    reported: false,
  ),
  CallEvent(
    id: 2,
    phone: '+37369000777',
    level: RiskLevel.unknown,
    time: DateTime(2026, 10, 3, 11),
    reported: true,
  ),
];

List<Override> _baseOverrides({
  NumbersRepository? numbers,
  ReportsRepository? reports,
  ApiClient? api,
  Notifications? notifications,
  bool onboardingDone = true,
}) => [
  settingsProvider.overrideWith(
    () => FakeSettings(onboardingDone: onboardingDone),
  ),
  syncControllerProvider.overrideWith(FakeSync.new),
  protectionProvider.overrideWith(FakeProtection.new),
  callEventsProvider.overrideWith((ref, limit) async => _events),
  numbersRepositoryProvider.overrideWithValue(
    numbers ??
        FakeNumbers(
          const CheckResult(
            phone: '+37379903529',
            riskLevel: RiskLevel.high,
            riskScore: 80,
          ),
        ),
  ),
  reportsRepositoryProvider.overrideWithValue(reports ?? FakeReports()),
  apiClientProvider.overrideWithValue(api ?? FakeApi()),
  notificationsProvider.overrideWithValue(notifications ?? FakeNotifications()),
];

Future<void> _pump(
  WidgetTester tester,
  Widget screen, {
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides.isEmpty ? _baseOverrides() : overrides,
      child: CupertinoApp(
        theme: appTheme,
        locale: const Locale('ru'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        home: screen,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void _phoneSize(WidgetTester tester, {double textScale = 1.0}) {
  tester.view.physicalSize = const Size(1179, 2556); // iPhone 15/16 Pro
  tester.view.devicePixelRatio = 3;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

Future<void> _scrollTo(WidgetTester tester, Finder target) =>
    tester.scrollUntilVisible(
      target,
      250,
      scrollable: find
          .byWidgetPredicate(
            (w) => w is Scrollable && w.axisDirection == AxisDirection.down,
          )
          .first,
    );

// --- tests ---------------------------------------------------------------

void main() {
  testWidgets(
    'home shows protection, database status and recent calls with full numbers',
    (tester) async {
      _phoneSize(tester);
      await _pump(tester, const HomeScreen());

      expect(find.text('Включить защиту'), findsOneWidget);
      expect(find.text('Номеров в базе: 90'), findsOneWidget);
      expect(find.text('ИИ-помощник'), findsOneWidget);
      await _scrollTo(tester, find.text('Последние звонки'));
      expect(find.text('+37379903529'), findsOneWidget);
    },
  );

  testWidgets('manual check shows the result and closes the keyboard', (
    tester,
  ) async {
    _phoneSize(tester);
    final numbers = FakeNumbers(
      const CheckResult(
        phone: '+37379903529',
        riskLevel: RiskLevel.high,
        riskScore: 80,
        reportsCount: 13,
      ),
    );
    await _pump(
      tester,
      const HomeScreen(),
      overrides: _baseOverrides(numbers: numbers),
    );

    final field = find.byType(CupertinoTextField);
    await _scrollTo(tester, field);
    await tester.tap(field);
    await tester.pump();
    await tester.enterText(field, '079903529');
    expect(tester.testTextInput.isVisible, isTrue);

    await tester.tap(find.text('Проверить'));
    await tester.pumpAndSettle();

    expect(numbers.checked, ['079903529']);
    expect(tester.testTextInput.isVisible, isFalse);
    expect(
      find.descendant(
        of: find.byType(RiskResultCard),
        matching: find.text('Опасно'),
      ),
      findsOneWidget,
    );
    expect(find.text('Жалоб: 13'), findsOneWidget);
    expect(find.text('Сообщить о номере'), findsOneWidget);
  });

  testWidgets('tapping outside a text field closes the keyboard', (
    tester,
  ) async {
    _phoneSize(tester);
    await tester.pumpWidget(
      ProviderScope(overrides: _baseOverrides(), child: const SafeCallApp()),
    );
    await tester.pumpAndSettle();

    final field = find.byType(CupertinoTextField);
    await _scrollTo(tester, field);
    await tester.showKeyboard(field);
    await tester.pump();
    expect(tester.testTextInput.isVisible, isTrue);

    await tester.tapAt(
      const Offset(200, 120),
    ); // the large title area, not a control
    await tester.pump();
    expect(tester.testTextInput.isVisible, isFalse);
  });

  testWidgets('tab bar hides while the keyboard is open', (tester) async {
    _phoneSize(tester);
    await tester.pumpWidget(
      ProviderScope(overrides: _baseOverrides(), child: const SafeCallApp()),
    );
    await tester.pumpAndSettle();
    expect(find.byType(CupertinoTabBar), findsOneWidget);

    tester.view.viewInsets = const FakeViewPadding(bottom: 900);
    await tester.pumpAndSettle();
    expect(find.byType(CupertinoTabBar), findsNothing);
    expect(
      tester.takeException(),
      isNull,
      reason: 'no overflow with the keyboard open',
    );

    tester.view.resetViewInsets();
    await tester.pumpAndSettle();
    expect(find.byType(CupertinoTabBar), findsOneWidget);
  });

  testWidgets('tabs switch between screens', (tester) async {
    _phoneSize(tester);
    await tester.pumpWidget(
      ProviderScope(overrides: _baseOverrides(), child: const SafeCallApp()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('История'));
    await tester.pumpAndSettle();
    expect(find.text('История звонков'), findsWidgets);

    await tester.tap(find.text('Настройки').last);
    await tester.pumpAndSettle();
    expect(find.text('Как это работает'), findsOneWidget);

    await tester.tap(find.text('Помощник'));
    await tester.pumpAndSettle();
    expect(find.text('Мне звонят из банка'), findsOneWidget);
  });

  testWidgets('first launch goes through onboarding to home', (tester) async {
    _phoneSize(tester);
    final notifications = FakeNotifications();
    await tester.pumpWidget(
      ProviderScope(
        overrides: _baseOverrides(
          onboardingDone: false,
          notifications: notifications,
        ),
        child: const SafeCallApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(OnboardingScreen), findsOneWidget);
    expect(find.text('Мы не слушаем разговоры'), findsOneWidget);

    await tester.tap(find.text('Далее'));
    await tester.pumpAndSettle();
    expect(find.text('Проверяем только номер'), findsOneWidget);
    await tester.tap(find.text('Далее'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Включить защиту'));
    await tester.pumpAndSettle();
    expect(notifications.permissionRequests, 1);
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  group('report', () {
    Future<FakeReports> pumpReport(WidgetTester tester, RiskLevel level) async {
      _phoneSize(tester);
      final reports = FakeReports();
      final router = GoRouter(
        initialLocation: '/start',
        routes: [
          GoRoute(
            path: '/start',
            builder: (_, _) =>
                const CupertinoPageScaffold(child: Text('start')),
          ),
          GoRoute(
            path: '/report',
            builder: (_, _) => ReportScreen(
              args: ReportArgs(phone: '+37379903529', level: level, eventId: 1),
            ),
          ),
          GoRoute(
            path: '/report/thanks',
            builder: (_, state) => ReportThanksScreen(
              queued: state.uri.queryParameters['queued'] == 'true',
            ),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: _baseOverrides(reports: reports),
          child: CupertinoApp.router(
            locale: const Locale('ru'),
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            routerConfig: router,
          ),
        ),
      );
      router.push('/report');
      await tester.pumpAndSettle();
      return reports;
    }

    testWidgets('"Yes" reveals options and sends a report', (tester) async {
      final reports = await pumpReport(tester, RiskLevel.high);
      expect(find.text('+37379903529'), findsOneWidget);
      expect(find.text('Просили SMS-код'), findsNothing);

      await tester.tap(find.text('Да'));
      await tester.pumpAndSettle();
      await _scrollTo(tester, find.text('Представились банком'));
      await tester.tap(find.text('Представились банком'));
      await _scrollTo(tester, find.text('Просили SMS-код'));
      await tester.tap(find.text('Просили SMS-код'));
      await tester.pump();
      await _scrollTo(tester, find.text('Отправить'));
      await tester.tap(find.text('Отправить'));
      await tester.pumpAndSettle();

      expect(reports.reports.single.category, ScamCategory.bank);
      expect(reports.reports.single.actions, {ScamAction.otp});
      expect(find.text('Спасибо, вы помогли другим'), findsOneWidget);
    });

    testWidgets('"No" after a warning sends negative feedback and closes', (
      tester,
    ) async {
      final reports = await pumpReport(tester, RiskLevel.high);
      await tester.tap(find.text('Нет'));
      await tester.pumpAndSettle();
      expect(reports.feedback, [false]);
      expect(find.text('start'), findsOneWidget);
    });

    testWidgets('free text is collapsed by default', (tester) async {
      await pumpReport(tester, RiskLevel.unknown);
      await tester.tap(find.text('Да'));
      await tester.pumpAndSettle();
      expect(find.byType(CupertinoTextField), findsNothing);
      await _scrollTo(tester, find.text('Расскажите, что произошло'));
      await tester.tap(find.text('Расскажите, что произошло'));
      await tester.pumpAndSettle();
      expect(find.byType(CupertinoTextField), findsOneWidget);
    });
  });

  group('post-call notification taps', () {
    Future<FakeReports> pumpRoute(WidgetTester tester, Widget screen) async {
      _phoneSize(tester);
      final reports = FakeReports();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            ..._baseOverrides(reports: reports),
            databaseProvider.overrideWithValue(FakeLookupDb()),
          ],
          child: CupertinoApp(
            locale: const Locale('ru'),
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            home: screen,
          ),
        ),
      );
      await tester.pumpAndSettle();
      return reports;
    }

    testWidgets('red "!" (known scammer) reports in one tap', (tester) async {
      final reports = await pumpRoute(
        tester,
        const QuickReportScreen(
          args: ReportArgs(
            phone: '+37367854919',
            level: RiskLevel.high,
            eventId: 1,
          ),
        ),
      );
      expect(
        reports.reports.single.category,
        ScamCategory.bank,
        reason: 'scheme known from the DB',
      );
      expect(find.text('Спасибо, вы помогли другим'), findsOneWidget);
    });

    testWidgets(
      'orange "!" (unknown) opens the form with the number and options ready',
      (tester) async {
        await pumpRoute(
          tester,
          const ReportScreen(
            args: ReportArgs(
              phone: '+37369000777',
              level: RiskLevel.unknown,
              eventId: 2,
              suspicious: true,
            ),
          ),
        );
        expect(find.text('+37369000777'), findsOneWidget);
        expect(
          find.text('Представились банком'),
          findsOneWidget,
          reason: 'no extra "was it suspicious?" step',
        );
      },
    );
  });

  group('assistant', () {
    testWidgets('quick question gets an answer with the disclaimer', (
      tester,
    ) async {
      _phoneSize(tester);
      final api = FakeApi();
      await _pump(
        tester,
        const ChatScreen(),
        overrides: _baseOverrides(api: api),
      );

      await tester.tap(find.text('Мне звонят из банка'));
      await tester.pumpAndSettle();

      expect(api.sent.single.single.content, 'Мне звонят из банка');
      expect(
        find.text('Положите трубку и позвоните в банк сами.'),
        findsOneWidget,
      );
      expect(find.textContaining('Помощник даёт общие советы'), findsOneWidget);

      await tester.tap(find.text('Новый чат'));
      await tester.pumpAndSettle();
      expect(
        find.text('Положите трубку и позвоните в банк сами.'),
        findsNothing,
      );
    });

    testWidgets('unavailable assistant shows a message and retry works', (
      tester,
    ) async {
      _phoneSize(tester);
      final api = FakeApi(fail: true);
      await _pump(
        tester,
        const ChatScreen(),
        overrides: _baseOverrides(api: api),
      );

      await tester.enterText(find.byType(CupertinoTextField), 'Что делать?');
      await tester.testTextInput.receiveAction(TextInputAction.send);
      await tester.pumpAndSettle();
      expect(
        find.text('Помощник сейчас недоступен. Попробуйте позже'),
        findsOneWidget,
      );

      api.fail = false;
      await tester.tap(find.text('Повторить'));
      await tester.pumpAndSettle();
      expect(
        api.sent.last.single.content,
        'Что делать?',
        reason: 'retry resends the same question',
      );
      expect(
        find.text('Положите трубку и позвоните в банк сами.'),
        findsOneWidget,
      );
    });
  });

  testWidgets('large text (130%) does not break the home layout', (
    tester,
  ) async {
    _phoneSize(tester, textScale: 1.3);
    await _pump(tester, const HomeScreen());
    expect(tester.takeException(), isNull);
    await _scrollTo(tester, find.text('Последние звонки'));
    expect(tester.takeException(), isNull);
  });

  testWidgets('small phone (iPhone SE) layout has no overflow', (tester) async {
    tester.view.physicalSize = const Size(750, 1334);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(overrides: _baseOverrides(), child: const SafeCallApp()),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('main buttons are at least 56 pt tall', (tester) async {
    _phoneSize(tester);
    await _pump(tester, const HomeScreen());
    for (final label in ['ИИ-помощник', 'Обновить сейчас']) {
      final button = find.ancestor(
        of: find.text(label),
        matching: find.byType(CupertinoButton),
      );
      expect(
        tester.getSize(button.first).height,
        greaterThanOrEqualTo(56),
        reason: label,
      );
    }
  });
}
