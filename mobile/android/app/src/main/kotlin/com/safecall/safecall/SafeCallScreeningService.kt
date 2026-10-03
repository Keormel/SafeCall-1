package com.safecall.safecall

import android.telecom.Call
import android.telecom.CallScreeningService

/**
 * Called by Android for every incoming call while SafeCall holds ROLE_CALL_SCREENING.
 * Checks the number in the on-device DB only (no network, well under a second), never blocks,
 * warns at once about known scammers and remembers the call for the post-call question.
 */
class SafeCallScreeningService : CallScreeningService() {
    override fun onScreenCall(details: Call.Details) {
        // Always let the call through: SafeCall only warns.
        respondToCall(details, CallResponse.Builder().build())

        if (details.callDirection != Call.Details.DIRECTION_INCOMING) return
        val raw = details.handle?.schemeSpecificPart ?: return

        val store = CallStore(this)
        val call = try {
            store.screen(raw)
        } catch (e: Exception) {
            // A broken or locked DB must never affect the call itself.
            ScreenedCall((System.currentTimeMillis() / 1000 % 100_000).toInt(), store.normalize(raw), Risk.UNKNOWN, System.currentTimeMillis())
        }
        store.savePending(call)

        if (store.notificationsEnabled && Risk.isWarning(call.level)) {
            NotificationHelper(this).showScamWarning(call.eventId, call.phone, store.languageCode)
        }
    }
}
