import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import 'chat_controller.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send([String? preset]) {
    final text = preset ?? _input.text;
    if (text.trim().isEmpty) return;
    _input.clear();
    ref.read(chatControllerProvider.notifier).send(text);
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final chat = ref.watch(chatControllerProvider);
    ref.listen(chatControllerProvider, (_, _) => _scrollToEnd());
    final chips = [l.chipBank, l.chipCode, l.chipUnknown, l.chipTransfer];

    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(
        middle: Text(l.assistantTitle),
        trailing: chat.messages.isEmpty
            ? null
            : CupertinoButton(
                padding: EdgeInsets.zero,
                onPressed: () =>
                    ref.read(chatControllerProvider.notifier).reset(),
                child: Text(l.newChat),
              ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                controller: _scroll,
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                children: [
                  _Bubble(text: l.assistantWelcome, fromUser: false),
                  for (final m in chat.messages) ...[
                    _Bubble(text: m.content, fromUser: m.role == ChatRole.user),
                    if (m.role == ChatRole.assistant)
                      _Disclaimer(l.assistantDisclaimer),
                  ],
                  if (chat.typing) const _TypingBubble(),
                  if (chat.error != null)
                    _ErrorRow(message: errorText(l, chat.error!)),
                ],
              ),
            ),
            SizedBox(
              height: 52,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 4,
                ),
                itemCount: chips.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (_, i) => _Chip(
                  label: chips[i],
                  onTap: chat.typing ? null : () => _send(chips[i]),
                ),
              ),
            ),
            _Composer(controller: _input, enabled: !chat.typing, onSend: _send),
          ],
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.text, required this.fromUser});

  final String text;
  final bool fromUser;

  @override
  Widget build(BuildContext context) => Align(
    alignment: fromUser ? Alignment.centerRight : Alignment.centerLeft,
    child: Container(
      margin: const EdgeInsets.only(top: 8),
      constraints: BoxConstraints(
        maxWidth: MediaQuery.sizeOf(context).width * 0.8,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: fromUser ? AppColors.primary : AppColors.card,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(20),
          topRight: const Radius.circular(20),
          bottomLeft: Radius.circular(fromUser ? 20 : 6),
          bottomRight: Radius.circular(fromUser ? 6 : 20),
        ),
        boxShadow: fromUser
            ? null
            : const [
                BoxShadow(
                  color: Color(0x0D0F172A),
                  blurRadius: 10,
                  offset: Offset(0, 2),
                ),
              ],
      ),
      child: Text(
        text,
        style: AppText.body.copyWith(
          color: fromUser ? CupertinoColors.white : AppColors.text,
        ),
      ),
    ),
  );
}

class _Disclaimer extends StatelessWidget {
  const _Disclaimer(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(6, 6, 48, 4),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 2),
          child: Icon(
            CupertinoIcons.info_circle,
            size: 16,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(text, style: AppText.secondary.copyWith(fontSize: 14)),
        ),
      ],
    ),
  );
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.centerLeft,
    child: Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CupertinoActivityIndicator(radius: 9),
          const SizedBox(width: 10),
          Text(context.l10n.typing, style: AppText.secondary),
        ],
      ),
    ),
  );
}

class _ErrorRow extends ConsumerWidget {
  const _ErrorRow({required this.message});

  final String message;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              CupertinoIcons.wifi_exclamationmark,
              size: 18,
              color: Color(0xFF991B1B),
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                message,
                style: AppText.secondary.copyWith(
                  color: const Color(0xFF991B1B),
                ),
              ),
            ),
          ],
        ),
        CupertinoButton(
          onPressed: () => ref.read(chatControllerProvider.notifier).retry(),
          child: Text(context.l10n.retry),
        ),
      ],
    ),
  );
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => CupertinoButton(
    padding: const EdgeInsets.symmetric(horizontal: 14),
    minimumSize: const Size(44, 44),
    color: AppColors.primarySoft,
    borderRadius: BorderRadius.circular(22),
    onPressed: onTap,
    child: Text(
      label,
      style: const TextStyle(
        fontSize: 15,
        color: AppColors.primary,
        fontWeight: FontWeight.w500,
      ),
    ),
  );
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.enabled,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final void Function([String?]) onSend;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
      decoration: const BoxDecoration(
        color: AppColors.card,
        border: Border(top: BorderSide(color: AppColors.separator, width: 0.5)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: CupertinoTextField(
              onTapOutside: (_) =>
                  FocusManager.instance.primaryFocus?.unfocus(),
              controller: controller,
              placeholder: l.messageHint,
              minLines: 1,
              maxLines: 4,
              maxLength: 1000,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSend(),
              style: AppText.body,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(22),
              ),
            ),
          ),
          Semantics(
            button: true,
            label: l.send,
            child: CupertinoButton(
              padding: const EdgeInsets.all(6),
              minimumSize: const Size(48, 48),
              onPressed: enabled ? () => onSend() : null,
              child: const Icon(CupertinoIcons.arrow_up_circle_fill, size: 40),
            ),
          ),
        ],
      ),
    );
  }
}
