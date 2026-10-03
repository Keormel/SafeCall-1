import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/repositories.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import '../../l10n/app_localizations.dart';

/// Debug-only: plays a whole call through the same code a real call uses —
/// on-device check and warning when it starts, the post-call notification when it ends.
class SimulateCallScreen extends ConsumerStatefulWidget {
  const SimulateCallScreen({super.key});

  @override
  ConsumerState<SimulateCallScreen> createState() => _SimulateCallScreenState();
}

enum _Phase { idle, inCall, ended }

class _SimulateCallScreenState extends ConsumerState<SimulateCallScreen> {
  // Seeded by `scripts.seed --reset`: a known scammer, and a number the server has no data on.
  static const _scamPhone = '+37367854919';
  static const _unknownPhone = '+37369000777';

  final _phone = TextEditingController();
  _Phase _phase = _Phase.idle;
  ScreenedCall? _call;
  bool _busy = false;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (_phone.text.trim().isEmpty) return;
    FocusScope.of(context).unfocus();
    setState(() => _busy = true);
    final s = ref.read(settingsProvider);
    final call = await ref
        .read(callFlowProvider)
        .handleIncomingCall(
          _phone.text,
          languageCode: s.languageCode,
          notificationsEnabled: s.notificationsEnabled,
        );
    ref.invalidate(callEventsProvider);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _call = call;
      _phase = _Phase.inCall;
    });
  }

  Future<void> _end() async {
    final s = ref.read(settingsProvider);
    setState(() => _phase = _Phase.ended);
    await ref
        .read(callFlowProvider)
        .handleCallEnded(
          _call!,
          languageCode: s.languageCode,
          notificationsEnabled: s.notificationsEnabled,
        );
  }

  void _reset() => setState(() {
    _phase = _Phase.idle;
    _call = null;
  });

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(middle: Text(l.simulateTitle)),
      child: SafeArea(
        child: ListView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.all(16),
          children: [
            AppCard(
              child: switch (_phase) {
                _Phase.idle => _idle(l),
                _Phase.inCall => _inCall(l),
                _Phase.ended => _ended(l),
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _idle(AppLocalizations l) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(l.simulateHint, style: AppText.secondary),
      const SizedBox(height: 14),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          _Preset(
            label: l.simulateScamPreset,
            color: const Color(0xFFDC2626),
            onTap: () => setState(() => _phone.text = _scamPhone),
          ),
          _Preset(
            label: l.simulateUnknownPreset,
            color: const Color(0xFFF59E0B),
            onTap: () => setState(() => _phone.text = _unknownPhone),
          ),
        ],
      ),
      const SizedBox(height: 14),
      CupertinoTextField(
        onTapOutside: (_) => FocusManager.instance.primaryFocus?.unfocus(),
        controller: _phone,
        placeholder: l.phoneHint,
        keyboardType: TextInputType.phone,
        style: const TextStyle(fontSize: 19, color: AppColors.text),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(14),
        ),
      ),
      const SizedBox(height: 12),
      BigButton(
        label: l.simulateCallButton,
        icon: CupertinoIcons.phone_fill_arrow_down_left,
        color: const Color(0xFF16A34A),
        loading: _busy,
        onPressed: _start,
      ),
    ],
  );

  Widget _inCall(AppLocalizations l) => Column(
    children: [
      const Icon(CupertinoIcons.phone_fill, size: 48, color: Color(0xFF16A34A)),
      const SizedBox(height: 12),
      Text(_call!.phone, style: AppText.title),
      const SizedBox(height: 4),
      Text(l.simulateInCall, style: AppText.secondary),
      const SizedBox(height: 12),
      RiskChip(_call!.level),
      const SizedBox(height: 20),
      BigButton(
        label: l.simulateEnd,
        icon: CupertinoIcons.phone_down_fill,
        color: const Color(0xFFDC2626),
        onPressed: _end,
      ),
    ],
  );

  Widget _ended(AppLocalizations l) => Column(
    children: [
      const Icon(CupertinoIcons.bell_fill, size: 44, color: AppColors.primary),
      const SizedBox(height: 12),
      Text(
        l.simulateEnded,
        textAlign: TextAlign.center,
        style: AppText.headline,
      ),
      const SizedBox(height: 20),
      BigButton(label: l.done, filled: false, onPressed: _reset),
    ],
  );
}

class _Preset extends StatelessWidget {
  const _Preset({
    required this.label,
    required this.color,
    required this.onTap,
  });

  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => CupertinoButton(
    padding: const EdgeInsets.symmetric(horizontal: 14),
    minimumSize: const Size(44, 44),
    color: color.withValues(alpha: 0.12),
    borderRadius: BorderRadius.circular(22),
    onPressed: onTap,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          CupertinoIcons.exclamationmark_circle_fill,
          size: 18,
          color: color,
        ),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            label,
            style: const TextStyle(fontSize: 15, color: AppColors.text),
          ),
        ),
      ],
    ),
  );
}
