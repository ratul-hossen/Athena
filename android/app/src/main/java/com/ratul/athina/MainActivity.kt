package com.ratul.athina

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.ratul.athina.ui.chat.ChatScreen
import com.ratul.athina.ui.chat.ChatViewModel
import com.ratul.athina.ui.theme.AthinaTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val chatViewModel: ChatViewModel by viewModels()

    private val requestAudioPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            chatViewModel.startVoiceMode()
        }
    }

    private val requestCameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            chatViewModel.openFaceScanner()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AthinaTheme {
                ChatScreen(
                    viewModel = chatViewModel,
                    onRequestAudioPermission = {
                        when {
                            ContextCompat.checkSelfPermission(
                                this,
                                Manifest.permission.RECORD_AUDIO
                            ) == PackageManager.PERMISSION_GRANTED -> {
                                chatViewModel.startVoiceMode()
                            }
                            else -> {
                                requestAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            }
                        }
                    },
                    onRequestCameraPermission = {
                        when {
                            ContextCompat.checkSelfPermission(
                                this,
                                Manifest.permission.CAMERA
                            ) == PackageManager.PERMISSION_GRANTED -> {
                                chatViewModel.openFaceScanner()
                            }
                            else -> {
                                requestCameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                            }
                        }
                    }
                )
            }
        }
    }
}
