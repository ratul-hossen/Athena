package com.ratul.athina.ui.components

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
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Face
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ratul.athina.domain.model.AthinaState
import com.ratul.athina.ui.theme.AthinaTheme

@Composable
fun FrostedTopBar(
    athinaState: AthinaState?,
    isThinking: Boolean = false,
    isRatulRecognized: Boolean = false,
    onFaceScanClick: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.92f))
            .border(width = 0.5.dp, color = AthinaTheme.extended.border)
            .statusBarsPadding()
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            // Eagle Mark Avatar
            AthinaAvatar(size = 40.dp, isThinking = isThinking)

            Spacer(modifier = Modifier.width(12.dp))

            // Title & Status text
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.Center
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "Athina",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    // Online indicator dot
                    Box(
                        modifier = Modifier
                            .size(7.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF34D399)) // Green dot
                    )
                }

                val statusText = if (isThinking) {
                    "Thinking…"
                } else if (athinaState != null) {
                    "${athinaState.mood.replaceFirstChar { it.uppercase() }} • ${athinaState.location}"
                } else {
                    "Active companion"
                }

                Text(
                    text = statusText,
                    style = MaterialTheme.typography.labelSmall,
                    color = AthinaTheme.extended.muted,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Face Recognition Trigger & Status
            IconButton(
                onClick = onFaceScanClick,
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(
                        if (isRatulRecognized) Color(0xFF34D399).copy(alpha = 0.15f)
                        else AthinaTheme.extended.surface2
                    )
                    .border(
                        0.5.dp,
                        if (isRatulRecognized) Color(0xFF34D399) else AthinaTheme.extended.border,
                        CircleShape
                    )
            ) {
                Icon(
                    imageVector = Icons.Default.Face,
                    contentDescription = "Face Recognition",
                    tint = if (isRatulRecognized) Color(0xFF34D399) else AthinaTheme.extended.muted,
                    modifier = Modifier.size(18.dp)
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            // Relationship warmth badge
            if (athinaState != null) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(AthinaTheme.extended.surface2)
                        .border(0.5.dp, AthinaTheme.extended.border, RoundedCornerShape(12.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "Warmth ${(athinaState.relationshipWarmth * 100).toInt()}%",
                        color = AthinaTheme.extended.accent,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}
