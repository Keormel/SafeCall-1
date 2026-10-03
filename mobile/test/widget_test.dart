import 'package:flutter_test/flutter_test.dart';
import 'package:safecall/core/models.dart';
import 'package:safecall/core/phone_utils.dart';
import 'package:safecall/features/report/report_controller.dart';

void main() {
  group('normalizePhone', () {
    test(
      'keeps E.164',
      () => expect(normalizePhone('+373 69 123-456'), '+37369123456'),
    );
    test(
      'national MD format',
      () => expect(normalizePhone('069123456'), '+37369123456'),
    );
    test(
      '00 prefix',
      () => expect(normalizePhone('0037369123456'), '+37369123456'),
    );
    test(
      'country code without plus',
      () => expect(normalizePhone('37369123456'), '+37369123456'),
    );
    test('empty', () => expect(normalizePhone('  '), ''));
  });

  group('maskPhone', () {
    test(
      'Moldovan number',
      () => expect(maskPhone('+37369123456'), '+373 69 ••• 456'),
    );
    test(
      'other country',
      () => expect(maskPhone('+4915112345678'), '+491 ••• 678'),
    );
    test('too short', () => expect(maskPhone('+123'), '•••'));
  });

  group('ReportRequest.from', () {
    test('bank wins as category, rest become actions', () {
      final r = ReportRequest.from({
        ReportOption.bank,
        ReportOption.police,
        ReportOption.otp,
        ReportOption.card,
      });
      expect(r.category, ScamCategory.bank);
      expect(r.actions, {ScamAction.otp, ScamAction.cardData});
    });
    test(
      'police',
      () => expect(
        ReportRequest.from({ReportOption.police}).category,
        ScamCategory.police,
      ),
    );
    test('nothing checked is OTHER', () {
      final r = ReportRequest.from({});
      expect(r.category, ScamCategory.other);
      expect(r.actions, isEmpty);
    });
  });

  test('parses /sync page', () {
    final page = SyncPage.fromJson({
      'items': [
        {
          'phone': '+37369123456',
          'risk_level': 'HIGH',
          'risk_score': 90,
          'campaign_type': 'BANK',
          'updated_at': '2026-10-03T10:00:00Z',
          'removed': false,
        },
      ],
      'server_time': '2026-10-03T10:00:00Z',
      'full_snapshot': true,
      'next_cursor': null,
      'has_more': false,
    });
    expect(page.items.single.riskLevel, RiskLevel.high);
    expect(page.fullSnapshot, isTrue);
  });

  test('warning levels', () {
    expect(RiskLevel.high.isWarning, isTrue);
    expect(RiskLevel.medium.isWarning, isTrue);
    expect(RiskLevel.unknown.isWarning, isFalse);
    expect(RiskLevel.parse('WEIRD'), RiskLevel.unknown);
  });
}
