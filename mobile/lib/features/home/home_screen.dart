import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models.dart';
import '../../core/notifications.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import '../history/call_tile.dart';
import 'check_controller.dart';
import 'protection_button.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final protection = ref.watch(protectionProvider).value ?? false;

    return CupertinoPageScaffold(
      child: CustomScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        slivers: [
          CupertinoSliverNavigationBar(
            largeTitle: Text(l.appName),
            border: null,
          ),
          CupertinoSliverRefreshControl(
            onRefresh: () => ref.read(syncControllerProvider.notifier).sync(),
          ),
          SliverSafeArea(
            top: false,
            sliver: SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
              sliver: SliverList.list(
                children: [
                  Center(
                    child: ProtectionButton(
                      enabled: protection,
                      onTap: () => _onProtectionTap(context, ref, protection),
                    ),
                  ),
                  const SizedBox(height: 24),
                  BigButton(
                    label: l.assistantButton,
                    icon: CupertinoIcons.chat_bubble_2_fill,
                    filled: false,
                    onPressed: () => context.go('/assistant'),
                  ),
                  const SizedBox(height: 16),
                  const _DatabaseCard(),
                  const SizedBox(height: 16),
                  const _ManualCheckCard(),
                  const SizedBox(height: 16),
                  const _RecentCallsCard(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _onProtectionTap(
    BuildContext context,
    WidgetRef ref,
    bool enabled,
  ) async {
    final l = context.l10n;
    final controller = ref.read(protectionProvider.notifier);
    HapticFeedback.selectionClick();
    final isIos = defaultTargetPlatform == TargetPlatform.iOS;
    if (!enabled && !isIos) {
      // Android: the system role dialog is the whole flow.
      await controller.request();
      return;
    }
    // Turning off is never possible from the app; on iOS turning on is done in Settings too.
    final open = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(enabled ? l.protectionOffTitle : l.protectionIosTitle),
        content: Text(enabled ? l.protectionOffBody : l.protectionIosBody),
        actions: [
          CupertinoDialogAction(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l.cancel),
          ),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l.openSettings),
          ),
        ],
      ),
    );
    if (open ?? false) await controller.openSettings();
  }
}

class _DatabaseCard extends ConsumerWidget {
  const _DatabaseCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final sync = ref.watch(syncControllerProvider);
    final last = sync.lastSync;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                CupertinoIcons.tray_full_fill,
                color: AppColors.primary,
                size: 28,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.dbCount(sync.count), style: AppText.headline),
                    Text(
                      last == null ? l.dbNever : l.dbUpdated(timeAgo(l, last)),
                      style: AppText.secondary,
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (sync.error != null) ...[
            const SizedBox(height: 10),
            Text(
              errorText(l, sync.error!),
              style: AppText.secondary.copyWith(color: const Color(0xFF991B1B)),
            ),
          ],
          const SizedBox(height: 14),
          BigButton(
            label: sync.syncing ? l.updating : l.updateNow,
            icon: CupertinoIcons.arrow_clockwise,
            filled: false,
            loading: sync.syncing,
            onPressed: () => ref.read(syncControllerProvider.notifier).sync(),
          ),
        ],
      ),
    );
  }
}

class _ManualCheckCard extends ConsumerStatefulWidget {
  const _ManualCheckCard();

  @override
  ConsumerState<_ManualCheckCard> createState() => _ManualCheckCardState();
}

class _ManualCheckCardState extends ConsumerState<_ManualCheckCard> {
  final _phone = TextEditingController();

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  void _check() {
    FocusScope.of(context).unfocus();
    ref.read(checkControllerProvider.notifier).check(_phone.text);
  }

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final result = ref.watch(checkControllerProvider);

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l.manualCheck, style: AppText.headline),
          const SizedBox(height: 12),
          CupertinoTextField(
            onTapOutside: (_) => FocusManager.instance.primaryFocus?.unfocus(),
            controller: _phone,
            placeholder: l.phoneHint,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.search,
            autofillHints: const [AutofillHints.telephoneNumber],
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9+()\- ]')),
            ],
            style: const TextStyle(fontSize: 19, color: AppColors.text),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
            prefix: const Padding(
              padding: EdgeInsets.only(left: 14),
              child: Icon(CupertinoIcons.phone, color: AppColors.textSecondary),
            ),
            clearButtonMode: OverlayVisibilityMode.editing,
            decoration: BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.circular(14),
            ),
            onSubmitted: (_) => _check(),
          ),
          const SizedBox(height: 12),
          BigButton(
            label: l.checkButton,
            icon: CupertinoIcons.search,
            loading: result?.isLoading ?? false,
            onPressed: _check,
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
            child: switch (result) {
              null || AsyncLoading() => const SizedBox(width: double.infinity),
              AsyncError(:final error) => Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Text(errorText(l, error), style: AppText.secondary),
              ),
              AsyncData(:final value) => Padding(
                padding: const EdgeInsets.only(top: 14),
                child: RiskResultCard(
                  result: value,
                  trailing: BigButton(
                    label: l.reportNumber,
                    icon: CupertinoIcons.flag_fill,
                    filled: false,
                    onPressed: () => context.push(
                      Notifications.reportLocation(
                        phone: value.phone,
                        level: value.riskLevel,
                      ),
                    ),
                  ),
                ),
              ),
            },
          ),
        ],
      ),
    );
  }
}

class _RecentCallsCard extends ConsumerWidget {
  const _RecentCallsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final calls = ref.watch(callEventsProvider(5));

    return AppCard(
      padding: const EdgeInsets.fromLTRB(20, 16, 8, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(l.recentCalls, style: AppText.headline)),
              CupertinoButton(
                onPressed: () => context.go('/history'),
                child: Text(l.allHistory),
              ),
            ],
          ),
          switch (calls) {
            AsyncData(value: final List<CallEvent> items) when items.isEmpty =>
              EmptyState(
                icon: CupertinoIcons.phone_badge_plus,
                text: l.noCalls,
              ),
            AsyncData(value: final List<CallEvent> items) => Column(
              children: [
                for (final e in items) CallTile(event: e, dense: true),
              ],
            ),
            AsyncError() => EmptyState(
              icon: CupertinoIcons.exclamationmark_circle,
              text: l.errGeneric,
            ),
            _ => const Padding(
              padding: EdgeInsets.all(16),
              child: CupertinoActivityIndicator(),
            ),
          },
        ],
      ),
    );
  }
}
