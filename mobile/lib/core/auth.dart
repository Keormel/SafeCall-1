import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

/// Random install id and the JWT issued for it, kept in the Keychain / Android Keystore.
class AuthStore {
  AuthStore._(this._storage, this.deviceId, this._token);

  static const _kDeviceId = 'device_id';
  static const _kToken = 'access_token';

  final FlutterSecureStorage _storage;
  final String deviceId;
  String? _token;

  String? get token => _token;

  static Future<AuthStore> load() async {
    const storage = FlutterSecureStorage();
    var deviceId = await storage.read(key: _kDeviceId);
    if (deviceId == null) {
      deviceId = const Uuid().v4();
      await storage.write(key: _kDeviceId, value: deviceId);
    }
    return AuthStore._(storage, deviceId, await storage.read(key: _kToken));
  }

  Future<void> saveToken(String? token) async {
    _token = token;
    if (token == null) {
      await _storage.delete(key: _kToken);
    } else {
      await _storage.write(key: _kToken, value: token);
    }
  }
}
