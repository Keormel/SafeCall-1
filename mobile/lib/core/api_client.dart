import 'package:dio/dio.dart';

import 'auth.dart';
import 'models.dart';

/// Backend error from the `{"error": {"code", "message"}}` envelope, or a transport failure.
class ApiException implements Exception {
  const ApiException(this.statusCode, this.code, this.message);

  final int statusCode;
  final String code;
  final String message;

  bool get isNetwork => code == 'NETWORK';

  /// Client errors that will fail the same way on retry, so queued items can be dropped.
  bool get isPermanent =>
      statusCode >= 400 &&
      statusCode < 500 &&
      statusCode != 401 &&
      statusCode != 429;

  @override
  String toString() => 'ApiException($statusCode $code)';
}

/// SafeCall API client (`/api/v1`). Registers the device on demand and re-authenticates on 401.
class ApiClient {
  ApiClient({required String baseUrl, required this.auth})
    : _dio = Dio(
        BaseOptions(
          baseUrl: _apiBase(baseUrl),
          connectTimeout: const Duration(seconds: 8),
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
          headers: {'Accept': 'application/json'},
        ),
      );

  final AuthStore auth;
  final Dio _dio;

  static String _apiBase(String url) {
    final trimmed = url.trim().replaceAll(RegExp(r'/+$'), '');
    return '$trimmed/api/v1';
  }

  set baseUrl(String url) => _dio.options.baseUrl = _apiBase(url);

  Future<void> authenticate() async {
    final json = await _send(
      'POST',
      '/auth/device',
      data: {'device_id': auth.deviceId},
      authorized: false,
    );
    await auth.saveToken(json['access_token'] as String);
  }

  Future<CheckResult> checkNumber(String phone) async => CheckResult.fromJson(
    await _send('POST', '/check-number', data: {'phone': phone}),
  );

  Future<void> report(Map<String, dynamic> payload) =>
      _send('POST', '/report', data: payload);

  Future<void> feedback(Map<String, dynamic> payload) =>
      _send('POST', '/feedback', data: payload);

  Future<SyncPage> sync({String? since, String? cursor}) async =>
      SyncPage.fromJson(
        await _send(
          'GET',
          '/sync',
          query: {'since': ?since, 'cursor': ?cursor},
        ),
      );

  Future<String> chat(List<ChatMessage> messages) async {
    final json = await _send(
      'POST',
      '/assistant/chat',
      data: {'messages': messages.map((m) => m.toJson()).toList()},
      receiveTimeout: const Duration(seconds: 40),
    );
    return json['reply'] as String;
  }

  Future<Map<String, dynamic>> _send(
    String method,
    String path, {
    Object? data,
    Map<String, dynamic>? query,
    bool authorized = true,
    bool retried = false,
    Duration? receiveTimeout,
  }) async {
    if (authorized && auth.token == null) await authenticate();
    try {
      final res = await _dio.request<dynamic>(
        path,
        data: data,
        queryParameters: query,
        options: Options(
          method: method,
          receiveTimeout: receiveTimeout,
          headers: {if (authorized) 'Authorization': 'Bearer ${auth.token}'},
        ),
      );
      final body = res.data;
      return body is Map<String, dynamic> ? body : <String, dynamic>{};
    } on DioException catch (e) {
      final res = e.response;
      if (res == null) throw ApiException(0, 'NETWORK', e.type.name);
      // Token expired or the server forgot the device: register again once.
      if (res.statusCode == 401 && authorized && !retried) {
        await auth.saveToken(null);
        return _send(
          method,
          path,
          data: data,
          query: query,
          retried: true,
          receiveTimeout: receiveTimeout,
        );
      }
      final err = res.data is Map ? (res.data as Map)['error'] : null;
      throw ApiException(
        res.statusCode ?? 0,
        err is Map ? '${err['code']}' : 'HTTP_${res.statusCode}',
        err is Map ? '${err['message']}' : (res.statusMessage ?? ''),
      );
    }
  }
}
