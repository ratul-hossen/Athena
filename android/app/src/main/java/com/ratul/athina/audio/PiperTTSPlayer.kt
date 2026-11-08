package com.ratul.athina.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PiperTTSPlayer @Inject constructor(
    @ApplicationContext private val context: Context
) : TextToSpeech.OnInitListener {

    private var tts: TextToSpeech? = null
    private var isReady = false

    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking.asStateFlow()

    private var onSpeechFinishedCallback: (() -> Unit)? = null

    init {
        tts = TextToSpeech(context, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val langResult = tts?.setLanguage(Locale.US)
            if (langResult != TextToSpeech.LANG_MISSING_DATA && langResult != TextToSpeech.LANG_NOT_SUPPORTED) {
                isReady = true
                
                // Select highest quality neural female voice
                selectBestNeuralVoice()
                
                // Athina conversational default prosody
                tts?.setSpeechRate(1.02f)
                tts?.setPitch(1.08f) // Warm, feminine companion pitch
                setupProgressListener()
            }
        }
    }

    /**
     * Inspects available TTS voices to dynamically pick the highest quality
     * natural female neural voice (e.g., Google TTS neural female voices).
     */
    private fun selectBestNeuralVoice() {
        try {
            val voices = tts?.voices ?: return
            val englishVoices = voices.filter { 
                it.locale.language == Locale.ENGLISH.language && !it.isNetworkConnectionRequired 
            }

            // Priority 1: High quality female neural voices (e.g., sfg, tpf, female)
            val preferredVoice = englishVoices.firstOrNull { voice ->
                val name = voice.name.lowercase()
                (name.contains("female") || name.contains("sfg") || name.contains("tpf") || name.contains("en-us-x-")) &&
                (voice.quality >= Voice.QUALITY_HIGH)
            } ?: englishVoices.firstOrNull { voice ->
                voice.name.lowercase().contains("female")
            } ?: englishVoices.firstOrNull { voice ->
                voice.quality >= Voice.QUALITY_HIGH
            }

            if (preferredVoice != null) {
                tts?.voice = preferredVoice
            }
        } catch (_: Exception) {
            // Graceful fallback to default engine voice
        }
    }

    private fun setupProgressListener() {
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                _isSpeaking.value = true
            }

            override fun onDone(utteranceId: String?) {
                _isSpeaking.value = false
                onSpeechFinishedCallback?.invoke()
            }

            override fun onError(utteranceId: String?) {
                _isSpeaking.value = false
            }
        })
    }

    /**
     * Adjusts pitch and speech rate dynamically based on Athina's emotional state.
     */
    fun setEmotionalTone(warmth: Float = 1.0f, humor: Float = 0.5f, energy: Float = 1.0f) {
        if (!isReady) return
        
        val basePitch = 1.08f
        val baseRate = 1.02f
        
        // Gentle/Sad/Comforting tone: slightly slower, warm pitch
        val targetPitch = when {
            humor > 0.7f -> basePitch + 0.04f  // Playful/Witty
            warmth > 0.9f && energy < 0.6f -> basePitch - 0.03f  // Gentle/Soft
            else -> basePitch
        }
        
        val targetRate = when {
            energy > 1.2f -> baseRate + 0.05f
            energy < 0.7f -> baseRate - 0.04f
            else -> baseRate
        }
        
        tts?.setPitch(targetPitch.coerceIn(0.95f, 1.25f))
        tts?.setSpeechRate(targetRate.coerceIn(0.90f, 1.20f))
    }

    /**
     * Sanitizes Markdown tokens and formats natural conversational pauses for speech.
     */
    fun sanitizeForSpeech(rawText: String): String {
        return rawText
            // Remove markdown code blocks and backticks
            .replace(Regex("```[\\s\\S]*?```"), "")
            .replace(Regex("`[^`]*`"), "")
            // Remove markdown bold, italic, headers
            .replace(Regex("[#*_~]"), "")
            // Convert dashes and semicolons to natural pause commas
            .replace("—", ", ")
            .replace(";", ", ")
            // Clean emojis for clean TTS pronunciation
            .replace(Regex("[\\p{So}\\p{Cn}]"), "")
            // Normalize spaces
            .replace(Regex("\\s+"), " ")
            .trim()
    }

    fun speakSentence(text: String, onFinished: (() -> Unit)? = null) {
        if (!isReady || text.isBlank()) return
        val cleanSpeechText = sanitizeForSpeech(text)
        if (cleanSpeechText.isBlank()) return
        
        onSpeechFinishedCallback = onFinished
        val utteranceId = UUID.randomUUID().toString()
        _isSpeaking.value = true
        tts?.speak(cleanSpeechText, TextToSpeech.QUEUE_ADD, null, utteranceId)
    }

    fun stop() {
        tts?.stop()
        _isSpeaking.value = false
        onSpeechFinishedCallback = null
    }

    fun release() {
        stop()
        tts?.shutdown()
        tts = null
    }
}
