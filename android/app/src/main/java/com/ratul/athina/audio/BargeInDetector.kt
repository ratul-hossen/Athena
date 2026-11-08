package com.ratul.athina.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BargeInDetector @Inject constructor() {

    private val sampleRate = 16000
    private val bufferSize = AudioRecord.getMinBufferSize(
        sampleRate,
        AudioFormat.CHANNEL_IN_MONO,
        AudioFormat.ENCODING_PCM_16BIT
    ).coerceAtLeast(2048)

    private var audioRecord: AudioRecord? = null
    @Volatile
    private var isWatching = false

    /**
     * Listens in the background while Athina speaks.
     * If user speech is detected above threshold, invokes onBargeIn callback.
     */
    @SuppressLint("MissingPermission")
    suspend fun watchForBargeIn(
        energyThresholdRms: Float = 1400f,
        speechWindowMs: Long = 180L,
        onBargeIn: () -> Unit
    ) = withContext(Dispatchers.IO) {
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                return@withContext
            }

            audioRecord?.startRecording()
            isWatching = true

            val buffer = ShortArray(bufferSize / 2)
            var speechDurationMs = 0L
            val loopIntervalMs = (buffer.size * 1000L) / sampleRate

            while (isWatching) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (read > 0) {
                    var sum = 0.0
                    for (i in 0 until read) {
                        sum += buffer[i] * buffer[i]
                    }
                    val rms = Math.sqrt(sum / read).toFloat()

                    if (rms > energyThresholdRms) {
                        speechDurationMs += loopIntervalMs
                        if (speechDurationMs >= speechWindowMs) {
                            // User spoke! Trigger barge-in immediately
                            stopWatching()
                            withContext(Dispatchers.Main) {
                                onBargeIn()
                            }
                            break
                        }
                    } else {
                        speechDurationMs = 0L
                    }
                }
            }
        } catch (e: Exception) {
            stopWatching()
        }
    }

    fun stopWatching() {
        isWatching = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {}
        audioRecord = null
    }
}
