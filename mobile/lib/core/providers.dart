import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/app_localizations.dart';

import 'api_client.dart';
import 'db/app_database.dart';
import 'models.dart';
import 'native_bridge.dart';
import 'notifications.dart';
import 'repositories.dart';
import 'settings_store.dart';

// --- infrastructure, created in main() and injected with overrides

final databaseProvider = Provider<AppDatabase>(
  (_) => throw UnimplementedError(),
);
final apiClientProvider = Provider<ApiClient>(
  (_) => throw UnimplementedError(),
);
final settingsStoreProvider = Provider<SettingsStore>(
  (_) => throw UnimplementedError(),
);
final notificationsProvider = Provider<Notifications>(
  (_) => throw UnimplementedError(),
);
final nativeBridgeProvider = Provider<NativeBridge>((_) => NativeBridge());

final numbersRepositoryProvider = Provider(
  (ref) => NumbersRepository(
    ref.watch(apiClientProvider),
    ref.watch(databaseProvider),
  ),
);
final reportsRepositoryProvider = Provider(
  (ref) => ReportsRepository(
    ref.watch(apiClientProvider),
    ref.watch(databaseProvider),
  ),
);
final callFlowProvider = Provider(
  (ref) =>
      CallFlow(ref.watch(databaseProvider), ref.watch(notificationsProvider)),
);

// --- settings

final settingsProvider = NotifierProvider<SettingsController, AppSettings>(
  SettingsController.new,
);

class SettingsController extends Notifier<AppSettings> {
  @override
  AppSettings build() => ref.watch(settingsStoreProvider).read();

  Future<void> _save(AppSettings next) async {
    state = next;
    await ref.read(settingsStoreProvider).write(next);
  }

  Future<void> completeOnboarding() =>
      _save(state.copyWith(onboardingDone: true));
  Future<void> setLanguage(String code) async {
    await _save(state.copyWith(languageCode: code));
    await ref
        .read(syncControllerProvider.notifier)
        .updateCallerId(); // relabel in the new language
  }

  Future<void> setNotifications(bool on) =>
      _save(state.copyWith(notificationsEnabled: on));

  Future<void> setApiBaseUrl(String url) async {
    await _save(state.copyWith(apiBaseUrl: url.trim()));
    ref.read(apiClientProvider).baseUrl = state.apiBaseUrl;
    // A different server has a different database.
    await ref.read(numbersRepositoryProvider).reset();
    await ref.read(syncControllerProvider.notifier).sync();
  }
}

// --- number database sync

class SyncState {
  const SyncState({
    this.count = 0,
    this.lastSync,
    this.syncing = false,
    this.error,
  });

  final int count;
  final DateTime? lastSync;
  final bool syncing;
  final ApiException? error;
}

final syncControllerProvider = NotifierProvider<SyncController, SyncState>(
  SyncController.new,
);

class SyncController extends Notifier<SyncState> {
  @override
  SyncState build() {
    _refreshStats();
    return const SyncState();
  }

  Future<void> _refreshStats({ApiException? error}) async {
    final repo = ref.read(numbersRepositoryProvider);
    state = SyncState(
      count: await repo.count(),
      lastSync: await repo.lastSync(),
      error: error,
    );
  }

  /// Sync unless one ran recently (app start / resume).
  Future<void> syncIfStale({Duration maxAge = const Duration(hours: 1)}) async {
    final last = await ref.read(numbersRepositoryProvider).lastSync();
    if (last == null || DateTime.now().difference(last) > maxAge) await sync();
  }

  Future<void> sync() async {
    if (state.syncing) return;
    state = SyncState(
      count: state.count,
      lastSync: state.lastSync,
      syncing: true,
    );
    ApiException? error;
    try {
      await ref.read(reportsRepositoryProvider).flushOutbox();
      await ref.read(numbersRepositoryProvider).sync();
    } on ApiException catch (e) {
      error = e;
    }
    await _refreshStats(error: error);
    if (error == null) await updateCallerId();
  }

  /// Pushes warned numbers to the OS caller ID (iOS Call Directory), labeled in the app language.
  Future<void> updateCallerId() async {
    final l = lookupAppLocalizations(
      Locale(ref.read(settingsProvider).languageCode),
    );
    final lines = await ref
        .read(numbersRepositoryProvider)
        .callerIdLines(
          highLabel: l.callerIdHigh,
          mediumLabel: l.callerIdMedium,
        );
    await ref.read(nativeBridgeProvider).updateCallDirectory(lines);
  }
}

// --- protection (native call screening / call directory)

final protectionProvider = AsyncNotifierProvider<ProtectionController, bool>(
  ProtectionController.new,
);

class ProtectionController extends AsyncNotifier<bool> {
  @override
  Future<bool> build() => ref.read(nativeBridgeProvider).isProtectionEnabled();

  Future<void> refresh() async {
    final was = state.value ?? false;
    final enabled = await ref.read(nativeBridgeProvider).isProtectionEnabled();
    state = AsyncData(enabled);
    // Just switched on in Settings: make sure the OS has the current list.
    if (enabled && !was) {
      await ref.read(syncControllerProvider.notifier).updateCallerId();
    }
  }

  Future<void> request() => ref.read(nativeBridgeProvider).requestProtection();

  Future<void> openSettings() =>
      ref.read(nativeBridgeProvider).openProtectionSettings();
}

// --- Android: warning card over the call screen

final overlayProvider = AsyncNotifierProvider<OverlayController, bool>(
  OverlayController.new,
);

class OverlayController extends AsyncNotifier<bool> {
  @override
  Future<bool> build() => ref.read(nativeBridgeProvider).canDrawOverlays();

  Future<void> refresh() async =>
      state = AsyncData(await ref.read(nativeBridgeProvider).canDrawOverlays());

  Future<void> request() => ref.read(nativeBridgeProvider).requestOverlay();
}

final isXiaomiProvider = FutureProvider<bool>(
  (ref) => ref.watch(nativeBridgeProvider).isXiaomi(),
);

// --- call history

final callEventsProvider = FutureProvider.family<List<CallEvent>, int?>(
  (ref, limit) => ref.watch(databaseProvider).callEvents(limit: limit),
);
