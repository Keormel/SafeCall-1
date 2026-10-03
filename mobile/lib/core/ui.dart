import 'package:flutter/cupertino.dart';

import '../l10n/app_localizations.dart';
import 'api_client.dart';
import 'models.dart';
import 'theme.dart';

extension L10nX on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}

String errorText(AppLocalizations l, Object error) {
  if (error is! ApiException) return l.errGeneric;
  return switch (error.code) {
    'NETWORK' => l.errNoConnection,
    'RATE_LIMITED' => l.errRateLimited,
    'INVALID_PHONE' || 'VALIDATION_ERROR' => l.errInvalidPhone,
    'DUPLICATE_REPORT' => l.errDuplicateReport,
    'ASSISTANT_UNAVAILABLE' => l.errAssistantUnavailable,
    _ => error.statusCode >= 500 ? l.errNoConnection : l.errGeneric,
  };
}

String riskLabel(AppLocalizations l, RiskLevel level) => switch (level) {
  RiskLevel.high => l.riskHigh,
  RiskLevel.medium => l.riskMedium,
  RiskLevel.low => l.riskLow,
  RiskLevel.unknown => l.riskUnknown,
};

String riskHint(AppLocalizations l, RiskLevel level) => switch (level) {
  RiskLevel.high => l.riskHighHint,
  RiskLevel.medium => l.riskMediumHint,
  RiskLevel.low => l.riskLowHint,
  RiskLevel.unknown => l.riskUnknownHint,
};

String categoryLabel(AppLocalizations l, String? raw) =>
    switch (ScamCategory.parse(raw)) {
      ScamCategory.bank => l.catBank,
      ScamCategory.police => l.catPolice,
      ScamCategory.delivery => l.catDelivery,
      ScamCategory.relative => l.catRelative,
      ScamCategory.investment => l.catInvestment,
      ScamCategory.other || null => l.catOther,
    };

String timeAgo(AppLocalizations l, DateTime time) {
  final d = DateTime.now().difference(time);
  if (d.inMinutes < 1) return l.justNow;
  if (d.inHours < 1) return l.minutesAgo(d.inMinutes);
  if (d.inDays < 1) return l.hoursAgo(d.inHours);
  return l.daysAgo(d.inDays);
}

/// White rounded card with a very light shadow.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.color,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? color;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: color ?? AppColors.card,
      borderRadius: BorderRadius.circular(22),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0D0F172A),
          blurRadius: 16,
          offset: Offset(0, 4),
        ),
      ],
    ),
    child: child,
  );
}

/// Full-width button, at least 56 pt tall (large touch target).
class BigButton extends StatelessWidget {
  const BigButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.filled = true,
    this.loading = false,
    this.color,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool filled;
  final bool loading;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final fg = filled ? CupertinoColors.white : (color ?? AppColors.primary);
    final child = loading
        ? CupertinoActivityIndicator(color: fg)
        : Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, color: fg, size: 22),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    color: fg,
                  ),
                ),
              ),
            ],
          );
    return SizedBox(
      width: double.infinity,
      child: CupertinoButton(
        minimumSize: const Size.fromHeight(56),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        borderRadius: BorderRadius.circular(16),
        color: filled ? (color ?? AppColors.primary) : AppColors.primarySoft,
        onPressed: loading ? null : onPressed,
        child: child,
      ),
    );
  }
}

/// Compact status chip: emoji-free icon + text, colored by risk.
class RiskChip extends StatelessWidget {
  const RiskChip(this.level, {super.key});

  final RiskLevel level;

  @override
  Widget build(BuildContext context) {
    final s = RiskStyle.of(level);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: s.background,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(s.icon, size: 16, color: s.accent),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              riskLabel(context.l10n, level),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: s.foreground,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Big result block for a checked number.
class RiskResultCard extends StatelessWidget {
  const RiskResultCard({super.key, required this.result, this.trailing});

  final CheckResult result;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final s = RiskStyle.of(result.riskLevel);
    final details = [
      if (result.reportsCount > 0) l.reportsCount(result.reportsCount),
      if (result.campaignType != null)
        l.schemeLabel(categoryLabel(l, result.campaignType)),
    ];
    return Semantics(
      liveRegion: true,
      label:
          '${riskLabel(l, result.riskLevel)}. ${riskHint(l, result.riskLevel)}',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: s.background,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(s.icon, color: s.accent, size: 34),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    riskLabel(l, result.riskLevel),
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: s.foreground,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              riskHint(l, result.riskLevel),
              style: TextStyle(fontSize: 17, color: s.foreground),
            ),
            const SizedBox(height: 12),
            Text(
              result.phone,
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: s.foreground,
              ),
            ),
            for (final d in details)
              Text(d, style: TextStyle(fontSize: 16, color: s.foreground)),
            if (result.fromLocalDb) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Icon(
                    CupertinoIcons.wifi_slash,
                    size: 18,
                    color: s.foreground,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      l.fromLocalDb,
                      style: TextStyle(fontSize: 15, color: s.foreground),
                    ),
                  ),
                ],
              ),
            ],
            if (trailing != null) ...[const SizedBox(height: 14), trailing!],
          ],
        ),
      ),
    );
  }
}

/// Icon + hint for empty lists.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.text,
    this.action,
  });

  final IconData icon;
  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
    child: Column(
      children: [
        Icon(icon, size: 44, color: AppColors.protectionOff),
        const SizedBox(height: 10),
        Text(text, textAlign: TextAlign.center, style: AppText.secondary),
        if (action != null) ...[const SizedBox(height: 8), action!],
      ],
    ),
  );
}

Future<void> showMessage(
  BuildContext context, {
  required String title,
  String? body,
}) => showCupertinoDialog<void>(
  context: context,
  builder: (ctx) => CupertinoAlertDialog(
    title: Text(title),
    content: body == null ? null : Text(body),
    actions: [
      CupertinoDialogAction(
        isDefaultAction: true,
        onPressed: () => Navigator.pop(ctx),
        child: Text(ctx.l10n.ok),
      ),
    ],
  ),
);
