import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/phone_utils.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import 'report_controller.dart';

class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key, required this.args});

  final ReportArgs args;

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final _text = TextEditingController();
  final _options = <ReportOption>{};
  late bool _suspicious = widget.args.suspicious;
  bool _showText = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = errorText(context.l10n, e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() => _run(() async {
    final sent = await ref
        .read(reportControllerProvider)
        .submit(widget.args, _options, _text.text);
    HapticFeedback.mediumImpact();
    if (mounted) context.pushReplacement('/report/thanks?queued=${!sent}');
  });

  Future<void> _no() => _run(() async {
    await ref.read(reportControllerProvider).notSuspicious(widget.args);
    if (mounted) _close(context);
  });

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final labels = {
      ReportOption.bank: l.optBank,
      ReportOption.police: l.optPolice,
      ReportOption.otp: l.optOtp,
      ReportOption.card: l.optCard,
      ReportOption.transfer: l.optTransfer,
      ReportOption.installApp: l.optApp,
      ReportOption.other: l.optOther,
    };

    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(
        middle: Text(l.reportTitle),
        leading: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: () => _close(context),
          child: Text(l.close),
        ),
        border: null,
      ),
      child: SafeArea(
        child: ListView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: [
            AppCard(
              child: Column(
                children: [
                  RiskChip(widget.args.level),
                  const SizedBox(height: 10),
                  Text(maskPhone(widget.args.phone), style: AppText.headline),
                  const SizedBox(height: 18),
                  Text(
                    l.reportQuestion,
                    textAlign: TextAlign.center,
                    style: AppText.title,
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: BigButton(
                          label: l.yes,
                          color: const Color(0xFFDC2626),
                          filled: _suspicious,
                          onPressed: _busy
                              ? null
                              : () => setState(() => _suspicious = true),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: BigButton(
                          label: l.no,
                          filled: false,
                          loading: _busy && !_suspicious,
                          onPressed: _busy ? null : _no,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            AnimatedSize(
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeOut,
              child: !_suspicious
                  ? const SizedBox(width: double.infinity)
                  : Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: AppCard(
                        padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(l.reportWhat, style: AppText.headline),
                            const SizedBox(height: 6),
                            for (final entry in labels.entries)
                              _CheckRow(
                                label: entry.value,
                                value: _options.contains(entry.key),
                                onChanged: (on) => setState(
                                  () => on
                                      ? _options.add(entry.key)
                                      : _options.remove(entry.key),
                                ),
                              ),
                            const SizedBox(height: 8),
                            if (!_showText)
                              CupertinoButton(
                                padding: EdgeInsets.zero,
                                onPressed: () =>
                                    setState(() => _showText = true),
                                child: Row(
                                  children: [
                                    const Icon(
                                      CupertinoIcons.plus_circle,
                                      size: 22,
                                    ),
                                    const SizedBox(width: 8),
                                    Flexible(child: Text(l.tellMore)),
                                  ],
                                ),
                              )
                            else ...[
                              Text(
                                l.tellMore,
                                style: AppText.body.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              CupertinoTextField(
                                onTapOutside: (_) => FocusManager
                                    .instance
                                    .primaryFocus
                                    ?.unfocus(),
                                controller: _text,
                                placeholder: l.tellMoreHint,
                                maxLines: 4,
                                minLines: 3,
                                maxLength: 1000,
                                padding: const EdgeInsets.all(14),
                                style: AppText.body,
                                decoration: BoxDecoration(
                                  color: AppColors.background,
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                            ],
                            const SizedBox(height: 16),
                            BigButton(
                              label: l.reportSend,
                              icon: CupertinoIcons.paperplane_fill,
                              loading: _busy,
                              onPressed: _send,
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: AppText.secondary,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Whole row is tappable; checkbox scaled up for older users.
class _CheckRow extends StatelessWidget {
  const _CheckRow({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => Semantics(
    checked: value,
    button: true,
    label: label,
    excludeSemantics: true,
    child: GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () {
        HapticFeedback.selectionClick();
        onChanged(!value);
      },
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 52),
        child: Row(
          children: [
            Transform.scale(
              scale: 1.3,
              child: CupertinoCheckbox(
                value: value,
                onChanged: (v) => onChanged(v ?? false),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(child: Text(label, style: AppText.body)),
          ],
        ),
      ),
    ),
  );
}

/// Leaves the report flow; when it was opened straight from a notification there is nothing to pop.
void _close(BuildContext context) {
  if (context.canPop()) {
    context.pop();
  } else {
    context.go('/home');
  }
}

class ReportThanksScreen extends StatelessWidget {
  const ReportThanksScreen({super.key, required this.queued, this.note});

  final bool queued;

  /// Replaces the default body text (e.g. "already reported today").
  final String? note;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return CupertinoPageScaffold(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),
              Container(
                width: 120,
                height: 120,
                decoration: const BoxDecoration(
                  color: Color(0xFFDCFCE7),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  CupertinoIcons.heart_fill,
                  size: 60,
                  color: Color(0xFF16A34A),
                ),
              ),
              const SizedBox(height: 28),
              Text(
                l.thanksTitle,
                textAlign: TextAlign.center,
                style: AppText.title.copyWith(fontSize: 26),
              ),
              const SizedBox(height: 12),
              Text(
                note ?? (queued ? l.thanksQueued : l.thanksBody),
                textAlign: TextAlign.center,
                style: AppText.secondary,
              ),
              const Spacer(),
              BigButton(label: l.done, onPressed: () => _close(context)),
            ],
          ),
        ),
      ),
    );
  }
}

/// One-tap report for a known scammer, opened from the post-call notification.
class QuickReportScreen extends ConsumerStatefulWidget {
  const QuickReportScreen({super.key, required this.args});

  final ReportArgs args;

  @override
  ConsumerState<QuickReportScreen> createState() => _QuickReportScreenState();
}

class _QuickReportScreenState extends ConsumerState<QuickReportScreen> {
  late Future<bool> _sending = _send();

  Future<bool> _send() =>
      ref.read(reportControllerProvider).quickReport(widget.args);

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return FutureBuilder<bool>(
      future: _sending,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return CupertinoPageScaffold(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CupertinoActivityIndicator(radius: 16),
                  const SizedBox(height: 16),
                  Text(l.quickReportSending, style: AppText.secondary),
                ],
              ),
            ),
          );
        }
        final error = snap.error;
        if (error == null) return ReportThanksScreen(queued: !snap.data!);
        // Already reported today still means the number is in the database.
        if (error is ApiException && error.code == 'DUPLICATE_REPORT') {
          return ReportThanksScreen(queued: false, note: l.errDuplicateReport);
        }
        return CupertinoPageScaffold(
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const Spacer(),
                  Text(
                    errorText(l, error),
                    textAlign: TextAlign.center,
                    style: AppText.body,
                  ),
                  const SizedBox(height: 16),
                  BigButton(
                    label: l.retry,
                    onPressed: () => setState(() => _sending = _send()),
                  ),
                  const Spacer(),
                  CupertinoButton(
                    onPressed: () => _close(context),
                    child: Text(l.close),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
