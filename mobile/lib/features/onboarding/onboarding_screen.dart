import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _pages = PageController();
  int _page = 0;
  bool _busy = false;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _next() => _pages.nextPage(
    duration: const Duration(milliseconds: 280),
    curve: Curves.easeOut,
  );

  Future<void> _finish({required bool enable}) async {
    setState(() => _busy = true);
    if (enable) {
      await ref.read(notificationsProvider).requestPermission();
      await ref.read(protectionProvider.notifier).request();
    }
    await ref.read(settingsProvider.notifier).completeOnboarding();
    if (mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final slides = [
      (CupertinoIcons.ear, l.onb1Title, l.onb1Body),
      (CupertinoIcons.device_phone_portrait, l.onb2Title, l.onb2Body),
      (CupertinoIcons.shield_lefthalf_fill, l.onb3Title, l.onb3Body),
    ];
    final last = _page == slides.length - 1;

    return CupertinoPageScaffold(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: AnimatedOpacity(
                  opacity: last ? 0 : 1,
                  duration: const Duration(milliseconds: 200),
                  child: CupertinoButton(
                    onPressed: last
                        ? null
                        : () => _pages.jumpToPage(slides.length - 1),
                    child: Text(l.onbSkip),
                  ),
                ),
              ),
              Expanded(
                child: PageView(
                  controller: _pages,
                  onPageChanged: (i) => setState(() => _page = i),
                  children: [
                    for (final (icon, title, body) in slides)
                      _Slide(icon: icon, title: title, body: body),
                  ],
                ),
              ),
              _Dots(count: slides.length, index: _page),
              const SizedBox(height: 24),
              if (last) ...[
                BigButton(
                  label: l.onbEnable,
                  icon: CupertinoIcons.shield_fill,
                  loading: _busy,
                  onPressed: () => _finish(enable: true),
                ),
                const SizedBox(height: 8),
                CupertinoButton(
                  onPressed: _busy ? null : () => _finish(enable: false),
                  child: Text(l.onbLater),
                ),
              ] else ...[
                BigButton(label: l.onbNext, onPressed: _next),
                const SizedBox(height: 52),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Slide extends StatelessWidget {
  const _Slide({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    child: Column(
      children: [
        const SizedBox(height: 32),
        Container(
          width: 132,
          height: 132,
          decoration: const BoxDecoration(
            color: AppColors.primarySoft,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 64, color: AppColors.primary),
        ),
        const SizedBox(height: 32),
        Text(
          title,
          textAlign: TextAlign.center,
          style: AppText.title.copyWith(fontSize: 28),
        ),
        const SizedBox(height: 16),
        Text(
          body,
          textAlign: TextAlign.center,
          style: AppText.body.copyWith(color: AppColors.textSecondary),
        ),
      ],
    ),
  );
}

class _Dots extends StatelessWidget {
  const _Dots({required this.count, required this.index});

  final int count;
  final int index;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      for (var i = 0; i < count; i++)
        AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          margin: const EdgeInsets.symmetric(horizontal: 4),
          width: i == index ? 22 : 8,
          height: 8,
          decoration: BoxDecoration(
            color: i == index ? AppColors.primary : AppColors.separator,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
    ],
  );
}
