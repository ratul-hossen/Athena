package com.ratul.athina.ui.voice

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ratul.athina.ui.components.AvatarState
import com.ratul.athina.ui.components.Eagle3DView
import com.ratul.athina.ui.theme.AthinaTheme

@Composable
fun VoiceOverlay(
    avatarState: AvatarState,
    interimUserText: String,
    assistantReplyText: String,
    onClose: () -> Unit,
    onInterrupt: () -> Unit,
    modifier: Modifier = Modifier
) {
    val canInterrupt = avatarState == AvatarState.SPEAKING || avatarState == AvatarState.THINKING

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.95f))
            .clickable(enabled = canInterrupt) { onInterrupt() }
    ) {
        // Exit button at top right
        IconButton(
            onClick = onClose,
            modifier = Modifier
                .statusBarsPadding()
                .padding(top = 16.dp, end = 16.dp)
                .align(Alignment.TopEnd)
                .size(42.dp)
                .clip(CircleShape)
                .background(AthinaTheme.extended.surface2)
                .border(0.5.dp, AthinaTheme.extended.border, CircleShape)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Close voice mode",
                tint = AthinaTheme.extended.muted,
                modifier = Modifier.size(20.dp)
            )
        }

        // Center Content: 3D Eagle + Status + Live Speech Captions
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
        ) {
            // Live Interactive 3D Eagle (Changes flapping/head according to state)
            Eagle3DView(
                state = avatarState,
                size = 220.dp
            )

            Spacer(modifier = Modifier.height(24.dp))

            // State Pill
            val (pillText, pillBg, pillColor) = when (avatarState) {
                AvatarState.LISTENING -> Triple(
                    "Listening… Go ahead, I'm right here",
                    Color(0xFF34D399).copy(alpha = 0.15f),
                    Color(0xFF34D399)
                )
                AvatarState.THINKING -> Triple(
                    "Thinking…",
                    AthinaTheme.extended.accent.copy(alpha = 0.15f),
                    AthinaTheme.extended.accent
                )
                AvatarState.SPEAKING -> Triple(
                    "Speaking (Talk or tap to interrupt)",
                    AthinaTheme.extended.accent.copy(alpha = 0.18f),
                    AthinaTheme.extended.accent
                )
                AvatarState.IDLE -> Triple(
                    "Ready",
                    AthinaTheme.extended.surface2,
                    AthinaTheme.extended.muted
                )
            }

            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(16.dp))
                    .background(pillBg)
                    .border(0.5.dp, pillColor.copy(alpha = 0.4f), RoundedCornerShape(16.dp))
                    .padding(horizontal = 14.dp, vertical = 6.dp)
            ) {
                Text(
                    text = pillText,
                    color = pillColor,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            // User speech prompt caption
            if (interimUserText.isNotEmpty()) {
                Text(
                    text = "“$interimUserText”",
                    color = AthinaTheme.extended.muted,
                    fontSize = 15.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
            }

            // Athina spoken words caption
            if (assistantReplyText.isNotEmpty()) {
                Text(
                    text = assistantReplyText,
                    color = MaterialTheme.colorScheme.onBackground,
                    style = MaterialTheme.typography.bodyLarge,
                    fontSize = 18.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Center,
                    fontWeight = FontWeight.Normal,
                    modifier = Modifier.fillMaxWidth(0.92f)
                )
            }
        }
    }
}
