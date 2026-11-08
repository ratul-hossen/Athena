package com.ratul.athina.ui.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ratul.athina.ui.components.AthinaAvatar
import com.ratul.athina.ui.components.ComposerBar
import com.ratul.athina.ui.components.FrostedTopBar
import com.ratul.athina.ui.components.MessageBubble
import com.ratul.athina.ui.recognition.FaceRecognitionOverlay
import com.ratul.athina.ui.theme.AthinaTheme
import com.ratul.athina.ui.voice.VoiceOverlay

@Composable
fun ChatScreen(
    viewModel: ChatViewModel,
    onRequestAudioPermission: () -> Unit = { viewModel.startVoiceMode() },
    onRequestCameraPermission: () -> Unit = { viewModel.openFaceScanner() },
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()

    // Auto-scroll to bottom on new token or message
    LaunchedEffect(uiState.messages.size, uiState.messages.lastOrNull()?.content?.length) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            FrostedTopBar(
                athinaState = uiState.athinaState,
                isThinking = uiState.isStreaming,
                isRatulRecognized = uiState.isRatulFaceRecognized,
                onFaceScanClick = onRequestCameraPermission
            )
        },
        bottomBar = {
            ComposerBar(
                inputText = uiState.inputText,
                onInputChange = viewModel::onInputTextChanged,
                onSend = viewModel::sendMessage,
                onStop = viewModel::stopStreaming,
                onMicClick = onRequestAudioPermission,
                isStreaming = uiState.isStreaming
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
        modifier = modifier.fillMaxSize()
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (uiState.messages.isEmpty()) {
                // Empty State: Mercy Greeting Card
                EmptyGreetingState(
                    onSuggestionClick = { suggestion ->
                        viewModel.onInputTextChanged(suggestion)
                        viewModel.sendMessage()
                    }
                )
            } else {
                LazyColumn(
                    state = listState,
                    contentPadding = PaddingValues(vertical = 12.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(
                        items = uiState.messages,
                        key = { it.id }
                    ) { message ->
                        AnimatedVisibility(
                            visible = true,
                            enter = fadeIn() + slideInVertically(initialOffsetY = { 20 })
                        ) {
                            MessageBubble(
                                message = message,
                                onFeedback = { feedback -> viewModel.onFeedback(message.id, feedback) }
                            )
                        }
                    }
                }
            }

            // Fullscreen Voice Mode Overlay (Phase 8 Conversational Voice)
            if (uiState.isVoiceModeActive) {
                VoiceOverlay(
                    avatarState = uiState.voiceAvatarState,
                    interimUserText = uiState.interimUserSpeech,
                    assistantReplyText = uiState.assistantSpeechReply,
                    onClose = viewModel::stopVoiceMode,
                    onInterrupt = viewModel::onVoiceInterrupt
                )
            }

            // On-Device Face Recognition Scanner (Phase 11)
            if (uiState.isFaceScannerOpen) {
                FaceRecognitionOverlay(
                    recognitionManager = viewModel.faceRecognitionManager,
                    onRatulRecognized = viewModel::onRatulFaceRecognized,
                    onDismiss = viewModel::closeFaceScanner
                )
            }
        }
    }
}

@Composable
private fun EmptyGreetingState(
    onSuggestionClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp)
    ) {
        // Procedural 3D Eagle Avatar
        com.ratul.athina.ui.components.Eagle3DView(
            size = 140.dp,
            state = com.ratul.athina.ui.components.AvatarState.IDLE
        )

        Spacer(modifier = Modifier.height(18.dp))

        Text(
            text = "Welcome, Ratul",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onBackground,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "Athina is here with you. What's on your mind today?",
            style = MaterialTheme.typography.bodyLarge,
            color = AthinaTheme.extended.muted,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(28.dp))

        // Quick Suggestion Chips
        val suggestions = listOf(
            "How are you feeling right now?",
            "What have you been up to today?",
            "Send me a selfie! 📸",
            "Tell me an interesting thought"
        )

        suggestions.forEach { chipText ->
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.85f)
                    .padding(vertical = 4.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(AthinaTheme.extended.surface2)
                    .border(0.5.dp, AthinaTheme.extended.border, RoundedCornerShape(14.dp))
                    .clickable { onSuggestionClick(chipText) }
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Text(
                    text = chipText,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontSize = 14.sp
                )
            }
        }
    }
}
