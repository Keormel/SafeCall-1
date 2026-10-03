package com.safecall.safecall

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager

/**
 * Detects the end of a call (state back to IDLE) and asks about the call screened just before.
 * Needs READ_PHONE_STATE; the number itself comes from the screening service, not from here.
 */
class CallStateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return
        if (intent.getStringExtra(TelephonyManager.EXTRA_STATE) != TelephonyManager.EXTRA_STATE_IDLE) return

        val store = CallStore(context)
        val call = store.takePending() ?: return
        if (!store.notificationsEnabled) return
        NotificationHelper(context).showPostCall(call.eventId, call.phone, call.level, store.languageCode)
    }
}
