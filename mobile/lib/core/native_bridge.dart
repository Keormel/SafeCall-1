import 'package:flutter/services.dart';

/// Platform channel to the native call-protection layer.
///
/// iOS: CallKit Call Directory extension status and its Settings page.
/// Android: RoleManager ROLE_CALL_SCREENING (native side not implemented yet).
/// When the native side is missing, protection reports as off and the app keeps working.
class NativeBridge {
  static const _channel = MethodChannel('safecall/native');

  Future<bool> isProtectionEnabled() async {
    try {
      return await _channel.invokeMethod<bool>('isProtectionEnabled') ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  /// Asks the OS to grant protection; re-check [isProtectionEnabled] when the app resumes.
  Future<void> requestProtection() => _invoke('requestProtection');

  /// Opens the system page where protection can be turned on or off.
  Future<void> openProtectionSettings() => _invoke('openRoleSettings');

  /// Hands the caller-ID list (`digits<TAB>label` lines, ascending) to the iOS Call Directory.
  Future<void> updateCallDirectory(String lines) =>
      _invoke('updateCallDirectory', {'lines': lines});

  Future<void> _invoke(String method, [Object? arguments]) async {
    try {
      await _channel.invokeMethod<void>(method, arguments);
    } on MissingPluginException {
      // No native implementation on this platform yet.
    } on PlatformException {
      // The OS refused or the page is unavailable; nothing else to do.
    }
  }
}
