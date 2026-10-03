import 'package:flutter_test/flutter_test.dart';
import 'package:safecall/core/db/app_database.dart';
import 'package:safecall/core/models.dart';
import 'package:safecall/core/notifications.dart';
import 'package:safecall/core/repositories.dart';

class FakeDb implements AppDatabase {
  FakeDb(this.known);

  final Map<String, RiskLevel> known;
  final events = <(String, RiskLevel)>[];

  @override
  Future<SyncItem?> lookup(String phone) async {
    final level = known[phone];
    if (level == null) return null;
    return SyncItem(
      phone: phone,
      riskLevel: level,
      riskScore: 90,
      campaignType: 'BANK',
      updatedAt: '',
      removed: false,
    );
  }

  @override
  Future<int> insertCallEvent(String phone, RiskLevel level) async {
    events.add((phone, level));
    return events.length;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class RecordingNotifications implements Notifications {
  final warnings = <String>[];
  final postCall = <(String, RiskLevel)>[];

  @override
  Future<void> showScamWarning({
    required int eventId,
    required String phone,
    required String languageCode,
  }) async => warnings.add(phone);

  @override
  Future<void> showPostCall({
    required int eventId,
    required String phone,
    required RiskLevel level,
    required String languageCode,
  }) async => postCall.add((phone, level));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late FakeDb db;
  late RecordingNotifications notifications;
  late CallFlow flow;

  setUp(() {
    db = FakeDb({
      '+37367854919': RiskLevel.high,
      '+37368000001': RiskLevel.low,
    });
    notifications = RecordingNotifications();
    flow = CallFlow(db, notifications);
  });

  Future<ScreenedCall> call(String phone) => flow.handleIncomingCall(
    phone,
    languageCode: 'ru',
    notificationsEnabled: true,
  );

  Future<void> end(ScreenedCall c) =>
      flow.handleCallEnded(c, languageCode: 'ru', notificationsEnabled: true);

  test(
    'scenario 1: known scammer is warned at once and asked after the call',
    () async {
      final c = await call(
        '067854919',
      ); // national format still matches the DB key
      expect(c.phone, '+37367854919');
      expect(c.level, RiskLevel.high);
      expect(notifications.warnings, ['+37367854919']);
      expect(
        notifications.postCall,
        isEmpty,
        reason: 'nothing until the call ends',
      );

      await end(c);
      expect(notifications.postCall, [('+37367854919', RiskLevel.high)]);
      expect(db.events, [('+37367854919', RiskLevel.high)]);
    },
  );

  test('scenario 2: unknown number gets nothing during the call, a question after it', () async {
    final c = await call('+37369000777');
    expect(c.level, RiskLevel.unknown);
    expect(notifications.warnings, isEmpty);
    await end(c);
    expect(notifications.postCall, [('+37369000777', RiskLevel.unknown)]);
  });

  test('low-risk number is treated like an unknown one', () async {
    final c = await call('+37368000001');
    expect(notifications.warnings, isEmpty);
    await end(c);
    expect(notifications.postCall.single.$2, RiskLevel.low);
  });

  test(
    'notifications switched off: nothing is shown, the call is still logged',
    () async {
      final c = await flow.handleIncomingCall(
        '+37367854919',
        languageCode: 'ru',
        notificationsEnabled: false,
      );
      await flow.handleCallEnded(
        c,
        languageCode: 'ru',
        notificationsEnabled: false,
      );
      expect(notifications.warnings, isEmpty);
      expect(notifications.postCall, isEmpty);
      expect(db.events, hasLength(1));
    },
  );

  test('notification taps open the right screen', () {
    expect(
      Notifications.quickReportLocation(
        phone: '+37367854919',
        level: RiskLevel.high,
        eventId: 3,
      ),
      '/quick-report?phone=%2B37367854919&level=HIGH&event=3',
    );
    expect(
      Notifications.reportLocation(
        phone: '+37369000777',
        level: RiskLevel.unknown,
        eventId: 4,
        suspicious: true,
      ),
      '/report?phone=%2B37369000777&level=UNKNOWN&event=4&suspicious=1',
    );
  });
}
