import 'dart:io';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../l10n/app_localizations.dart';
import 'models.dart';

/// Local notifications for the two call scenarios:
///
/// 1. Known scammer (HIGH/MEDIUM in the on-device DB): a warning as soon as the number is checked,
///    then after the call a max-priority "tap if it was a scammer" with a red "!" on the right;
///    tapping it reports the number in one step.
/// 2. Any other number: nothing during the call; after it, "was it a scammer?" with an orange "!";
///    tapping it opens the report form with the number filled in.
class Notifications {
  Notifications(this._plugin);

  static const _chWarnings = 'call_warnings';
  static const _chReports = 'reports';
  static const _catScam = 'post_call_scam';
  static const _catUnknown = 'post_call_unknown';
  static const _actionScam = 'scam';
  static const _actionNo = 'no';

  final FlutterLocalNotificationsPlugin _plugin;

  /// On Android the call notifications are drawn natively (custom layout with the "!" button),
  /// the same code the call-screening service uses for real calls.
  static const _native = MethodChannel('safecall/native');
  static bool get _isAndroid => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  /// Set by the app to navigate when a notification is tapped.
  void Function(String location)? onOpen;

  /// Route to open if the app was launched by tapping a notification.
  String? launchLocation;

  static Future<Notifications> init(String languageCode) async {
    final n = Notifications(FlutterLocalNotificationsPlugin());
    final l = lookupAppLocalizations(Locale(languageCode));
    await n._plugin.initialize(
      settings: InitializationSettings(
        android: const AndroidInitializationSettings('@mipmap/ic_launcher'),
        // Permission is asked during onboarding, with an explanation, not at first launch.
        iOS: DarwinInitializationSettings(
          requestAlertPermission: false,
          requestSoundPermission: false,
          requestBadgePermission: false,
          // iOS shows these when the notification is pressed and held (at most 2 per category).
          notificationCategories: [
            DarwinNotificationCategory(
              _catScam,
              actions: [
                DarwinNotificationAction.plain(
                  _actionScam,
                  l.actionScam,
                  options: {
                    DarwinNotificationActionOption.destructive, // red
                    DarwinNotificationActionOption.foreground,
                  },
                ),
                DarwinNotificationAction.plain(_actionNo, l.no),
              ],
            ),
            DarwinNotificationCategory(
              _catUnknown,
              actions: [
                DarwinNotificationAction.plain(
                  _actionScam,
                  l.actionYesScam,
                  options: {DarwinNotificationActionOption.foreground},
                ),
                DarwinNotificationAction.plain(_actionNo, l.no),
              ],
            ),
          ],
        ),
      ),
      onDidReceiveNotificationResponse: n._onResponse,
    );
    await n._createAndroidChannels(l);
    final launch = await n._plugin.getNotificationAppLaunchDetails();
    if (launch?.didNotificationLaunchApp ?? false) {
      final response = launch!.notificationResponse;
      if (response != null) n.launchLocation = _locationFor(response);
    }
    return n;
  }

  Future<void> _createAndroidChannels(AppLocalizations l) async {
    final android = _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    if (android == null) return;
    await android.createNotificationChannel(
      AndroidNotificationChannel(
        _chWarnings,
        l.channelWarnings,
        importance: Importance.max,
        enableVibration: true,
      ),
    );
    await android.createNotificationChannel(
      AndroidNotificationChannel(
        _chReports,
        l.channelReports,
        importance: Importance.max,
      ),
    );
    await android.createNotificationChannel(
      AndroidNotificationChannel(
        'sync',
        l.channelSync,
        importance: Importance.low,
        playSound: false,
      ),
    );
  }

  Future<bool> requestPermission() async {
    if (kIsWeb) return false;
    final ios = _plugin
        .resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin
        >();
    if (ios != null) {
      return await ios.requestPermissions(
            alert: true,
            sound: true,
            badge: false,
          ) ??
          false;
    }
    final android = _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    if (android != null) {
      return await android.requestNotificationsPermission() ?? false;
    }
    return false;
  }

