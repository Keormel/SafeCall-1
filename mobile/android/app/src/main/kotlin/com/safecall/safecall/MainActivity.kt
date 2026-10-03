package com.safecall.safecall

import android.Manifest
import android.app.role.RoleManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.core.app.NotificationManagerCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/** `safecall/native` channel: call-screening role, permissions, native notifications. */
class MainActivity : FlutterActivity() {
    companion object {
        private const val REQUEST_ROLE = 41
        private const val REQUEST_PHONE_STATE = 42
        private const val REQUEST_OVERLAY = 43
    }

    private val roleManager by lazy { getSystemService(RoleManager::class.java) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        dismissNotificationFor(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        dismissNotificationFor(intent)
    }

    /**
     * Tapping the "!" inside the custom layout does not auto-cancel the notification like a normal
     * tap does, so close the post-call notification once its link (safecall://open/...?event=N) opens.
     */
    private fun dismissNotificationFor(intent: Intent?) {
        val event = intent?.data?.getQueryParameter("event")?.toIntOrNull() ?: return
        NotificationManagerCompat.from(this).cancel(event * 2 + 1)
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "safecall/native")
            .setMethodCallHandler { call, result -> handle(call, result) }
    }

    private fun handle(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "isProtectionEnabled" -> result.success(isScreeningRoleHeld())
            "requestProtection" -> {
                requestProtection()
                result.success(null)
            }
            "openRoleSettings" -> {
                startActivity(Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS))
                result.success(null)
            }
            "canDrawOverlays" -> result.success(CallAlertOverlay.canShow(this))
            "isXiaomi" -> result.success(isXiaomi)
            "openXiaomiPermissions" -> result.success(openXiaomiPermissions())
            "requestOverlay" -> {
                requestOverlay()
                result.success(null)
            }
            "getDatabasePath" -> result.success(getDatabasePath("safecall.db").absolutePath)
            "updateCallDirectory" -> result.success(null) // iOS only; Android reads the DB directly
            "showScamWarning" -> {
                val phone = call.argument<String>("phone")!!
                val lang = call.argument<String>("language") ?: "ru"
                val store = CallStore(this)
                CallAlertOverlay.showRinging(this, phone, store.campaignTypeOf(phone), lang)
                NotificationHelper(this).showScamWarning(
                    call.argument<Int>("eventId")!!,
                    call.argument<String>("phone")!!,
                    call.argument<String>("language") ?: "ru",
                )
                result.success(null)
            }
            "showPostCall" -> {
                CallAlertOverlay.hide()
                NotificationHelper(this).showPostCall(
                    call.argument<Int>("eventId")!!,
                    call.argument<String>("phone")!!,
                    call.argument<String>("level") ?: Risk.UNKNOWN,
                    call.argument<String>("language") ?: "ru",
                )
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    private fun isScreeningRoleHeld() =
        roleManager.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING) &&
            roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)

    /** Phone permissions, then the call-screening role, then "display over other apps". */
    private fun requestProtection() {
        // Phone state: notice when a call is answered or ends.
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_PHONE_STATE), REQUEST_PHONE_STATE)
        } else {
            requestScreeningRole()
        }
    }

    private fun requestScreeningRole() {
        if (isScreeningRoleHeld() || !roleManager.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            requestOverlay()
            return
        }
        @Suppress("DEPRECATION")
        startActivityForResult(roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING), REQUEST_ROLE)
    }

    /** "Display over other apps": lets the warning card appear over the incoming-call screen. */
    private fun requestOverlay() {
        if (CallAlertOverlay.canShow(this)) {
            openXiaomiPermissions()
            return
        }
        val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
        @Suppress("DEPRECATION")
        startActivityForResult(intent, REQUEST_OVERLAY)
    }

    private val isXiaomi get() = Build.MANUFACTURER.equals("Xiaomi", ignoreCase = true)

    /**
     * MIUI blocks pop-up windows, pop-ups from the background and the lock screen by its own
     * switches, which no permission dialog can ask for. Open SafeCall's MIUI permission page with
     * a hint; fall back to the app's system settings.
     */
    private fun openXiaomiPermissions(): Boolean {
        if (!isXiaomi) return false
        val lang = CallStore(this).languageCode
        Toast.makeText(
            this,
            if (lang == "ro") {
                "Activați: ferestre pop-up, ferestre pop-up în fundal și ecranul de blocare"
            } else {
                "Включите: всплывающие окна, всплывающие окна в фоне и экран блокировки"
            },
            Toast.LENGTH_LONG,
        ).show()
        val miui = Intent("miui.intent.action.APP_PERM_EDITOR").apply {
            setClassName("com.miui.securitycenter", "com.miui.permcenter.permissions.PermissionsEditorActivity")
            putExtra("extra_pkgname", packageName)
        }
        return try {
            startActivity(miui)
            true
        } catch (_: Exception) {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            true
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        // Setup chain: phone permissions → caller-ID role → overlay → (Xiaomi) MIUI permissions.
        when (requestCode) {
            REQUEST_ROLE -> requestOverlay()
            REQUEST_OVERLAY -> openXiaomiPermissions()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        // Ask for the role even if phone state was denied: warnings during the call still work.
        if (requestCode == REQUEST_PHONE_STATE) requestScreeningRole()
    }
}
