package com.ratul.athina.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class VoiceRecorder @Inject constructor() {

    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat).coerceAtLeast(2048)

    private var audioRecord: AudioRecord? = null
    @Volatile
    private var isRecording = false

    @SuppressLint("MissingPermission")
    suspend fun recordSpeechUntilSilence(
        silenceThresholdRms: Float = 600f,
        silenceDurationMs: Long = 850L,
        maxDurationMs: Long = 15000L,
        onRmsUpdate: (Float) -> Unit = {}
    ): ByteArray? = withContext(Dispatchers.IO) {
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRate,
                channelConfig,
                audioFormat,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                return@withContext null
            }

            audioRecord?.startRecording()
            isRecording = true

            val pcmData = ByteArrayOutputStream()
            val buffer = ShortArray(bufferSize / 2)

            var speechStarted = false
            var silenceStartTime = 0L
            val startTime = System.currentTimeMillis()

            while (isRecording) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (read > 0) {
                    // Compute Root Mean Square (RMS) energy
                    var sum = 0.0
                    for (i in 0 until read) {
                        sum += buffer[i] * buffer[i]
                    }
                    val rms = Math.sqrt(sum / read).toFloat()
                    onRmsUpdate(rms)

                    // Write PCM bytes
                    for (i in 0 until read) {
                        val s = buffer[i].toInt()
                        pcmData.write(s and 0xFF)
                        pcmData.write((s shr 8) and 0xFF)
                    }

                    val now = System.currentTimeMillis()
                    if (rms > silenceThresholdRms) {
                        speechStarted = true
                        silenceStartTime = 0L
                    } else if (speechStarted) {
                        if (silenceStartTime == 0L) {
                            silenceStartTime = now
                        } else if (now - silenceStartTime > silenceDurationMs) {
                            // User paused speaking
                            break
                        }
                    }

                    // Max timeout guard
                    if (now - startTime > maxDurationMs) {
                        break
                    }
                }
            }

            stop()
            val rawPcm = pcmData.toByteArray()
            if (rawPcm.size > sampleRate * 2 * 0.4) { // At least 0.4s of audio
                return@withContext createWavFromPcm(rawPcm, sampleRate)
            }
            null
        } catch (e: Exception) {
            stop()
            null
        }
    }

    fun stop() {
        isRecording = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {}
        audioRecord = null
    }

    private fun createWavFromPcm(pcmData: ByteArray, sampleRate: Int): ByteArray {
        val totalAudioLen = pcmData.size.toLong()
        val totalDataLen = totalAudioLen + 36
        val channels = 1
        val byteRate = 16 * sampleRate * channels / 8

        val wavOut = ByteArrayOutputStream()
        val out = DataOutputStream(wavOut)

        // RIFF header
        out.writeBytes("RIFF")
        out.writeInt(Integer.reverseBytes(totalDataLen.toInt()))
        out.writeBytes("WAVE")
        out.writeBytes("fmt ")
        out.writeInt(Integer.reverseBytes(16)) // Subchunk1Size (16 for PCM)
        out.writeShort(java.lang.Short.reverseBytes(1.toShort()).toInt()) // AudioFormat (1 for PCM)
        out.writeShort(java.lang.Short.reverseBytes(channels.toShort()).toInt())
        out.writeInt(Integer.reverseBytes(sampleRate))
        out.writeInt(Integer.reverseBytes(byteRate))
        out.writeShort(java.lang.Short.reverseBytes((channels * 16 / 8).toShort()).toInt()) // BlockAlign
        out.writeShort(java.lang.Short.reverseBytes(16.toShort()).toInt()) // BitsPerSample
        out.writeBytes("data")
        out.writeInt(Integer.reverseBytes(totalAudioLen.toInt()))
        out.write(pcmData)

        return wavOut.toByteArray()
    }
}
