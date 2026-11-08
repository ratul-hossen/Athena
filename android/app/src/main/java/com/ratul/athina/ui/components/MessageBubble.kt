package com.ratul.athina.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ThumbDown
import androidx.compose.material.icons.filled.ThumbUp
import androidx.compose.material.icons.outlined.ThumbDown
import androidx.compose.material.icons.outlined.ThumbUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.ratul.athina.domain.model.ChatMessage
import com.ratul.athina.domain.model.MessageRole
import com.ratul.athina.ui.theme.AthinaTheme

@Composable
fun MessageBubble(
    message: ChatMessage,
    onFeedback: (Int) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val isUser = message.role == MessageRole.USER

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 6.dp),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top
    ) {
        if (!isUser) {
            AthinaAvatar(size = 30.dp, modifier = Modifier.padding(top = 4.dp))
            Spacer(modifier = Modifier.width(8.dp))
        }

        Column(
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
            modifier = Modifier.widthIn(max = 310.dp)
        ) {
            val bubbleShape = if (isUser) {
                RoundedCornerShape(18.dp, 18.dp, 4.dp, 18.dp)
            } else {
                RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp)
            }

            val bubbleBg = if (isUser) {
                AthinaTheme.extended.userBubble
            } else {
                AthinaTheme.extended.surface2
            }

            Box(
                modifier = Modifier
                    .clip(bubbleShape)
                    .background(bubbleBg)
                    .then(
                        if (!isUser) Modifier.border(0.5.dp, AthinaTheme.extended.border, bubbleShape)
                        else Modifier
                    )
                    .padding(horizontal = 14.dp, vertical = 10.dp)
            ) {
                if (message.content.isEmpty() && message.isStreaming) {
                    // Shimmer thinking indicator
                    ThinkingShimmer()
                } else {
                    Row(verticalAlignment = Alignment.Bottom) {
                        Text(
                            text = message.content,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurface,
                            lineHeight = 21.sp
                        )

                        // Pulsing cursor during active token streaming
                        if (message.isStreaming) {
                            StreamingCursor()
                        }
                    }
                }
            }

            // Image Card Preview if generated
            if (message.imageUrl != null) {
                Spacer(modifier = Modifier.height(8.dp))
                AsyncImage(
                    model = message.imageUrl,
                    contentDescription = "Athina photo",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .size(240.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .border(1.dp, AthinaTheme.extended.border, RoundedCornerShape(14.dp))
                )
            } else if (message.isImageLoading) {
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .size(width = 240.dp, height = 140.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(AthinaTheme.extended.surface3)
                        .border(1.dp, AthinaTheme.extended.border, RoundedCornerShape(14.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator(
                            color = AthinaTheme.extended.accent,
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Taking a selfie for you…",
                            color = AthinaTheme.extended.muted,
                            fontSize = 12.sp
                        )
                    }
                }
            }

            // Bottom metadata & feedback buttons for assistant messages
            if (!isUser && !message.isStreaming && message.content.isNotEmpty()) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(top = 2.dp, start = 4.dp)
                ) {
                    if (message.providerInfo != null) {
                        Text(
                            text = message.providerInfo,
                            color = AthinaTheme.extended.muted.copy(alpha = 0.6f),
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }

                    // Thumbs Up
                    IconButton(
                        onClick = { onFeedback(if (message.feedback == 1) 0 else 1) },
                        modifier = Modifier.size(24.dp)
                    ) {
                        Icon(
                            imageVector = if (message.feedback == 1) Icons.Filled.ThumbUp else Icons.Outlined.ThumbUp,
                            contentDescription = "Like",
                            tint = if (message.feedback == 1) AthinaTheme.extended.accent else AthinaTheme.extended.muted,
                            modifier = Modifier.size(13.dp)
                        )
                    }

                    // Thumbs Down
                    IconButton(
                        onClick = { onFeedback(if (message.feedback == -1) 0 else -1) },
                        modifier = Modifier.size(24.dp)
                    ) {
                        Icon(
                            imageVector = if (message.feedback == -1) Icons.Filled.ThumbDown else Icons.Outlined.ThumbDown,
                            contentDescription = "Dislike",
                            tint = if (message.feedback == -1) AthinaTheme.extended.danger else AthinaTheme.extended.muted,
                            modifier = Modifier.size(13.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ThinkingShimmer() {
    Row(verticalAlignment = Alignment.CenterVertically) {
        val transition = rememberInfiniteTransition(label = "thinking_shimmer")
        val alpha by transition.animateFloat(
            initialValue = 0.3f,
            targetValue = 0.9f,
            animationSpec = infiniteRepeatable(
                animation = tween(600, easing = LinearEasing),
                repeatMode = RepeatMode.Reverse
            ),
            label = "shimmer_alpha"
        )
        Text(
            text = "Thinking…",
            color = AthinaTheme.extended.muted.copy(alpha = alpha),
            style = MaterialTheme.typography.bodyLarge,
            fontFamily = FontFamily.Default
        )
    }
}

@Composable
private fun StreamingCursor() {
    val transition = rememberInfiniteTransition(label = "cursor_blink")
    val alpha by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(450, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "cursor_alpha"
    )
    Box(
        modifier = Modifier
            .padding(start = 3.dp, bottom = 3.dp)
            .size(width = 6.dp, height = 14.dp)
            .clip(RoundedCornerShape(1.dp))
            .background(AthinaTheme.extended.accent.copy(alpha = alpha))
    )
}
