package com.safecall.safecall

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat

/** "No" on the post-call notification: just close it, without opening the app. */
class NotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != NotificationHelper.ACTION_DISMISS) return
        val id = intent.getIntExtra(NotificationHelper.EXTRA_NOTIFICATION_ID, -1)
        if (id >= 0) NotificationManagerCompat.from(context).cancel(id)
    }
}
