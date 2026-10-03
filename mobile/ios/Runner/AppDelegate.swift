import CallKit
import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  /// Call Directory extension that labels numbers from the on-device DB (ios/CallDirectory).
  private var callDirectoryExtensionId: String {
    (Bundle.main.bundleIdentifier ?? "com.akula.safecall") + ".CallDirectory"
  }

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Lets flutter_local_notifications show banners while the app is in the foreground.
    UNUserNotificationCenter.current().delegate = self
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "SafeCallNative") else { return }
    let channel = FlutterMethodChannel(name: "safecall/native", binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { [weak self] call, result in
      self?.handle(call, result: result)
    }
  }

  private func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "isProtectionEnabled":
      CXCallDirectoryManager.sharedInstance.getEnabledStatusForExtension(
        withIdentifier: callDirectoryExtensionId
      ) { status, error in
        // No extension installed yet (error) counts as "off".
        DispatchQueue.main.async { result(error == nil && status == .enabled) }
      }
    case "requestProtection", "openRoleSettings":
      // iOS never lets an app enable itself: the user flips the switch in Settings.
      CXCallDirectoryManager.sharedInstance.openSettings { error in
        DispatchQueue.main.async {
          if error != nil, let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
          }
          result(nil)
        }
      }
    case "updateCallDirectory":
      // The whole caller-ID list as "<digits>\t<label>" lines, already sorted by the app.
      guard let text = (call.arguments as? [String: Any])?["lines"] as? String else {
        result(FlutterError(code: "BAD_ARGS", message: "lines missing", details: nil))
        return
      }
      guard let url = FileManager.default
        .containerURL(forSecurityApplicationGroupIdentifier: "group.com.akula.safecall")?
        .appendingPathComponent("callerid.txt")
      else {
        result(FlutterError(code: "NO_APP_GROUP", message: "App Group container unavailable", details: nil))
        return
      }
      do {
        try text.write(to: url, atomically: true, encoding: .utf8)
      } catch {
        result(FlutterError(code: "WRITE_FAILED", message: error.localizedDescription, details: nil))
        return
      }
      // Fails harmlessly while the user has not enabled SafeCall in Settings yet.
      CXCallDirectoryManager.sharedInstance.reloadExtension(withIdentifier: callDirectoryExtensionId) { error in
        DispatchQueue.main.async { result(error == nil) }
      }
    case "getDatabasePath":
      result(nil) // Flutter owns the DB path on iOS (sqflite's databases directory).
    default:
      result(FlutterMethodNotImplemented)
    }
  }
}
