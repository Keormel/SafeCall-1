package com.safecall.safecall

import android.Manifest
import android.app.role.RoleManager
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
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
            "getDatabasePath" -> result.success(getDatabasePath("safecall.db").absolutePath)
            "updateCallDirectory" -> result.success(null) // iOS only; Android reads the DB directly
            "showScamWarning" -> {
                NotificationHelper(this).showScamWarning(
                    call.argument<Int>("eventId")!!,
                    call.argument<String>("phone")!!,
                    call.argument<String>("language") ?: "ru",
                )
                result.success(null)
            }
            "showPostCall" -> {
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

    /** Phone-state permission (to notice the end of a call), then the call-screening role. */
    private fun requestProtection() {
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_PHONE_STATE), REQUEST_PHONE_STATE)
        } else {
            requestScreeningRole()
        }
    }

    private fun requestScreeningRole() {
        if (isScreeningRoleHeld() || !roleManager.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) return
        @Suppress("DEPRECATION")
        startActivityForResult(roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING), REQUEST_ROLE)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        // Ask for the role even if phone state was denied: warnings during the call still work.
        if (requestCode == REQUEST_PHONE_STATE) requestScreeningRole()
    }
}
