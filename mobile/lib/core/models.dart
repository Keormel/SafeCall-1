// Mirrors backend/app/schemas.py. Keep enum values in sync with the backend.

enum RiskLevel {
  unknown('UNKNOWN'),
  low('LOW'),
  medium('MEDIUM'),
  high('HIGH');

  const RiskLevel(this.value);
  final String value;

  static RiskLevel parse(String? raw) => RiskLevel.values.firstWhere(
    (r) => r.value == raw,
    orElse: () => RiskLevel.unknown,
  );

  /// Levels that deserve a warning and a follow-up "was it suspicious?" question.
  bool get isWarning => this == RiskLevel.high || this == RiskLevel.medium;
}

/// Backend `Category` enum.
enum ScamCategory {
  bank('BANK'),
  police('POLICE'),
  delivery('DELIVERY'),
  relative('RELATIVE'),
  investment('INVESTMENT'),
  other('OTHER');

  const ScamCategory(this.value);
  final String value;

  static ScamCategory? parse(String? raw) =>
      ScamCategory.values.where((c) => c.value == raw).firstOrNull;
}

/// Backend `Action` enum.
enum ScamAction {
  suspiciousTransaction('SUSPICIOUS_TRANSACTION'),
  otp('OTP'),
  cardData('CARD_DATA'),
  transfer('TRANSFER'),
  installApp('INSTALL_APP'),
  urgency('URGENCY'),
  threat('THREAT');

  const ScamAction(this.value);
  final String value;
}

class CheckResult {
  const CheckResult({
    required this.phone,
    required this.riskLevel,
    required this.riskScore,
    this.campaignType,
    this.reportsCount = 0,
    this.fromLocalDb = false,
  });

  final String phone;
  final RiskLevel riskLevel;
  final int riskScore;
  final String? campaignType;
  final int reportsCount;
  final bool fromLocalDb;

  factory CheckResult.fromJson(Map<String, dynamic> j) => CheckResult(
    phone: j['phone'] as String,
    riskLevel: RiskLevel.parse(j['risk_level'] as String?),
    riskScore: j['risk_score'] as int? ?? 0,
    campaignType: j['campaign_type'] as String?,
    reportsCount: j['reports_count'] as int? ?? 0,
  );
}

class SyncItem {
  const SyncItem({
    required this.phone,
    required this.riskLevel,
    required this.riskScore,
    required this.campaignType,
    required this.updatedAt,
    required this.removed,
  });

  final String phone;
  final RiskLevel riskLevel;
  final int riskScore;
  final String? campaignType;
  final String updatedAt;
  final bool removed;

  factory SyncItem.fromJson(Map<String, dynamic> j) => SyncItem(
    phone: j['phone'] as String,
    riskLevel: RiskLevel.parse(j['risk_level'] as String?),
    riskScore: j['risk_score'] as int? ?? 0,
    campaignType: j['campaign_type'] as String?,
    updatedAt: j['updated_at'] as String? ?? '',
    removed: j['removed'] as bool? ?? false,
  );
}

class SyncPage {
  const SyncPage({
    required this.items,
    required this.serverTime,
    required this.fullSnapshot,
    required this.nextCursor,
    required this.hasMore,
  });

  final List<SyncItem> items;
  final String serverTime;
  final bool fullSnapshot;
  final String? nextCursor;
  final bool hasMore;

  factory SyncPage.fromJson(Map<String, dynamic> j) => SyncPage(
    items: (j['items'] as List)
        .map((e) => SyncItem.fromJson(e as Map<String, dynamic>))
        .toList(),
    serverTime: j['server_time'] as String,
    fullSnapshot: j['full_snapshot'] as bool? ?? false,
    nextCursor: j['next_cursor'] as String?,
    hasMore: j['has_more'] as bool? ?? false,
  );
}

/// One screened (or simulated) call, written to `call_events`.
class CallEvent {
  const CallEvent({
    required this.id,
    required this.phone,
    required this.level,
    required this.time,
    required this.reported,
  });

  final int id;
  final String phone;
  final RiskLevel level;
  final DateTime time;
  final bool reported;

  factory CallEvent.fromRow(Map<String, Object?> r) => CallEvent(
    id: r['id']! as int,
    phone: r['phone']! as String,
    level: RiskLevel.parse(r['level'] as String?),
    time: DateTime.fromMillisecondsSinceEpoch(r['ts']! as int),
    reported: (r['reported'] as int? ?? 0) != 0,
  );
}

enum ChatRole { user, assistant }

class ChatMessage {
  const ChatMessage(this.role, this.content);

  final ChatRole role;
  final String content;

  Map<String, dynamic> toJson() => {'role': role.name, 'content': content};
}
