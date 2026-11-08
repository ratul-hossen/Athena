package com.ratul.athina.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

@Immutable
data class AthinaExtendedColors(
    val surface2: Color,
    val surface3: Color,
    val border: Color,
    val userBubble: Color,
    val muted: Color,
    val danger: Color,
    val accent: Color
)

val LocalAthinaExtendedColors = staticCompositionLocalOf {
    AthinaExtendedColors(
        surface2 = DarkSurface2,
        surface3 = DarkSurface3,
        border = DarkBorder,
        userBubble = DarkUserBubble,
        muted = DarkMuted,
        danger = DarkDanger,
        accent = DarkAccent
    )
}

private val DarkColorScheme = darkColorScheme(
    primary = DarkAccent,
    background = DarkBackground,
    surface = DarkSurface,
    onPrimary = Color.Black,
    onBackground = DarkText,
    onSurface = DarkText
)

private val LightColorScheme = lightColorScheme(
    primary = LightAccent,
    background = LightBackground,
    surface = LightSurface,
    onPrimary = Color.White,
    onBackground = LightText,
    onSurface = LightText
)

@Composable
fun AthinaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val extendedColors = if (darkTheme) {
        AthinaExtendedColors(
            surface2 = DarkSurface2,
            surface3 = DarkSurface3,
            border = DarkBorder,
            userBubble = DarkUserBubble,
            muted = DarkMuted,
            danger = DarkDanger,
            accent = DarkAccent
        )
    } else {
        AthinaExtendedColors(
            surface2 = LightSurface2,
            surface3 = LightSurface3,
            border = LightBorder,
            userBubble = LightUserBubble,
            muted = LightMuted,
            danger = LightDanger,
            accent = LightAccent
        )
    }

    CompositionLocalProvider(LocalAthinaExtendedColors provides extendedColors) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography,
            content = content
        )
    }
}

object AthinaTheme {
    val extended: AthinaExtendedColors
        @Composable
        get() = LocalAthinaExtendedColors.current
}
