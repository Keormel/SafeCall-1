package com.safecall.safecall

import android.os.Build
import android.telecom.Call
import android.telecom.Connection
import android.telecom.TelecomManager
import android.util.Log

/** What the OS tells us about an incoming call before it rings (from the call parser prototype). */
data class CallEvent(
    /** Number as the network sent it, without URI parameters; null for hidden/withheld numbers. */
    val phone: String?,
    /** E.164 like the server stores it (region MD): the key looked up in the on-device DB. */
    val normalized: String?,
    val eventType: String,
    val timestamp: Long,
    val callState: String,
    /** STIR/SHAKEN result: PASSED, FAILED (likely spoofed) or NOT_VERIFIED (Android 11+). */
    val verification: String,
    val platform: String,
)

object IncomingCallParser {
    private const val TAG = "SafeCall"

    fun parse(details: Call.Details, normalize: (String) -> String): CallEvent {
        val phone = phoneOf(details)
        return CallEvent(
            phone = phone,
            normalized = phone?.let(normalize),
            eventType = if (details.callDirection == Call.Details.DIRECTION_INCOMING) "INCOMING" else "OUTGOING",
            timestamp = System.currentTimeMillis(),
            callState = "RINGING",
            verification = verificationOf(details),
            platform = "ANDROID",
        ).also { Log.i(TAG, "CALL_EVENT: $it") }
    }

    /**
     * `tel:` URIs may carry parameters ("+37360616690;phone-context=+373"): keep only the number,
     * otherwise the lookup key would not match the database.
     */
    private fun phoneOf(details: Call.Details): String? {
        if (details.handlePresentation != TelecomManager.PRESENTATION_ALLOWED) return null
        return details.handle
            ?.schemeSpecificPart
            ?.substringBefore(";")
            ?.trim()
            ?.takeIf { it.isNotEmpty() }
    }

    private fun verificationOf(details: Call.Details): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return "UNKNOWN"
        return when (details.callerNumberVerificationStatus) {
            Connection.VERIFICATION_STATUS_PASSED -> "PASSED"
            Connection.VERIFICATION_STATUS_FAILED -> "FAILED"
            else -> "NOT_VERIFIED"
        }
    }
}
