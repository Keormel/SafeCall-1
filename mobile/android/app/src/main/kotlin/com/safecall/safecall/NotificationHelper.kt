package com.safecall.safecall

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/**
 * Native notifications for real calls (and the Android "simulate call" screen), so they work
 * even when the Flutter engine is not running.
 *
 * Scenario 1, known scammer: heads-up warning as soon as the number is screened, then after the
 * call "tap if it was a scammer" with a red "!" (large icon) that reports in one tap.
 * Scenario 2, any other number: after the call "was it a scammer?" with an orange "!" that opens
 * the report form with the number filled in.
 */
class NotificationHelper(private val context: Context) {
    companion object {
        // Same ids the Flutter side uses, so there is one set of channels in system settings.
        const val CH_WARNINGS = "call_warnings"
        const val CH_REPORTS = "reports"
        const val ACTION_DISMISS = "com.safecall.safecall.DISMISS"
        const val EXTRA_NOTIFICATION_ID = "notification_id"
        private val VIBRATION = longArrayOf(0, 400, 200, 400, 200, 600)
    }

    private val manager = NotificationManagerCompat.from(context)

    private fun strings(lang: String) = if (lang == "ro") RO else RU

    fun ensureChannels(lang: String) {
        val s = strings(lang)
        val nm = context.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CH_WARNINGS) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CH_WARNINGS, s.channelWarnings, NotificationManager.IMPORTANCE_HIGH).apply {
                    enableVibration(true)
                    vibrationPattern = VIBRATION
                    lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
                },
            )
        }
        if (nm.getNotificationChannel(CH_REPORTS) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CH_REPORTS, s.channelReports, NotificationManager.IMPORTANCE_HIGH).apply {
                    enableVibration(true)
                    lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
                },
            )
        }
    }

    /** Scenario 1, while the phone is ringing. */
    fun showScamWarning(eventId: Int, phone: String, lang: String) {
        val s = strings(lang)
        ensureChannels(lang)
        manager.cancelAll() // a new call: older SafeCall notifications are no longer relevant
        val notification = NotificationCompat.Builder(context, CH_WARNINGS)
            .setSmallIcon(R.drawable.ic_stat_safecall)
            .setLargeIcon(BitmapFactory.decodeResource(context.resources, R.drawable.alert_red))
            .setContentTitle(s.scamTitle)
            .setContentText(phone)
            .setStyle(NotificationCompat.BigTextStyle().bigText("$phone\n${s.scamHint}"))
            .setColor(Color.parseColor("#DC2626"))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setVibrate(VIBRATION)
            .setDefaults(NotificationCompat.DEFAULT_SOUND)
            .setOnlyAlertOnce(false)
            .setAutoCancel(true)
            .setTimeoutAfter(2 * 60 * 1000L)
            .setContentIntent(openApp("/history", eventId * 2))
            .build()
        notify(eventId * 2, notification)
    }

    /** After the call. Red "!" for known scammers (one-tap report), orange for everything else. */
    fun showPostCall(eventId: Int, phone: String, level: String, lang: String) {
        val s = strings(lang)
        ensureChannels(lang)
        // Only the latest call's question stays: older ones would be bundled by Android into a group
        // whose summary opens the app instead of the report.
        manager.cancelAll()
        val id = eventId * 2 + 1
        val scam = Risk.isWarning(level)
        val hint = if (scam) s.postCallScam else s.postCallUnknown
        val query = "phone=${Uri.encode(phone)}&level=$level&event=$eventId"
        val report = openApp(if (scam) "/quick-report?$query" else "/report?$query&suspicious=1", id)

        val shortHint = if (scam) s.postCallScamShort else s.postCallUnknownShort

        // Standard template on purpose: custom RemoteViews get as little as 48dp (Android 12+) and
        // MIUI clips them. The "!" is the large icon, which every skin draws on the right.
        val notification = NotificationCompat.Builder(context, CH_REPORTS)
            .setSmallIcon(R.drawable.ic_stat_safecall)
            .setLargeIcon(
                BitmapFactory.decodeResource(
                    context.resources,
                    if (scam) R.drawable.alert_red else R.drawable.alert_orange,
                ),
            )
            .setContentTitle(phone)
            .setContentText(shortHint)
            .setStyle(NotificationCompat.BigTextStyle().bigText(hint))
            .setColor(Color.parseColor(if (scam) "#DC2626" else "#F59E0B"))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setVibrate(VIBRATION)
            .setDefaults(NotificationCompat.DEFAULT_SOUND)
            .setAutoCancel(true)
            .setContentIntent(report)
            .addAction(0, if (scam) s.actionScam else s.actionYesScam, report)
            .addAction(0, s.no, dismiss(id))
            .build()
        notify(id, notification)
    }

    /** The call was answered: the reminder over the call screen replaces the in-call warning. */
    fun cancelScamWarning(eventId: Int) = manager.cancel(eventId * 2)

    /** Deep link into the Flutter router (handled by go_router via flutter_deeplinking_enabled). */
    private fun openApp(location: String, requestCode: Int): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse("safecall://open$location")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        return PendingIntent.getActivity(
            context, requestCode, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun dismiss(id: Int): PendingIntent {
        val intent = Intent(context, NotificationActionReceiver::class.java).apply {
            action = ACTION_DISMISS
            putExtra(EXTRA_NOTIFICATION_ID, id)
        }
        return PendingIntent.getBroadcast(
            context, id, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun notify(id: Int, notification: android.app.Notification) {
        try {
            manager.notify(id, notification)
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS not granted: nothing can be shown.
        }
    }

    private class Strings(
        val channelWarnings: String,
        val channelReports: String,
        val scamTitle: String,
        val scamHint: String,
        val postCallScam: String,
        val postCallUnknown: String,
        val postCallScamShort: String,
        val postCallUnknownShort: String,
        val actionScam: String,
        val actionYesScam: String,
        val no: String,
    )

    private val RU = Strings(
        channelWarnings = "Предупреждения о звонках",
        channelReports = "Вопросы после звонка",
        scamTitle = "Осторожно, возможно вам позвонил мошенник",
        scamHint = "Не называйте коды из SMS и данные карты, не переводите деньги",
        postCallScam = "Нажмите, если это был мошенник",
        postCallUnknown = "Был ли это мошенник? Нажмите, чтобы сообщить",
        postCallScamShort = "Нажмите, если мошенник",
        postCallUnknownShort = "Это был мошенник?",
        actionScam = "❗ Это мошенник",
        actionYesScam = "❗ Да, мошенник",
        no = "Нет",
    )

    private val RO = Strings(
        channelWarnings = "Avertismente despre apeluri",
        channelReports = "Întrebări după apel",
        scamTitle = "Atenție, posibil v-a sunat un escroc",
        scamHint = "Nu comunicați codurile din SMS și datele cardului, nu transferați bani",
        postCallScam = "Apăsați dacă a fost un escroc",
        postCallUnknown = "A fost un escroc? Apăsați pentru a raporta",
        postCallScamShort = "Apăsați dacă e escroc",
        postCallUnknownShort = "A fost un escroc?",
        actionScam = "❗ Este escroc",
        actionYesScam = "❗ Da, escroc",
        no = "Nu",
    )
}
