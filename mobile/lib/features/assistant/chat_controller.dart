import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/providers.dart';

/// Chat history lives only in memory and is never written to disk.
class ChatState {
  const ChatState({this.messages = const [], this.typing = false, this.error});

  final List<ChatMessage> messages;
  final bool typing;

  /// Last failure, shown under the conversation; not part of the dialogue sent to the server.
  final Object? error;
}

final chatControllerProvider = NotifierProvider<ChatController, ChatState>(
  ChatController.new,
);

class ChatController extends Notifier<ChatState> {
  // Backend limits: at most 20 messages of 1000 characters each.
  static const _maxMessages = 20;
  static const _maxChars = 1000;

  @override
  ChatState build() => const ChatState();

  Future<void> send(String text) async {
    final content = text.trim();
    if (content.isEmpty || state.typing) return;
    final clipped = content.length > _maxChars
        ? content.substring(0, _maxChars)
        : content;
    final messages = [...state.messages, ChatMessage(ChatRole.user, clipped)];
    state = ChatState(messages: messages, typing: true);
    await _ask(messages);
  }

  /// Re-sends the dialogue after a failure (the last message is the unanswered question).
  Future<void> retry() async {
    if (state.typing || state.messages.isEmpty) return;
    state = ChatState(messages: state.messages, typing: true);
    await _ask(state.messages);
  }

  Future<void> _ask(List<ChatMessage> messages) async {
    final window = messages.length > _maxMessages
        ? messages.sublist(messages.length - _maxMessages)
        : messages;
    try {
      final reply = await ref.read(apiClientProvider).chat(window);
      if (!ref.mounted) return;
      state = ChatState(
        messages: [...messages, ChatMessage(ChatRole.assistant, reply)],
      );
    } on ApiException catch (e) {
      if (!ref.mounted) return;
      state = ChatState(messages: messages, error: e);
    }
  }

  void reset() => state = const ChatState();
}
