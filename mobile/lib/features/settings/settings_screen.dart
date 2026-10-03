import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/config.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final settings = ref.watch(settingsProvider);
    final sync = ref.watch(syncControllerProvider);
    final ctrl = ref.read(settingsProvider.notifier);

    return CupertinoPageScaffold(
      child: CustomScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        slivers: [
          CupertinoSliverNavigationBar(
            largeTitle: Text(l.settingsTitle),
            border: null,
          ),
          SliverSafeArea(
            top: false,
            sliver: SliverList.list(
              children: [
                CupertinoListSection.insetGrouped(
                  header: Text(l.sectionAbout),
                  children: [
                    _Row(
                      icon: CupertinoIcons.question_circle_fill,
                      color: AppColors.primary,
                      title: l.howItWorks,
                      onTap: () => context.push('/settings/how'),
                    ),
                    _Row(
                      icon: CupertinoIcons.lock_fill,
                      color: const Color(0xFF16A34A),
                      title: l.privacy,
                      onTap: () => context.push('/settings/privacy'),
                    ),
                  ],
                ),
                CupertinoListSection.insetGrouped(
                  header: Text(l.sectionDatabase),
                  children: [
                    CupertinoListTile(
                      leading: const _IconBox(
                        icon: CupertinoIcons.arrow_clockwise,
                        color: AppColors.primary,
                      ),
                      title: Text(l.updateDb),
                      subtitle: Text(l.dbCount(sync.count)),
                      trailing: sync.syncing
                          ? const CupertinoActivityIndicator()
                          : null,
                      onTap: sync.syncing
                          ? null
                          : () => ref
                                .read(syncControllerProvider.notifier)
                                .sync(),
                    ),
                  ],
                ),
                CupertinoListSection.insetGrouped(
                  header: Text(l.sectionNotifications),
                  children: [
                    CupertinoListTile(
                      leading: const _IconBox(
                        icon: CupertinoIcons.bell_fill,
                        color: Color(0xFFDC2626),
                      ),
                      title: Text(l.notifications),
                      trailing: CupertinoSwitch(
                        value: settings.notificationsEnabled,
                        onChanged: (on) async {
                          if (on) {
                            await ref
                                .read(notificationsProvider)
                                .requestPermission();
                          }
                          await ctrl.setNotifications(on);
                        },
                      ),
                    ),
                    if (defaultTargetPlatform == TargetPlatform.android)
                      CupertinoListTile(
                        leading: const _IconBox(
                          icon: CupertinoIcons.exclamationmark_shield_fill,
                          color: Color(0xFFDC2626),
                        ),
                        title: Text(l.overlayTitle),
                        subtitle: Text(
                          (ref.watch(overlayProvider).value ?? false)
                              ? l.overlayOn
                              : l.overlayOff,
                        ),
                        trailing: (ref.watch(overlayProvider).value ?? false)
                            ? const Icon(
                                CupertinoIcons.checkmark_alt,
                                color: Color(0xFF16A34A),
                              )
                            : const CupertinoListTileChevron(),
                        onTap: () =>
                            ref.read(overlayProvider.notifier).request(),
                      ),
                    if (ref.watch(isXiaomiProvider).value ?? false)
                      CupertinoListTile(
                        leading: const _IconBox(
                          icon: CupertinoIcons.wrench_fill,
                          color: Color(0xFFF59E0B),
                        ),
                        title: Text(l.xiaomiSetup),
                        subtitle: Text(l.xiaomiSetupHint, maxLines: 2),
                        trailing: const CupertinoListTileChevron(),
                        onTap: () => ref
                            .read(nativeBridgeProvider)
                            .openXiaomiPermissions(),
                      ),
                  ],
                ),
                CupertinoListSection.insetGrouped(
                  header: Text(l.language),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: CupertinoSlidingSegmentedControl<String>(
                        groupValue: settings.languageCode,
                        onValueChanged: (v) {
                          if (v != null) ctrl.setLanguage(v);
                        },
                        children: {
                          'ru': Padding(
                            padding: const EdgeInsets.all(10),
                            child: Text(l.langRu),
                          ),
                          'ro': Padding(
                            padding: const EdgeInsets.all(10),
                            child: Text(l.langRo),
                          ),
                        },
                      ),
                    ),
                  ],
                ),
                CupertinoListSection.insetGrouped(
                  children: [
                    CupertinoListTile(
                      leading: const _IconBox(
                        icon: CupertinoIcons.cloud_fill,
                        color: Color(0xFF64748B),
                      ),
                      title: Text(l.server),
                      subtitle: Text(settings.apiBaseUrl),
                      trailing: const CupertinoListTileChevron(),
                      onTap: () =>
                          _editServer(context, ref, settings.apiBaseUrl),
                    ),
                    CupertinoListTile(
                      leading: const _IconBox(
                        icon: CupertinoIcons.info,
                        color: Color(0xFF64748B),
                      ),
                      title: Text(l.version),
                      additionalInfo: const Text(appVersion),
                    ),
                  ],
                ),
                if (kDebugMode)
                  CupertinoListSection.insetGrouped(
                    header: Text(l.sectionDemo),
                    children: [
                      _Row(
                        icon: CupertinoIcons.phone_fill_arrow_down_left,
                        color: const Color(0xFFF59E0B),
                        title: l.simulateCall,
                        onTap: () => context.push('/settings/simulate'),
                      ),
                    ],
                  ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _editServer(
    BuildContext context,
    WidgetRef ref,
    String current,
  ) async {
    final l = context.l10n;
    final controller = TextEditingController(text: current);
    final url = await showCupertinoDialog<String>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(l.server),
        content: Column(
          children: [
            Text(l.serverHint),
            const SizedBox(height: 10),
            CupertinoTextField(
              controller: controller,
              keyboardType: TextInputType.url,
              autofocus: true,
            ),
          ],
        ),
        actions: [
          CupertinoDialogAction(
            onPressed: () => Navigator.pop(ctx),
            child: Text(l.cancel),
          ),
          CupertinoDialogAction(
            onPressed: () => Navigator.pop(ctx, defaultApiBaseUrl()),
            child: Text(l.resetDefault),
          ),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: Text(l.save),
          ),
        ],
      ),
    );
    controller.dispose();
    if (url != null && url.trim().isNotEmpty && url.trim() != current) {
      await ref.read(settingsProvider.notifier).setApiBaseUrl(url);
    }
  }
}

class _IconBox extends StatelessWidget {
  const _IconBox({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    width: 30,
    height: 30,
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(7),
    ),
    child: Icon(icon, size: 18, color: CupertinoColors.white),
  );
}

class _Row extends StatelessWidget {
  const _Row({
    required this.icon,
    required this.color,
    required this.title,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => CupertinoListTile(
    leading: _IconBox(icon: icon, color: color),
    title: Text(title),
    trailing: const CupertinoListTileChevron(),
    onTap: onTap,
  );
}

/// "How it works" and "Privacy" pages.
class InfoScreen extends StatelessWidget {
  const InfoScreen({super.key, required this.title, required this.sections});

  final String title;
  final List<(IconData, String?, String)> sections;

  @override
  Widget build(BuildContext context) => CupertinoPageScaffold(
    navigationBar: CupertinoNavigationBar(middle: Text(title)),
    child: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final (icon, heading, body) in sections) ...[
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: AppColors.primary, size: 26),
                      if (heading != null) ...[
                        const SizedBox(width: 10),
                        Expanded(child: Text(heading, style: AppText.headline)),
                      ],
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(body, style: AppText.body),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ],
      ),
    ),
  );
}
