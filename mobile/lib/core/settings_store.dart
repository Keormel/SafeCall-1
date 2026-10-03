import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

/// Small user preferences. Secrets live in [AuthStore], data in [AppDatabase].
class AppSettings {
  const AppSettings({
    required this.onboardingDone,
    required this.languageCode,
    required this.notificationsEnabled,
    required this.apiBaseUrl,
  });

  final bool onboardingDone;
  final String languageCode;
  final bool notificationsEnabled;
  final String apiBaseUrl;

  AppSettings copyWith({
    bool? onboardingDone,
    String? languageCode,
    bool? notificationsEnabled,
    String? apiBaseUrl,
  }) => AppSettings(
    onboardingDone: onboardingDone ?? this.onboardingDone,
    languageCode: languageCode ?? this.languageCode,
    notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
    apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
  );
}

class SettingsStore {
  SettingsStore(this._prefs);

  final SharedPreferences _prefs;

  static Future<SettingsStore> load() async =>
      SettingsStore(await SharedPreferences.getInstance());

  AppSettings read() => AppSettings(
    onboardingDone: _prefs.getBool('onboarding_done') ?? false,
    languageCode: _prefs.getString('language') ?? 'ru',
    notificationsEnabled: _prefs.getBool('notifications') ?? true,
    apiBaseUrl: _prefs.getString('api_base_url') ?? defaultApiBaseUrl(),
  );

  Future<void> write(AppSettings s) async {
    await _prefs.setBool('onboarding_done', s.onboardingDone);
    await _prefs.setString('language', s.languageCode);
    await _prefs.setBool('notifications', s.notificationsEnabled);
    await _prefs.setString('api_base_url', s.apiBaseUrl);
  }
}
