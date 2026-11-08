package com.ratul.athina.ui.components

import android.annotation.SuppressLint
import android.graphics.Color
import android.view.ViewGroup
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver

enum class AvatarState(val value: String) {
    IDLE("idle"),
    LISTENING("listening"),
    THINKING("thinking"),
    SPEAKING("speaking")
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun Eagle3DView(
    state: AvatarState = AvatarState.IDLE,
    size: Dp = 160.dp,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var webViewInstance by remember { mutableStateOf<WebView?>(null) }
    var isLoaded by remember { mutableStateOf(false) }

    // Update avatar animation state whenever the parameter changes
    LaunchedEffect(state, isLoaded) {
        if (isLoaded) {
            webViewInstance?.evaluateJavascript("window.setAvatarState('${state.value}');", null)
        }
    }

    // Battery optimization: pause WebGL rendering when app is backgrounded or screen off
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_PAUSE, Lifecycle.Event.ON_STOP -> {
                    webViewInstance?.evaluateJavascript("window.pauseRendering();", null)
                }
                Lifecycle.Event.ON_RESUME -> {
                    webViewInstance?.evaluateJavascript("window.resumeRendering();", null)
                }
                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            webViewInstance?.destroy()
        }
    }

    Box(modifier = modifier.size(size)) {
        AndroidView(
            factory = { ctx ->
                WebView(ctx).apply {
                    layoutParams = ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    )
                    setBackgroundColor(Color.TRANSPARENT)
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.allowFileAccess = true

                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            super.onPageFinished(view, url)
                            isLoaded = true
                            view?.evaluateJavascript("window.setAvatarState('${state.value}');", null)
                        }
                    }

                    loadUrl("file:///android_asset/eagle/index.html")
                    webViewInstance = this
                }
            },
            modifier = Modifier.size(size)
        )
    }
}
