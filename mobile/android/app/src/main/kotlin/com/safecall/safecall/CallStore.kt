package com.safecall.safecall

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.google.i18n.phonenumbers.NumberParseException
import com.google.i18n.phonenumbers.PhoneNumberUtil

/** Risk levels as stored by the Flutter app in `numbers.risk_level`. */
object Risk {
    const val HIGH = "HIGH"
    const val MEDIUM = "MEDIUM"
    const val LOW = "LOW"
    const val UNKNOWN = "UNKNOWN"

    fun isWarning(level: String) = level == HIGH || level == MEDIUM
}

/** A call that was screened and is waiting for its end to ask "was it a scammer?". */
data class ScreenedCall(val eventId: Int, val phone: String, val level: String, val startedAt: Long)

/**
 * Native side of the shared on-device data, usable while the Flutter engine is not running:
 * reads `numbers` and writes `call_events` in the app's SQLite file, reads the app settings.
 */
class CallStore(private val context: Context) {
    private val phoneUtil = PhoneNumberUtil.getInstance()
    private val flutterPrefs = context.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
    private val nativePrefs = context.getSharedPreferences("safecall_native", Context.MODE_PRIVATE)

    /** Same file sqflite opens (`getDatabasesPath()/safecall.db`). */
    private val dbFile get() = context.getDatabasePath("safecall.db")

    val languageCode: String get() = flutterPrefs.getString("flutter.language", null) ?: "ru"
    val notificationsEnabled: Boolean get() = flutterPrefs.getBoolean("flutter.notifications", true)

    /** E.164 like the server (DEFAULT_REGION=MD), or the raw digits if libphonenumber cannot parse it. */
    fun normalize(raw: String): String = try {
        phoneUtil.format(phoneUtil.parse(raw, "MD"), PhoneNumberUtil.PhoneNumberFormat.E164)
    } catch (e: NumberParseException) {
        raw.filter { it.isDigit() || it == '+' }
    }

    /** Looks up the number and logs the call. Never touches the network; returns in milliseconds. */
    fun screen(rawPhone: String): ScreenedCall {
        val phone = normalize(rawPhone)
        var level = Risk.UNKNOWN
        var eventId = (System.currentTimeMillis() / 1000 % 100_000).toInt() // fallback id if no DB yet
        val file = dbFile
        if (file.exists()) {
            // WAL: Flutter may have the same file open for writing.
            SQLiteDatabase.openDatabase(
                file.path, null,
                SQLiteDatabase.OPEN_READWRITE or SQLiteDatabase.ENABLE_WRITE_AHEAD_LOGGING,
            ).use { db ->
                db.rawQuery("SELECT risk_level FROM numbers WHERE phone = ?", arrayOf(phone)).use { c ->
                    if (c.moveToFirst()) level = c.getString(0) ?: Risk.UNKNOWN
                }
                db.compileStatement("INSERT INTO call_events (phone, level, ts, reported) VALUES (?, ?, ?, 0)").use {
                    it.bindString(1, phone)
                    it.bindString(2, level)
                    it.bindLong(3, System.currentTimeMillis())
                    eventId = it.executeInsert().toInt()
                }
            }
        }
        return ScreenedCall(eventId, phone, level, System.currentTimeMillis())
    }

    fun savePending(call: ScreenedCall) {
        nativePrefs.edit()
            .putInt("event", call.eventId)
            .putString("phone", call.phone)
            .putString("level", call.level)
            .putLong("ts", call.startedAt)
            .apply()
    }

    /** The last screened call, once; stale entries (no end seen for hours) are dropped. */
    fun takePending(): ScreenedCall? {
        val phone = nativePrefs.getString("phone", null) ?: return null
        val call = ScreenedCall(
            nativePrefs.getInt("event", 0),
            phone,
            nativePrefs.getString("level", Risk.UNKNOWN) ?: Risk.UNKNOWN,
            nativePrefs.getLong("ts", 0),
        )
        nativePrefs.edit().clear().apply()
        return if (System.currentTimeMillis() - call.startedAt < 3 * 60 * 60 * 1000) call else null
    }
}
