import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../models.dart';

/// The single on-device SQLite file. The schema of `numbers` and `call_events` is shared with
/// the native call-screening code, which reads numbers and writes events without Flutter running.
class AppDatabase {
  AppDatabase._(this._db);

  static const fileName = 'safecall.db';
  static const _version = 1;

  final Database _db;

  static Future<AppDatabase> open() async {
    final path = p.join(await getDatabasesPath(), fileName);
    final db = await openDatabase(
      path,
      version: _version,
      // WAL lets the native reader and the Flutter writer work at the same time.
      onConfigure: (db) => db.rawQuery('PRAGMA journal_mode=WAL'),
      onCreate: (db, _) async {
        final batch = db.batch()
          ..execute('''
            CREATE TABLE numbers (
              phone TEXT PRIMARY KEY,
              risk_level TEXT NOT NULL,
              risk_score INTEGER NOT NULL,
              campaign_type TEXT,
              updated_at TEXT
            )''')
          ..execute('''
            CREATE TABLE call_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              phone TEXT NOT NULL,
              level TEXT NOT NULL,
              ts INTEGER NOT NULL,
              reported INTEGER NOT NULL DEFAULT 0
            )''')
          ..execute('''
            CREATE TABLE outbox (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )''')
          ..execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)');
        await batch.commit(noResult: true);
      },
    );
    return AppDatabase._(db);
  }

  // --- numbers

  Future<SyncItem?> lookup(String phone) async {
    final rows = await _db.query(
      'numbers',
      where: 'phone = ?',
      whereArgs: [phone],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    final r = rows.first;
    return SyncItem(
      phone: r['phone']! as String,
      riskLevel: RiskLevel.parse(r['risk_level'] as String?),
      riskScore: r['risk_score'] as int? ?? 0,
      campaignType: r['campaign_type'] as String?,
      updatedAt: r['updated_at'] as String? ?? '',
      removed: false,
    );
  }

  /// Numbers worth labeling on an incoming call, in the order CallKit requires (ascending).
  Future<List<({String phone, RiskLevel level})>> warningNumbers() async {
    final rows = await _db.query(
      'numbers',
      columns: ['phone', 'risk_level'],
      where: 'risk_level IN (?, ?)',
      whereArgs: [RiskLevel.high.value, RiskLevel.medium.value],
      orderBy: 'CAST(substr(phone, 2) AS INTEGER)',
    );
    return [
      for (final r in rows)
        (
          phone: r['phone']! as String,
          level: RiskLevel.parse(r['risk_level'] as String?),
        ),
    ];
  }

  Future<int> countNumbers() async =>
      Sqflite.firstIntValue(
        await _db.rawQuery('SELECT COUNT(*) FROM numbers'),
      ) ??
      0;

  /// Applies every page of one sync run atomically, together with the next `since`.
  Future<void> applySync(List<SyncPage> pages, String nextSince) async {
    await _db.transaction((txn) async {
      if (pages.isNotEmpty && pages.first.fullSnapshot) {
        await txn.delete('numbers');
      }
      final batch = txn.batch();
      for (final item in pages.expand((pg) => pg.items)) {
        if (item.removed) {
          batch.delete('numbers', where: 'phone = ?', whereArgs: [item.phone]);
        } else {
          batch.insert('numbers', {
            'phone': item.phone,
            'risk_level': item.riskLevel.value,
            'risk_score': item.riskScore,
            'campaign_type': item.campaignType,
            'updated_at': item.updatedAt,
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }
      batch.insert('meta', {
        'key': 'sync_since',
        'value': nextSince,
      }, conflictAlgorithm: ConflictAlgorithm.replace);
      batch.insert('meta', {
        'key': 'last_sync',
        'value': DateTime.now().toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
      await batch.commit(noResult: true);
    });
  }

  Future<void> clearNumbers() async {
    await _db.delete('numbers');
    await _db.delete(
      'meta',
      where: 'key IN (?, ?)',
      whereArgs: ['sync_since', 'last_sync'],
    );
  }

  Future<String?> getMeta(String key) async {
    final rows = await _db.query(
      'meta',
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    return rows.isEmpty ? null : rows.first['value'] as String?;
  }

  // --- call events

  Future<int> insertCallEvent(String phone, RiskLevel level) =>
      _db.insert('call_events', {
        'phone': phone,
        'level': level.value,
        'ts': DateTime.now().millisecondsSinceEpoch,
      });

  Future<List<CallEvent>> callEvents({int? limit}) async {
    final rows = await _db.query(
      'call_events',
      orderBy: 'ts DESC',
      limit: limit,
    );
    return rows.map(CallEvent.fromRow).toList();
  }

  Future<void> markReported(int eventId) => _db.update(
    'call_events',
    {'reported': 1},
    where: 'id = ?',
    whereArgs: [eventId],
  );

  // --- outbox (reports/feedback waiting for the network)

  Future<void> enqueue(String kind, Map<String, dynamic> payload) =>
      _db.insert('outbox', {
        'kind': kind,
        'payload': jsonEncode(payload),
        'created_at': DateTime.now().millisecondsSinceEpoch,
      });

  Future<List<({int id, String kind, Map<String, dynamic> payload})>>
  outbox() async {
    final rows = await _db.query('outbox', orderBy: 'id');
    return [
      for (final r in rows)
        (
          id: r['id']! as int,
          kind: r['kind']! as String,
          payload: jsonDecode(r['payload']! as String) as Map<String, dynamic>,
        ),
    ];
  }

  Future<void> dequeue(int id) =>
      _db.delete('outbox', where: 'id = ?', whereArgs: [id]);
}