  /// Scenario 1, during the call: shown as soon as the number matched a known scammer.
  Future<void> showScamWarning({
    required int eventId,
    required String phone,
    required String languageCode,
  }) async {
    if (_isAndroid) {
      await _native.invokeMethod<void>('showScamWarning', {
        'eventId': eventId,
        'phone': phone,
        'language': languageCode,
      });
      return;
    }
    final l = lookupAppLocalizations(Locale(languageCode));
    await _plugin.show(
      id: eventId * 2,
      title: l.notifScamTitle,
      body: phone,
      payload: '/history',
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _chWarnings,
          l.channelWarnings,
          importance: Importance.max,
          priority: Priority.max,
          category: AndroidNotificationCategory.call,
          largeIcon: await _icon(red: true),
        ),
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentBanner: true,
          presentList: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.timeSensitive,
          attachments: await _attachment(red: true),
        ),
      ),
    );
  }

  /// After the call ends. Scammer: one tap reports it. Other numbers: one tap opens the report form.
  Future<void> showPostCall({
    required int eventId,
    required String phone,
    required RiskLevel level,
    required String languageCode,
  }) async {
    if (_isAndroid) {
      await _native.invokeMethod<void>('showPostCall', {
        'eventId': eventId,
        'phone': phone,
        'level': level.value,
        'language': languageCode,
      });
      return;
    }
    final l = lookupAppLocalizations(Locale(languageCode));
    final scam = level.isWarning;
    await _plugin.show(
      id: eventId * 2 + 1,
      title: phone,
      body: scam ? l.postCallScamBody : l.postCallUnknownBody,
      payload: scam
          ? quickReportLocation(phone: phone, level: level, eventId: eventId)
          : reportLocation(
              phone: phone,
              level: level,
              eventId: eventId,
              suspicious: true,
            ),
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _chReports,
          l.channelReports,
          importance: Importance.max,
          priority: Priority.max,
          largeIcon: await _icon(red: scam),
          actions: [
            AndroidNotificationAction(
              _actionScam,
              scam ? l.actionScam : l.actionYesScam,
              showsUserInterface: true,
            ),
            AndroidNotificationAction(
              _actionNo,
              l.no,
              cancelNotification: true,
            ),
          ],
        ),
        iOS: DarwinNotificationDetails(
          categoryIdentifier: scam ? _catScam : _catUnknown,
          presentAlert: true,
          presentBanner: true,
          presentList: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.timeSensitive,
          attachments: await _attachment(red: scam),
        ),
      ),
    );
  }

  static String reportLocation({
    required String phone,
    required RiskLevel level,
    int? eventId,
    bool suspicious = false,
  }) => Uri(
    path: '/report',
    queryParameters: {
      'phone': phone,
      'level': level.value,
      if (eventId != null) 'event': '$eventId',
      if (suspicious) 'suspicious': '1',
    },
  ).toString();

  static String quickReportLocation({
    required String phone,
    required RiskLevel level,
    int? eventId,
  }) => Uri(
    path: '/quick-report',
    queryParameters: {
      'phone': phone,
      'level': level.value,
      if (eventId != null) 'event': '$eventId',
    },
  ).toString();

  // --- the red/orange "!" shown on the right of the notification

  static int _fileCounter = 0;

  /// Copies the bundled icon to a file: notifications can only show images from disk,
  /// and iOS moves attachment files into its own store, so each notification needs a fresh copy.
  Future<String?> _iconFile({required bool red}) async {
    try {
      final name = red ? 'alert_red.png' : 'alert_orange.png';
      final data = await rootBundle.load('assets/notifications/$name');
      final dir = await getTemporaryDirectory();
      final file = File(p.join(dir.path, '${_fileCounter++}_$name'));
      await file.writeAsBytes(data.buffer.asUint8List(), flush: true);
      return file.path;
    } catch (_) {
      return null; // the notification still works without the picture
    }
  }

  Future<List<DarwinNotificationAttachment>?> _attachment({
    required bool red,
  }) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.iOS) return null;
    final path = await _iconFile(red: red);
    return path == null ? null : [DarwinNotificationAttachment(path)];
  }

  Future<AndroidBitmap<Object>?> _icon({required bool red}) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return null;
    final path = await _iconFile(red: red);
    return path == null ? null : FilePathAndroidBitmap(path);
  }

  static String? _locationFor(NotificationResponse r) {
    if (r.actionId == _actionNo) return null; // "No" just dismisses
    final payload = r.payload;
    return (payload == null || payload.isEmpty) ? null : payload;
  }

  void _onResponse(NotificationResponse r) {
    final location = _locationFor(r);
    if (location != null) onOpen?.call(location);
  }
}
