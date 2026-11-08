package com.ratul.athina.domain.model

data class ChatMessage(
    val id: String,
    val sessionId: String,
    val role: MessageRole,
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val isStreaming: Boolean = false,
    val isImageLoading: Boolean = false,
    val imageUrl: String? = null,
    val providerInfo: String? = null,
    val feedback: Int? = null // 1 for thumbs up, -1 for thumbs down
)

enum class MessageRole {
    USER,
    ASSISTANT,
    SYSTEM
}

data class AthinaState(
    val mood: String = "calm",
    val location: String = "in her cozy study room",
    val energy: Float = 0.9f,
    val relationshipWarmth: Float = 1.0f
)
