import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/models.dart';
import '../../core/notifications.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';

/// One call: masked number, time, status chip and a "Report" action.
class CallTile extends StatelessWidget {
  const CallTile({super.key, required this.event, this.dense = false});

  final CallEvent event;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final locale = Localizations.localeOf(context).toLanguageTag();
    final time = DateFormat.MMMd(locale).add_Hm().format(event.time);

    return Padding(
      padding: EdgeInsets.symmetric(vertical: dense ? 8 : 12),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  event.phone,
                  style: AppText.body.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(time, style: AppText.secondary),
                const SizedBox(height: 6),
                RiskChip(event.level),
              ],
            ),
          ),
          if (event.reported)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Row(
                children: [
                  const Icon(
                    CupertinoIcons.checkmark_alt,
                    size: 18,
                    color: AppColors.textSecondary,
                  ),
                  const SizedBox(width: 4),
                  Text(l.reportedLabel, style: AppText.secondary),
                ],
              ),
            )
          else
            CupertinoButton(
              minimumSize: const Size(44, 44),
              onPressed: () => context.push(
                Notifications.reportLocation(
                  phone: event.phone,
                  level: event.level,
                  eventId: event.id,
                ),
              ),
              child: Text(l.reportAction),
            ),
        ],
      ),
    );
  }
}
