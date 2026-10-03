import 'package:flutter/foundation.dart';

const appVersion = '1.0.0';

/// Default backend address. Override at build time:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
/// or at runtime in Settings (needed for a physical iPhone).
String defaultApiBaseUrl() {
  const fromEnv = String.fromEnvironment('API_BASE_URL');
  if (fromEnv.isNotEmpty) return fromEnv;
  // The Android emulator reaches the host via 10.0.2.2; the iOS simulator and web use localhost.
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
}
