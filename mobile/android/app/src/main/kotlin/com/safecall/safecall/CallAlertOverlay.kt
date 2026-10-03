package com.safecall.safecall

import android.content.Context
import android.app.KeyguardManager
import android.graphics.PixelFormat
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Warning card drawn over the incoming-call screen when a known scammer calls.
 *
 * A notification cannot be relied on here: while the phone rings Android (and skins like MIUI)
 * keeps its own call banner/screen on top and our heads-up only lands in the shade. An overlay
 * window ("display over other apps") is shown on every skin. Fully on-device: no network.
 *
 * Ringing: big card in the middle (answer/decline buttons stay free at the top/bottom).
 * Talking: a slim reminder at the top. Call ended: removed.
 */
object CallAlertOverlay {
    private val main = Handler(Looper.getMainLooper())
    private var view: View? = null

    /** A scam call is in progress and the user has not dismissed the warning. */
    private var warningActive = false
    private val autoHide: Runnable = Runnable { hide() }

    fun canShow(context: Context) = Settings.canDrawOverlays(context)

    /** Big card while the phone rings. */
    fun showRinging(context: Context, phone: String, campaignType: String?, lang: String) {
        main.post { ringing(context, phone, campaignType, lang) }
    }

    private fun ringing(context: Context, phone: String, campaignType: String?, lang: String) {
        val app = context.applicationContext
        warningActive = true
        // Overlay windows are not drawn above a secure lock screen (checked on Android 16):
        // there the card is a small activity allowed over the keyguard instead.
        if (isLockedOrOff(app)) {
            CallAlertActivity.start(app, phone, campaignType, lang)
            return
        }
        if (!canShow(app)) return
        val card = LayoutInflater.from(app).inflate(R.layout.overlay_call_alert, null)
        bindCard(card, phone, campaignType, lang) { hide() }
        attach(app, card, Gravity.CENTER, 0)
        // The dialer's call UI may open right after screening and cover the card: re-stack it on top.
        // Touches outside the overlay card reach the call screen's own buttons.
        for (delay in longArrayOf(1500, 3000)) {
            main.postDelayed({ restack(app) }, delay)
        }
    }

    private fun restack(context: Context) {
        val v = view ?: return
        if (!warningActive || v.parent == null && v.windowToken == null) return
        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val params = v.layoutParams as? WindowManager.LayoutParams ?: return
        try {
            wm.removeViewImmediate(v)
            wm.addView(v, params)
        } catch (_: Exception) {
        }
    }

    fun isLockedOrOff(context: Context): Boolean {
        val keyguard = context.getSystemService(KeyguardManager::class.java)
        val power = context.getSystemService(PowerManager::class.java)
        return keyguard.isKeyguardLocked || !power.isInteractive
    }

    /** Fills the warning card; shared by the overlay window and the lock-screen activity. */
    fun bindCard(card: View, phone: String, campaignType: String?, lang: String, onClose: () -> Unit) {
        val s = if (lang == "ro") RO else RU
        val inflater = LayoutInflater.from(card.context)
        card.findViewById<TextView>(R.id.overlay_title).text = s.title
        card.findViewById<TextView>(R.id.overlay_phone).text = phone
        s.scheme(campaignType)?.let {
            card.findViewById<TextView>(R.id.overlay_scheme).apply {
                text = it
                visibility = View.VISIBLE
            }
        }
        val tips = card.findViewById<LinearLayout>(R.id.overlay_tips)
        for ((icon, title, text) in s.tips) {
            val row = inflater.inflate(R.layout.overlay_tip_row, tips, false)
            row.findViewById<TextView>(R.id.tip_icon).text = icon
            row.findViewById<TextView>(R.id.tip_title).text = title
            row.findViewById<TextView>(R.id.tip_text).text = text
            tips.addView(row)
        }
        card.findViewById<View>(R.id.overlay_close).setOnClickListener { onClose() }
        card.findViewById<TextView>(R.id.overlay_advice).text = s.advice
    }

    /** The call was answered: shrink to a reminder so the in-call controls stay usable. */
    fun showTalking(context: Context, lang: String) {
        main.post { talking(context, lang) }
    }

