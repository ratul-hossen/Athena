package com.ratul.athina.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ratul.athina.audio.BargeInDetector
import com.ratul.athina.audio.PiperTTSPlayer
import com.ratul.athina.audio.VoiceRecorder
import com.ratul.athina.data.remote.ChatStreamEvent
import com.ratul.athina.data.repository.ChatRepository
import com.ratul.athina.domain.model.AthinaState
import com.ratul.athina.domain.model.ChatMessage
import com.ratul.athina.domain.model.MessageRole
import com.ratul.athina.ml.FaceRecognitionManager
import com.ratul.athina.ui.components.AvatarState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false,
    val inputText: String = "",
    val athinaState: AthinaState? = null,
    val error: String? = null,
    val isVoiceModeActive: Boolean = false,
    val voiceAvatarState: AvatarState = AvatarState.IDLE,
    val interimUserSpeech: String = "",
    val assistantSpeechReply: String = "",
    val isRatulFaceRecognized: Boolean = false,
    val isFaceScannerOpen: Boolean = false
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val repository: ChatRepository,
    private val voiceRecorder: VoiceRecorder,
    private val piperTTSPlayer: PiperTTSPlayer,
    private val bargeInDetector: BargeInDetector,
    val faceRecognitionManager: FaceRecognitionManager
) : ViewModel() {

    private val sessionId: String = "session_main_ratul"

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var streamJob: Job? = null
    private var voiceCycleJob: Job? = null
    private var bargeInJob: Job? = null

    init {
        observeMessages()
        refreshAthinaState()
    }

    private fun observeMessages() {
        repository.getMessages(sessionId)
            .onEach { roomMessages ->
                // Keep streaming message if one is active
                _uiState.update { current ->
                    val combined = if (current.isStreaming) {
                        val withoutStreaming = roomMessages.filter { !it.isStreaming }
                        val activeStream = current.messages.find { it.isStreaming }
                        if (activeStream != null) withoutStreaming + activeStream else withoutStreaming
                    } else {
                        roomMessages
                    }
                    current.copy(messages = combined)
                }
            }
            .launchIn(viewModelScope)
    }

    fun onInputTextChanged(text: String) {
        _uiState.update { it.copy(inputText = text) }
    }

    fun sendMessage() {
        val text = _uiState.value.inputText.trim()
        if (text.isEmpty() || _uiState.value.isStreaming) return

        _uiState.update { it.copy(inputText = "", isStreaming = true, error = null) }

        viewModelScope.launch {
            // Save user message to Room
            repository.saveUserMessage(sessionId, text)

            // Setup temporary streaming assistant message
            val assistantMsgId = UUID.randomUUID().toString()
            val tempAssistantMsg = ChatMessage(
                id = assistantMsgId,
                sessionId = sessionId,
                role = MessageRole.ASSISTANT,
                content = "",
                isStreaming = true
            )

            _uiState.update { current ->
                current.copy(messages = current.messages + tempAssistantMsg)
            }

            var accumulatedText = ""
            var providerInfo: String? = null
            var imageRequested = false

            streamJob = launch {
                repository.streamAssistantResponse(sessionId, text).collect { event ->
                    when (event) {
                        is ChatStreamEvent.Token -> {
                            accumulatedText += event.text
                            updateStreamingMessage(assistantMsgId, accumulatedText, providerInfo, isImageLoading = imageRequested)
                        }
                        is ChatStreamEvent.Provider -> {
                            providerInfo = "${event.provider} • ${event.model}"
                            updateStreamingMessage(assistantMsgId, accumulatedText, providerInfo, isImageLoading = imageRequested)
                        }
                        is ChatStreamEvent.ImageJob -> {
                            imageRequested = true
                            updateStreamingMessage(assistantMsgId, accumulatedText, providerInfo, isImageLoading = true)
                        }
                        is ChatStreamEvent.Error -> {
                            _uiState.update { it.copy(error = event.message) }
                        }
                        ChatStreamEvent.Done -> {
                            // Handled at stream finish
                        }
                    }
                }

                // Stream ended: persist assistant message to Room
                repository.saveAssistantMessage(
                    messageId = assistantMsgId,
                    sessionId = sessionId,
                    content = accumulatedText,
                    providerInfo = providerInfo
                )
                _uiState.update { it.copy(isStreaming = false) }
                refreshAthinaState()
            }
        }
    }

    private fun updateStreamingMessage(
        msgId: String,
        content: String,
        providerInfo: String?,
        isImageLoading: Boolean
    ) {
        _uiState.update { current ->
            val updated = current.messages.map { msg ->
                if (msg.id == msgId) {
                    msg.copy(
                        content = content,
                        providerInfo = providerInfo,
                        isImageLoading = isImageLoading
                    )
                } else msg
            }
            current.copy(messages = updated)
        }
    }

    fun stopStreaming() {
        streamJob?.cancel()
        _uiState.update { it.copy(isStreaming = false) }
    }

    fun onFeedback(messageId: String, feedback: Int) {
        viewModelScope.launch {
            repository.updateFeedback(messageId, feedback)
        }
    }

    fun refreshAthinaState() {
        viewModelScope.launch {
            val state = repository.getAthinaState()
            if (state != null) {
                _uiState.update { it.copy(athinaState = state) }
            }
        }
    }

    // ==========================================
    // Conversational Voice Pipeline (Phase 8)
    // ==========================================

    fun startVoiceMode() {
        _uiState.update {
            it.copy(
                isVoiceModeActive = true,
                voiceAvatarState = AvatarState.LISTENING,
                interimUserSpeech = "",
                assistantSpeechReply = ""
            )
        }
        startListeningLoop()
    }

    fun stopVoiceMode() {
        voiceCycleJob?.cancel()
        bargeInJob?.cancel()
        voiceRecorder.stop()
        bargeInDetector.stopWatching()
        piperTTSPlayer.stop()
        _uiState.update {
            it.copy(
                isVoiceModeActive = false,
                voiceAvatarState = AvatarState.IDLE
            )
        }
    }

    fun onVoiceInterrupt() {
        piperTTSPlayer.stop()
        bargeInDetector.stopWatching()
        bargeInJob?.cancel()
        voiceCycleJob?.cancel()
        _uiState.update {
            it.copy(
                voiceAvatarState = AvatarState.LISTENING,
                assistantSpeechReply = ""
            )
        }
        startListeningLoop()
    }

    private fun startListeningLoop() {
        voiceCycleJob?.cancel()
        voiceCycleJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    voiceAvatarState = AvatarState.LISTENING,
                    interimUserSpeech = ""
                )
            }

            // 1. Record until user stops speaking (silence detected via VAD)
            val audioWav = voiceRecorder.recordSpeechUntilSilence()
            if (audioWav == null || !_uiState.value.isVoiceModeActive) {
                if (_uiState.value.isVoiceModeActive) {
                    // Re-listen if no speech detected
                    delay(300)
                    startListeningLoop()
                }
                return@launch
            }

            // 2. Transcribe using Groq Whisper Large-v3
            _uiState.update { it.copy(voiceAvatarState = AvatarState.THINKING) }
            val transcript = repository.transcribeAudio(audioWav)
            if (transcript.isNullOrBlank()) {
                if (_uiState.value.isVoiceModeActive) {
                    delay(300)
                    startListeningLoop()
                }
                return@launch
            }

            _uiState.update { it.copy(interimUserSpeech = transcript) }
            repository.saveUserMessage(sessionId, transcript)

            // 3. Stream Athina's reply & queue TTS sentences with barge-in detection
            val assistantMsgId = UUID.randomUUID().toString()
            var accumulatedText = ""
            var sentenceBuffer = StringBuilder()

            _uiState.update {
                it.copy(
                    voiceAvatarState = AvatarState.SPEAKING,
                    assistantSpeechReply = ""
                )
            }

            // Start background Barge-in watcher
            startBargeInWatcher()

            repository.streamAssistantResponse(sessionId, transcript).collect { event ->
                when (event) {
                    is ChatStreamEvent.Token -> {
                        accumulatedText += event.text
                        sentenceBuffer.append(event.text)
                        _uiState.update { it.copy(assistantSpeechReply = accumulatedText) }

                        // Check if a complete sentence has formed (. ? !)
                        val currentChunk = sentenceBuffer.toString()
                        val punctIndex = currentChunk.indexOfAny(charArrayOf('.', '?', '!', '\n'))
                        if (punctIndex != -1 && punctIndex < currentChunk.length - 1) {
                            val sentence = currentChunk.substring(0, punctIndex + 1).trim()
                            sentenceBuffer = StringBuilder(currentChunk.substring(punctIndex + 1))
                            if (sentence.isNotEmpty() && _uiState.value.isVoiceModeActive) {
                                piperTTSPlayer.speakSentence(sentence)
                            }
                        }
                    }
                    is ChatStreamEvent.Done -> {
                        val remainder = sentenceBuffer.toString().trim()
                        if (remainder.isNotEmpty() && _uiState.value.isVoiceModeActive) {
                            piperTTSPlayer.speakSentence(remainder)
                        }
                    }
                    else -> {}
                }
            }

            // Save completed assistant response to Room
            repository.saveAssistantMessage(
                messageId = assistantMsgId,
                sessionId = sessionId,
                content = accumulatedText,
                providerInfo = "Groq Whisper + Athina Brain"
            )

            // Wait for TTS playback to conclude before returning to listening
            while (piperTTSPlayer.isSpeaking.value && _uiState.value.isVoiceModeActive) {
                delay(150)
            }

            bargeInDetector.stopWatching()
            bargeInJob?.cancel()

            if (_uiState.value.isVoiceModeActive) {
                delay(500)
                startListeningLoop()
            }
        }
    }

    private fun startBargeInWatcher() {
        bargeInJob?.cancel()
        bargeInJob = viewModelScope.launch {
            bargeInDetector.watchForBargeIn(
                energyThresholdRms = 1400f,
                speechWindowMs = 200L,
                onBargeIn = {
                    onVoiceInterrupt()
                }
            )
        }
    }

    // ==========================================
    // On-Device Face Recognition (Phase 11)
    // ==========================================

    fun openFaceScanner() {
        _uiState.update { it.copy(isFaceScannerOpen = true) }
    }

    fun closeFaceScanner() {
        _uiState.update { it.copy(isFaceScannerOpen = false) }
    }

    fun onRatulFaceRecognized(userName: String) {
        _uiState.update {
            it.copy(
                isRatulFaceRecognized = true,
                isFaceScannerOpen = false
            )
        }

        viewModelScope.launch {
            val greeting = "Welcome back, $userName! ✨ It's so wonderful to see you in person. How are you feeling right now?"
            val msgId = UUID.randomUUID().toString()

            // Save assistant greeting message
            repository.saveAssistantMessage(
                messageId = msgId,
                sessionId = sessionId,
                content = greeting,
                providerInfo = "On-Device Visual Recognition"
            )

            // Speak greeting via offline Piper TTS
            piperTTSPlayer.speakSentence(greeting)
        }
    }

    override fun onCleared() {
        super.onCleared()
        stopVoiceMode()
        piperTTSPlayer.release()
    }
}
