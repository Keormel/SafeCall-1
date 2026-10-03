package com.safecall.safecall

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.WindowManager
import java.lang.ref.WeakReference

/**
 * The scam-warning card for a locked phone or a dark screen, where overlay windows are not drawn.
 *
 * A small translucent activity allowed over the keyguard: it turns the screen on and sits in the
 * middle. The locked call screen below ignores touches while another activity is on top, so the
 * first touch outside the card closes it and the call's Answer/Decline work right away.
 * Also closed by its ✕, when the call is answered, or when it ends.
 */
class CallAlertActivity : Activity() {
    companion object {
        private const val EXTRA_PHONE = "phone"
        private const val EXTRA_SCHEME = "scheme"
        private const val EXTRA_LANG = "lang"
        private var current: WeakReference<CallAlertActivity>? = null
        private val main = Handler(Looper.getMainLooper())

        /** True while this call's card should be on screen (cleared by ✕, answer or hang-up). */
        private var active = false

        /**
         * Screening happens before the phone starts ringing, so the dialer's full-screen call UI
         * opens right after us and covers the card. Bring the card back on top once that UI is up.
         */
        fun start(context: Context, phone: String, campaignType: String?, lang: String) {
            active = true
            launch(context, phone, campaignType, lang)
            for (delay in longArrayOf(1500, 3000)) {
                main.postDelayed({ if (active) launch(context, phone, campaignType, lang) }, delay)
            }
        }

        private fun launch(context: Context, phone: String, campaignType: String?, lang: String) {
            val intent = Intent(context, CallAlertActivity::class.java).apply {
                addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or
                        Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or
                        Intent.FLAG_ACTIVITY_NO_ANIMATION,
                )
                putExtra(EXTRA_PHONE, phone)
                putExtra(EXTRA_SCHEME, campaignType)
                putExtra(EXTRA_LANG, lang)
            }
            try {
                // Allowed from the background because SafeCall holds "display over other apps".
                context.startActivity(intent)
            } catch (_: Exception) {
                // The OS refused (no permission): the heads-up notification still warns.
            }
        }

        fun dismiss() {
            active = false
            main.removeCallbacksAndMessages(null)
            current?.get()?.let { if (!it.isFinishing) it.finish() }
            current = null
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        window.apply {
            setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.WRAP_CONTENT)
            setGravity(Gravity.CENTER)
            // Touches outside the card go to the call screen; never take the keyboard focus.
            addFlags(
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                    WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH or
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON,
            )
            clearFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND)
        }
        val card = LayoutInflater.from(this).inflate(R.layout.overlay_call_alert, null)
        CallAlertOverlay.bindCard(
            card,
            intent.getStringExtra(EXTRA_PHONE) ?: "",
            intent.getStringExtra(EXTRA_SCHEME),
            intent.getStringExtra(EXTRA_LANG) ?: "ru",
        ) { CallAlertOverlay.hide() }
        setContentView(card)
        current = WeakReference(this)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.action == MotionEvent.ACTION_OUTSIDE) {
            dismiss() // the user reaches for the call buttons: get out of the way
            return true
        }
        return super.onTouchEvent(event)
    }

    override fun onDestroy() {
        if (current?.get() === this) current = null
        super.onDestroy()
    }
}