    private fun talking(context: Context, lang: String) {
        val app = context.applicationContext
        // Answered: the big card has done its job; keep a slim reminder over the in-call screen.
        CallAlertActivity.dismiss()
        if (!warningActive || !canShow(app)) return // dismissed by the user, or not a scam call
        val s = if (lang == "ro") RO else RU
        val pill = LayoutInflater.from(app).inflate(R.layout.overlay_call_pill, null)
        pill.findViewById<TextView>(R.id.pill_text).text = s.pill
        pill.findViewById<View>(R.id.pill_close).setOnClickListener { hide() }
        val top = (48 * app.resources.displayMetrics.density).toInt() // below the status bar
        attach(app, pill, Gravity.TOP, top)
    }

    fun hide() {
        main.post { remove() }
    }

    private fun remove() {
        warningActive = false
        main.removeCallbacks(autoHide)
        CallAlertActivity.dismiss()
        val v = view ?: return
        view = null
        try {
            (v.context.getSystemService(Context.WINDOW_SERVICE) as WindowManager).removeView(v)
        } catch (_: Exception) {
            // Already gone (process restarted or window removed by the system).
        }
    }

    private fun attach(context: Context, newView: View, gravity: Int, y: Int) {
        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        view?.let { old -> try { wm.removeView(old) } catch (_: Exception) {} }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            // Never steal focus or touches outside the card: the call screen must stay usable.
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            this.gravity = gravity
            this.y = y
            windowAnimations = android.R.style.Animation_Dialog
        }
        try {
            wm.addView(newView, params)
            view = newView
            main.removeCallbacks(autoHide)
            main.postDelayed(autoHide, 10 * 60 * 1000L) // safety net if the end of the call is missed
        } catch (_: Exception) {
            view = null // permission revoked meanwhile: the notification still warns
        }
    }

    private class Strings(
        val title: String,
        val schemePrefix: String,
        val schemes: Map<String, String>,
        val tips: List<Triple<String, String, String>>,
        val advice: String,
        val pill: String,
    ) {
        fun scheme(type: String?) = type?.let { schemes[it] }?.let { "$schemePrefix $it" }
    }

    private val RU = Strings(
        title = "Осторожно, возможно мошенники",
        schemePrefix = "Обычно представляются:",
        schemes = mapOf(
            "BANK" to "банком",
            "POLICE" to "полицией",
            "DELIVERY" to "службой доставки",
            "RELATIVE" to "родственником",
            "INVESTMENT" to "инвестиционной компанией",
        ),
        tips = listOf(
            Triple("🔐", "Не сообщайте коды", "Из SMS, приложений или почты — никому и никогда"),
            Triple("⏳", "Не поддавайтесь давлению", "Мошенники торопят и пугают — это их главный приём"),
            Triple(
                "👮",
                "Не верьте «сотрудникам»",
                "Если представились полицией, банком или другой службой — это не повод доверять",
            ),
        ),
        advice = "Советуем завершить звонок",
        pill = "⚠️ Возможно мошенники — не сообщайте коды",
    )

    private val RO = Strings(
        title = "Atenție, posibil escroci",
        schemePrefix = "De obicei se prezintă ca:",
        schemes = mapOf(
            "BANK" to "bancă",
            "POLICE" to "poliție",
            "DELIVERY" to "serviciu de livrare",
            "RELATIVE" to "rudă",
            "INVESTMENT" to "companie de investiții",
        ),
        tips = listOf(
            Triple("🔐", "Nu comunicați coduri", "Din SMS, aplicații sau e-mail — nimănui, niciodată"),
            Triple("⏳", "Nu cedați presiunii", "Escrocii grăbesc și sperie — e trucul lor principal"),
            Triple(
                "👮",
                "Nu credeți „angajaților”",
                "Dacă se prezintă ca poliție, bancă sau alt serviciu — nu e un motiv de încredere",
            ),
        ),
        advice = "Vă recomandăm să închideți apelul",
        pill = "⚠️ Posibil escroci — nu comunicați coduri",
    )
}
