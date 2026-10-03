import CallKit
import Foundation

/// Labels incoming calls from SafeCall's on-device number list. Never blocks a call.
///
/// The app writes `callerid.txt` (one "<E.164 digits>\t<label>" per line, ascending) into the
/// shared App Group container after each sync and asks the system to reload this extension.
final class CallDirectoryHandler: CXCallDirectoryProvider {
  static let appGroup = "group.com.akula.safecall"
  static let fileName = "callerid.txt"

  override func beginRequest(with context: CXCallDirectoryExtensionContext) {
    context.delegate = self
    // The app always ships the full list, so an incremental reload starts from scratch.
    if context.isIncremental {
      context.removeAllIdentificationEntries()
    }
    if let url = FileManager.default
      .containerURL(forSecurityApplicationGroupIdentifier: Self.appGroup)?
      .appendingPathComponent(Self.fileName),
      let text = try? String(contentsOf: url, encoding: .utf8)
    {
      var last: Int64 = -1
      for line in text.split(separator: "\n") {
        let parts = line.split(separator: "\t", maxSplits: 1)
        // CallKit requires strictly ascending numbers.
        guard parts.count == 2, let number = Int64(parts[0]), number > last else { continue }
        context.addIdentificationEntry(withNextSequentialPhoneNumber: number, label: String(parts[1]))
        last = number
      }
    }
    context.completeRequest()
  }
}

extension CallDirectoryHandler: CXCallDirectoryExtensionContextDelegate {
  func requestFailed(for extensionContext: CXCallDirectoryExtensionContext, withError error: Error) {}
}
