package com.safecall.safecall

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager

/**
 * Follows the call screened just before: answered → the warning card shrinks to a reminder;
 * ended (IDLE) → the card goes away and the post-call question appears.
 * Needs READ_PHONE_STATE; the number itself comes from the screening service, not from here.
 */
class CallStateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return
        val store = CallStore(context)
        when (intent.getStringExtra(TelephonyManager.EXTRA_STATE)) {
            TelephonyManager.EXTRA_STATE_RINGING -> {
                // Screening runs just before the phone rings. A call SafeCall did not screen (a number
                // in the contacts) must not inherit an older call's post-call question.
                store.dropStalePending(maxAgeMs = 30_000)
                return
            }
            TelephonyManager.EXTRA_STATE_OFFHOOK -> {
                CallAlertOverlay.showTalking(context, store.languageCode)
                store.peekPending()?.let { NotificationHelper(context).cancelScamWarning(it.eventId) }
                return
            }
            TelephonyManager.EXTRA_STATE_IDLE -> CallAlertOverlay.hide()
            else -> return
        }

        val call = store.takePending() ?: return
        if (!store.notificationsEnabled) return
        NotificationHelper(context).showPostCall(call.eventId, call.phone, call.level, store.languageCode)
    }
}
