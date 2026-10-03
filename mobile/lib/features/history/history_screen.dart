import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import 'call_tile.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final calls = ref.watch(callEventsProvider(null));

    return CupertinoPageScaffold(
      child: CustomScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        slivers: [
          CupertinoSliverNavigationBar(
            largeTitle: Text(l.historyTitle),
            border: null,
          ),
          CupertinoSliverRefreshControl(
            onRefresh: () async => ref.invalidate(callEventsProvider),
          ),
          SliverSafeArea(
            top: false,
            sliver: SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
              sliver: switch (calls) {
                AsyncData(:final value) when value.isEmpty =>
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 60),
                      child: EmptyState(
                        icon: CupertinoIcons.clock,
                        text: l.historyEmpty,
                      ),
                    ),
                  ),
                AsyncData(:final value) => SliverToBoxAdapter(
                  child: AppCard(
                    padding: const EdgeInsets.fromLTRB(20, 4, 8, 4),
                    child: Column(
                      children: [
                        for (var i = 0; i < value.length; i++) ...[
                          if (i > 0)
                            Container(height: 0.5, color: AppColors.separator),
                          CallTile(event: value[i]),
                        ],
                      ],
                    ),
                  ),
                ),
                AsyncError() => SliverToBoxAdapter(
                  child: EmptyState(
                    icon: CupertinoIcons.exclamationmark_circle,
                    text: l.errGeneric,
                  ),
                ),
                _ => const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.only(top: 60),
                    child: CupertinoActivityIndicator(),
                  ),
                ),
              },
            ),
          ),
        ],
      ),
    );
  }
}
