/// Best-effort E.164 for local lookups. The server (libphonenumber, DEFAULT_REGION=MD) stays the
/// source of truth; this only has to match the keys it ships in /sync for common inputs.
String normalizePhone(String raw, {String countryCode = '373'}) {
  final trimmed = raw.trim();
  var digits = trimmed.replaceAll(RegExp(r'\D'), '');
  if (digits.isEmpty) return '';
  if (trimmed.startsWith('+')) return '+$digits';
  if (digits.startsWith('00')) return '+${digits.substring(2)}';
  if (digits.startsWith(countryCode)) return '+$digits';
  // National format, e.g. 069123456 -> +37369123456.
  if (digits.startsWith('0')) digits = digits.substring(1);
  return '+$countryCode$digits';
}

/// Hides the middle of a number for lists and logs: +37369123456 -> +373 69 ••• 456.
String maskPhone(String phone) {
  final digits = phone.replaceAll(RegExp(r'\D'), '');
  if (digits.length < 7) return '•••';
  final tail = digits.substring(digits.length - 3);
  if (digits.startsWith('373') && digits.length == 11) {
    return '+373 ${digits.substring(3, 5)} ••• $tail';
  }
  return '+${digits.substring(0, digits.length > 9 ? 3 : 1)} ••• $tail';
}
