package com.ratul.athina

import android.app.Application
import com.ratul.athina.worker.AthinaSyncWorker
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class AthinaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Schedule battery-optimized periodic state sync
        AthinaSyncWorker.schedule(this)
    }
}
