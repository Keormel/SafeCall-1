import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/api_client.dart';
import 'core/auth.dart';
import 'core/db/app_database.dart';
import 'core/notifications.dart';
import 'core/providers.dart';
import 'core/settings_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settingsStore = await SettingsStore.load();
  final settings = settingsStore.read();
  final auth = await AuthStore.load();
  final db = await AppDatabase.open();
  final notifications = await Notifications.init(settings.languageCode);

  runApp(
    ProviderScope(
      overrides: [
        settingsStoreProvider.overrideWithValue(settingsStore),
        databaseProvider.overrideWithValue(db),
        apiClientProvider.overrideWithValue(
          ApiClient(baseUrl: settings.apiBaseUrl, auth: auth),
        ),
        notificationsProvider.overrideWithValue(notifications),
      ],
      child: const SafeCallApp(),
    ),
  );
}
