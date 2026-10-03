import 'api_client.dart';
import 'db/app_database.dart';
import 'models.dart';
import 'notifications.dart';
import 'phone_utils.dart';

class NumbersRepository {
  NumbersRepository(this._api, this._db);

  final ApiClient _api;
  final AppDatabase _db;

  /// Fresh answer from the server; the on-device DB when the server is unreachable.
  Future<CheckResult> check(String rawPhone) async {
    try {
      return await _api.checkNumber(rawPhone);
    } on ApiException catch (e) {
      if (!e.isNetwork) rethrow;
      final phone = normalizePhone(rawPhone);
      final local = await _db.lookup(phone);
      return CheckResult(
        phone: phone,
        riskLevel: local?.riskLevel ?? RiskLevel.unknown,
        riskScore: local?.riskScore ?? 0,
        campaignType: local?.campaignType,
        fromLocalDb: true,
      );
    }
  }

  /// Pulls the delta (full snapshot on first run) across all cursor pages.
  Future<void> sync() async {
    final since = await _db.getMeta('sync_since');
    final pages = <SyncPage>[];
    String? cursor;
    do {
      final page = await _api.sync(since: since, cursor: cursor);
      pages.add(page);
      cursor = page.nextCursor;
    } while (pages.last.hasMore && cursor != null);
    // Per the API contract, the next `since` is server_time from the FIRST page.
    await _db.applySync(pages, pages.first.serverTime);
  }

  /// Caller-ID lines for the iOS Call Directory: `digits<TAB>label`, ascending by number.
  Future<String> callerIdLines({
    required String highLabel,
    required String mediumLabel,
  }) async {
    final buffer = StringBuffer();
    for (final n in await _db.warningNumbers()) {
      final digits = n.phone.replaceAll(RegExp(r'\D'), '');
      if (digits.isEmpty) continue;
      buffer
        ..write(digits)
        ..write('\t')
        ..writeln(n.level == RiskLevel.high ? highLabel : mediumLabel);
    }
    return buffer.toString();
  }

  Future<int> count() => _db.countNumbers();

  Future<DateTime?> lastSync() async =>
      DateTime.tryParse(await _db.getMeta('last_sync') ?? '');

  /// Called when the server changes: its numbers no longer apply.
  Future<void> reset() => _db.clearNumbers();
}

/// Reports and feedback go out immediately, or wait in the outbox until the network returns.
class ReportsRepository {
  ReportsRepository(this._api, this._db);

  final ApiClient _api;
  final AppDatabase _db;

  static const _kReport = 'report';
  static const _kFeedback = 'feedback';

  /// Returns true if delivered now, false if queued for later.
  Future<bool> sendReport({
    required String phone,
    required ScamCategory category,
    required Set<ScamAction> actions,
    String? freeText,
    int? eventId,
  }) async {
    final payload = {
      'phone': phone,
      'category': category.value,
      'actions': actions.map((a) => a.value).toList(),
      if (freeText != null && freeText.trim().isNotEmpty)
        'free_text': freeText.trim(),
    };
    final sent = await _deliver(_kReport, payload);
    if (eventId != null) await _db.markReported(eventId);
    return sent;
  }

  Future<bool> sendFeedback({
    required String phone,
    required bool wasCorrect,
    int? eventId,
  }) async {
    final sent = await _deliver(_kFeedback, {
      'phone': phone,
      'was_correct': wasCorrect,
    });
    if (eventId != null) await _db.markReported(eventId);
    return sent;
  }

  Future<bool> _deliver(String kind, Map<String, dynamic> payload) async {
    try {
      await _post(kind, payload);
      return true;
    } on ApiException catch (e) {
      if (e.isNetwork || e.statusCode >= 500) {
        await _db.enqueue(kind, payload);
        return false;
      }
      // Feedback for a number the server has no data on is simply not needed.
      if (kind == _kFeedback && e.statusCode == 404) return true;
      rethrow;
    }
  }

  Future<void> _post(String kind, Map<String, dynamic> payload) =>
      kind == _kReport ? _api.report(payload) : _api.feedback(payload);

  /// Sends queued items in order; stops at the first network failure.
  Future<void> flushOutbox() async {
    for (final item in await _db.outbox()) {
      try {
        await _post(item.kind, item.payload);
        await _db.dequeue(item.id);
      } on ApiException catch (e) {
        if (e.isPermanent) {
          await _db.dequeue(
            item.id,
          ); // e.g. duplicate report: retrying will never succeed
        } else {
          return;
        }
      }
    }
  }
}

/// One screened call: the number as stored, its level and the `call_events` row.
typedef ScreenedCall = ({int eventId, String phone, RiskLevel level});

/// The call flow: on-device lookup only (no network), log the event, warn, then ask after the call.
///
/// The native call-screening service runs the same steps; the debug "simulate call" screen
/// calls this directly so the scenario can be shown without a real call.
class CallFlow {
  CallFlow(this._db, this._notifications);

  final AppDatabase _db;
  final Notifications _notifications;

  /// Start of the call. Known scammers get a warning right away; other numbers get nothing yet.
  Future<ScreenedCall> handleIncomingCall(
    String rawPhone, {
    required String languageCode,
    required bool notificationsEnabled,
  }) async {
    final phone = normalizePhone(rawPhone);
    final level = (await _db.lookup(phone))?.riskLevel ?? RiskLevel.unknown;
    final eventId = await _db.insertCallEvent(phone, level);
    if (notificationsEnabled && level.isWarning) {
      await _notifications.showScamWarning(
        eventId: eventId,
        phone: phone,
        languageCode: languageCode,
      );
    }
    return (eventId: eventId, phone: phone, level: level);
  }

  /// End of the call: ask whether it was a scammer (one-tap report for known scammers).
  Future<void> handleCallEnded(
    ScreenedCall call, {
    required String languageCode,
    required bool notificationsEnabled,
  }) async {
    if (!notificationsEnabled) return;
    await _notifications.showPostCall(
      eventId: call.eventId,
      phone: call.phone,
      level: call.level,
      languageCode: languageCode,
    );
  }
}
