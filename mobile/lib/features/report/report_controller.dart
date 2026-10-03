import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';

/// Checkboxes on the report screen. Two of them pick the category, the rest map to actions.
enum ReportOption { bank, police, otp, card, transfer, installApp, other }

class ReportArgs {
  const ReportArgs({
    required this.phone,
    required this.level,
    this.eventId,
    this.suspicious = false,
  });

  final String phone;
  final RiskLevel level;
  final int? eventId;

  /// The user already said "it was a scammer" (from the post-call notification): skip the question.
  final bool suspicious;
}

class ReportRequest {
  const ReportRequest(this.category, this.actions);

  final ScamCategory category;
  final Set<ScamAction> actions;

  factory ReportRequest.from(Set<ReportOption> options) {
    final category = options.contains(ReportOption.bank)
        ? ScamCategory.bank
        : options.contains(ReportOption.police)
        ? ScamCategory.police
        : ScamCategory.other;
    final actions = {
      if (options.contains(ReportOption.otp)) ScamAction.otp,
      if (options.contains(ReportOption.card)) ScamAction.cardData,
      if (options.contains(ReportOption.transfer)) ScamAction.transfer,
      if (options.contains(ReportOption.installApp)) ScamAction.installApp,
    };
    return ReportRequest(category, actions);
  }
}

class ReportController {
  ReportController(this._ref);

  final Ref _ref;

  /// "Yes, suspicious": send the report. Returns true if delivered, false if queued offline.
  Future<bool> submit(
    ReportArgs args,
    Set<ReportOption> options,
    String freeText,
  ) async {
    final req = ReportRequest.from(options);
    final sent = await _ref
        .read(reportsRepositoryProvider)
        .sendReport(
          phone: args.phone,
          category: req.category,
          actions: req.actions,
          freeText: freeText,
          eventId: args.eventId,
        );
    _ref.invalidate(callEventsProvider);
    return sent;
  }

  /// One-tap report from the post-call notification for a known scammer.
  /// The scheme the server already knows for this number is reused as the category.
  /// Returns true if delivered, false if queued offline.
  Future<bool> quickReport(ReportArgs args) async {
    final known = await _ref.read(databaseProvider).lookup(args.phone);
    final sent = await _ref
        .read(reportsRepositoryProvider)
        .sendReport(
          phone: args.phone,
          category:
              ScamCategory.parse(known?.campaignType) ?? ScamCategory.other,
          actions: const {},
          eventId: args.eventId,
        );
    _ref.invalidate(callEventsProvider);
    return sent;
  }

  /// "No, it was fine": the warning was right only if we did not warn.
  Future<void> notSuspicious(ReportArgs args) async {
    await _ref
        .read(reportsRepositoryProvider)
        .sendFeedback(
          phone: args.phone,
          wasCorrect: !args.level.isWarning,
          eventId: args.eventId,
        );
    _ref.invalidate(callEventsProvider);
  }
}

final reportControllerProvider = Provider(ReportController.new);
