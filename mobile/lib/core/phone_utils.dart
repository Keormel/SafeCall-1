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
