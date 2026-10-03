package com.safecall.safecall

import android.telecom.Call
import android.telecom.CallScreeningService

/**
 * Called by Android for every incoming call while SafeCall holds ROLE_CALL_SCREENING.
 * Parses the call, checks the number in the on-device DB only (no network, well under a second),
 * never blocks, warns at once about known scammers and remembers the call for the post-call question.
 */
class SafeCallScreeningService : CallScreeningService() {
    override fun onScreenCall(details: Call.Details) {
        // Always let the call through: SafeCall only warns. Spelled out so it stays that way.
        val response = CallResponse.Builder()
            .setDisallowCall(false)
            .setRejectCall(false)
            .setSilenceCall(false)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .build()
        respondToCall(details, response)

        if (details.callDirection != Call.Details.DIRECTION_INCOMING) return
        val store = CallStore(this)
        val event = IncomingCallParser.parse(details, store::normalize)
        val raw = event.phone ?: return // hidden number: nothing to look up or report

        val call = try {
            store.screen(raw)
        } catch (e: Exception) {
            // A broken or locked DB must never affect the call itself.
            ScreenedCall((System.currentTimeMillis() / 1000 % 100_000).toInt(), store.normalize(raw), Risk.UNKNOWN, System.currentTimeMillis())
        }
        store.savePending(call)

        if (store.notificationsEnabled && Risk.isWarning(call.level)) {
            // The card over the call screen is what the user actually sees while it rings;
            // the notification stays as a fallback (no overlay permission) and in the shade.
            CallAlertOverlay.showRinging(this, call.phone, call.campaignType, store.languageCode)
            NotificationHelper(this).showScamWarning(call.eventId, call.phone, store.languageCode)
        }
    }
}
