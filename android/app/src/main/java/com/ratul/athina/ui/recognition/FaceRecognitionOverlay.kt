package com.ratul.athina.ui.recognition

import android.graphics.Bitmap
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.view.LifecycleCameraController
import androidx.camera.view.PreviewView
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.ratul.athina.ml.FaceRecognitionManager
import com.ratul.athina.ml.FaceRecognitionState
import com.ratul.athina.ui.theme.AthinaTheme
import kotlinx.coroutines.delay

@Composable
fun FaceRecognitionOverlay(
    recognitionManager: FaceRecognitionManager,
    onRatulRecognized: (String) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()
    val recognitionState by recognitionManager.recognitionState.collectAsState()

    var isEnrolling by remember { mutableStateOf(false) }
    val cameraController = remember {
        LifecycleCameraController(context).apply {
            cameraSelector = CameraSelector.DEFAULT_FRONT_CAMERA
        }
    }

    // Auto-dismiss on recognition success
    LaunchedEffect(recognitionState) {
        if (recognitionState is FaceRecognitionState.Recognized) {
            val name = (recognitionState as FaceRecognitionState.Recognized).userName
            delay(1200)
            onRatulRecognized(name)
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.96f))
    ) {
        // Close Button
        IconButton(
            onClick = onDismiss,
            modifier = Modifier
                .statusBarsPadding()
                .padding(top = 16.dp, end = 16.dp)
                .align(Alignment.TopEnd)
                .size(42.dp)
                .clip(CircleShape)
                .background(AthinaTheme.extended.surface2)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Close Scanner",
                tint = AthinaTheme.extended.muted,
                modifier = Modifier.size(20.dp)
            )
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
        ) {
            // Scanner Viewport
            val ringColor = when (recognitionState) {
                is FaceRecognitionState.Recognized -> Color(0xFF34D399) // Green
                is FaceRecognitionState.UnknownPerson -> Color(0xFFEF4444) // Red
                is FaceRecognitionState.NotEnrolled -> AthinaTheme.extended.muted
                else -> AthinaTheme.extended.accent
            }

            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(260.dp)
                    .clip(CircleShape)
                    .border(3.dp, ringColor, CircleShape)
            ) {
                // CameraX Front Camera Preview
                AndroidView(
                    factory = { ctx ->
                        PreviewView(ctx).apply {
                            controller = cameraController
                            cameraController.bindToLifecycle(lifecycleOwner)
                        }
                    },
                    modifier = Modifier.fillMaxSize()
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Status Headline & Description
            when (val state = recognitionState) {
                is FaceRecognitionState.Recognized -> {
                    Text(
                        text = "Welcome, ${state.userName}! ✨",
                        color = Color(0xFF34D399),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Athina recognized you locally. 100% on-device private biometrics.",
                        color = AthinaTheme.extended.muted,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center
                    )
                }
                is FaceRecognitionState.UnknownPerson -> {
                    Text(
                        text = "Face Not Recognized",
                        color = Color(0xFFEF4444),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Please face the camera directly in good lighting.",
                        color = AthinaTheme.extended.muted,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center
                    )
                }
                is FaceRecognitionState.NotEnrolled -> {
                    Text(
                        text = "Enroll Ratul's Face",
                        color = AthinaTheme.extended.accent,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Save your face vector on your phone so Athina greets you instantly.",
                        color = AthinaTheme.extended.muted,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            val preview = Bitmap.createBitmap(128, 128, Bitmap.Config.ARGB_8888)
                            coroutineScope.launch {
                                recognitionManager.enrollRatulFace(preview)
                            }
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = AthinaTheme.extended.accent,
                            contentColor = Color.Black
                        ),
                        shape = RoundedCornerShape(20.dp)
                    ) {
                        Icon(imageVector = Icons.Default.Face, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.size(8.dp))
                        Text(text = "Save Face Template", fontWeight = FontWeight.Bold)
                    }
                }
                else -> {
                    Text(
                        text = "Scanning for Ratul…",
                        color = MaterialTheme.colorScheme.onBackground,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Strictly local on-device verification. No biometrics uploaded.",
                        color = AthinaTheme.extended.muted,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}
