import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';

/// Manual number check on the home screen. `null` = nothing checked yet.
final checkControllerProvider =
    NotifierProvider<CheckController, AsyncValue<CheckResult>?>(
      CheckController.new,
    );

class CheckController extends Notifier<AsyncValue<CheckResult>?> {
  @override
  AsyncValue<CheckResult>? build() => null;

  Future<void> check(String raw) async {
    if (raw.trim().isEmpty) return;
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(numbersRepositoryProvider).check(raw.trim()),
    );
  }

  void clear() => state = null;
}
