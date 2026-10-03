import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/models.dart';
import 'core/providers.dart';
import 'core/theme.dart';
import 'core/ui.dart';
import 'features/assistant/chat_screen.dart';
import 'features/debug/simulate_call_screen.dart';
import 'features/history/history_screen.dart';
import 'features/home/home_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/report/report_controller.dart';
import 'features/report/report_screen.dart';
import 'features/settings/settings_screen.dart';
import 'l10n/app_localizations.dart';

final _rootKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final launch = ref.read(notificationsProvider).launchLocation;
  final router = GoRouter(
    navigatorKey: _rootKey,
    initialLocation: launch ?? '/home',
    redirect: (_, state) {
      final done = ref.read(settingsProvider).onboardingDone;
      final atOnboarding = state.matchedLocation == '/onboarding';
      if (!done && !atOnboarding) return '/onboarding';
      if (done && atOnboarding) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/onboarding', builder: (_, _) => const OnboardingScreen()),
      StatefulShellRoute.indexedStack(
        builder: (_, _, shell) => _TabShell(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/assistant',
                builder: (_, _) => const ChatScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/history',
                builder: (_, _) => const HistoryScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                builder: (_, _) => const SettingsScreen(),
                routes: [
                  GoRoute(
                    path: 'how',
                    builder: (context, _) => InfoScreen(
                      title: context.l10n.howItWorks,
                      sections: [
                        (
                          CupertinoIcons.shield_lefthalf_fill,
                          null,
                          context.l10n.howItWorksBody,
                        ),
                      ],
                    ),
                  ),
                  GoRoute(
                    path: 'privacy',
                    builder: (context, _) => InfoScreen(
                      title: context.l10n.privacy,
                      sections: [
                        (
                          CupertinoIcons.device_phone_portrait,
                          context.l10n.privacyStored,
                          context.l10n.privacyStoredBody,
                        ),
                        (
                          CupertinoIcons.eye_slash_fill,
                          context.l10n.privacyNotStored,
                          context.l10n.privacyNotStoredBody,
                        ),
                      ],
                    ),
                  ),
                  if (kDebugMode)
                    GoRoute(
                      path: 'simulate',
                      builder: (_, _) => const SimulateCallScreen(),
                    ),
                ],
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/quick-report',
        parentNavigatorKey: _rootKey,
        redirect: (_, state) =>
            state.uri.queryParameters['phone'] == null ? '/home' : null,
        pageBuilder: (_, state) {
          final q = state.uri.queryParameters;
          return CupertinoPage(
            fullscreenDialog: true,
            child: QuickReportScreen(
              args: ReportArgs(
                phone: q['phone']!,
                level: RiskLevel.parse(q['level']),
                eventId: int.tryParse(q['event'] ?? ''),
              ),
            ),
          );
        },
      ),
      GoRoute(
        path: '/report',
        parentNavigatorKey: _rootKey,
        redirect: (_, state) =>
            state.uri.queryParameters['phone'] == null ? '/home' : null,
        pageBuilder: (_, state) {
          final q = state.uri.queryParameters;
          return CupertinoPage(
            fullscreenDialog: true,
            child: ReportScreen(
              args: ReportArgs(
                phone: q['phone']!,
                level: RiskLevel.parse(q['level']),
                eventId: int.tryParse(q['event'] ?? ''),
                suspicious: q['suspicious'] == '1',
              ),
            ),
          );
        },
        routes: [
          GoRoute(
            path: 'thanks',
            parentNavigatorKey: _rootKey,
            pageBuilder: (_, state) => CupertinoPage(
              fullscreenDialog: true,
              child: ReportThanksScreen(
                queued: state.uri.queryParameters['queued'] == 'true',
              ),
            ),
          ),
        ],
      ),
    ],
  );
  ref.read(notificationsProvider).onOpen = router.push;
  ref.onDispose(router.dispose);
  return router;
});

class SafeCallApp extends ConsumerStatefulWidget {
  const SafeCallApp({super.key});

  @override
  ConsumerState<SafeCallApp> createState() => _SafeCallAppState();
}

class _SafeCallAppState extends ConsumerState<SafeCallApp> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    // Protection is toggled in system settings, so re-check whenever we come back.
    _lifecycle = AppLifecycleListener(
      onResume: () {
        ref.read(protectionProvider.notifier).refresh();
        ref.read(overlayProvider.notifier).refresh();
        ref.read(syncControllerProvider.notifier).syncIfStale();
        ref.invalidate(callEventsProvider);
      },
    );
    ref
        .read(syncControllerProvider.notifier)
        .syncIfStale(maxAge: Duration.zero);
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final language = ref.watch(settingsProvider.select((s) => s.languageCode));
    return CupertinoApp.router(
      onGenerateTitle: (context) => context.l10n.appName,
      debugShowCheckedModeBanner: false,
      theme: appTheme,
      locale: Locale(language),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      routerConfig: ref.watch(routerProvider),
    );
  }
}

class _TabShell extends StatelessWidget {
  const _TabShell({required this.shell});

  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    // The keyboard covers the tab bar anyway; hiding it keeps the page from being inset twice.
    final keyboardOpen = MediaQuery.viewInsetsOf(context).bottom > 0;
    return Column(
      children: [
        // The tab bar handles the bottom safe area itself.
        Expanded(
          child: MediaQuery.removePadding(
            context: context,
            removeBottom: !keyboardOpen,
            child: shell,
          ),
        ),
        if (!keyboardOpen)
          CupertinoTabBar(
            backgroundColor:
                AppColors.card, // opaque: no per-frame background blur
            currentIndex: shell.currentIndex,
            activeColor: AppColors.primary,
            iconSize: 28,
            height: 56,
            onTap: (i) =>
                shell.goBranch(i, initialLocation: i == shell.currentIndex),
            items: [
              BottomNavigationBarItem(
                icon: const Icon(CupertinoIcons.shield_fill),
                label: l.tabHome,
              ),
              BottomNavigationBarItem(
                icon: const Icon(CupertinoIcons.chat_bubble_2_fill),
                label: l.tabAssistant,
              ),
              BottomNavigationBarItem(
                icon: const Icon(CupertinoIcons.clock_fill),
                label: l.tabHistory,
              ),
              BottomNavigationBarItem(
                icon: const Icon(CupertinoIcons.gear_solid),
                label: l.tabSettings,
              ),
            ],
          ),
      ],
    );
  }
}
