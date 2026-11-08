package com.ratul.athina.data.remote

sealed interface ChatStreamEvent {
    data class Token(val text: String) : ChatStreamEvent
    data class Provider(val provider: String, val model: String) : ChatStreamEvent
    data class ImageJob(val jobId: String, val prompt: String) : ChatStreamEvent
    data class Error(val message: String) : ChatStreamEvent
    data object Done : ChatStreamEvent
}
