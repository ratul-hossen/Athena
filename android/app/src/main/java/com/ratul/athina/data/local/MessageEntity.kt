package com.ratul.athina.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.ratul.athina.domain.model.ChatMessage
import com.ratul.athina.domain.model.MessageRole

@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey
    val id: String,
    val sessionId: String,
    val role: String,
    val content: String,
    val timestamp: Long,
    val imageUrl: String? = null,
    val providerInfo: String? = null,
    val feedback: Int? = null
) {
    fun toDomain(): ChatMessage {
        val messageRole = when (role.lowercase()) {
            "user" -> MessageRole.USER
            "assistant" -> MessageRole.ASSISTANT
            else -> MessageRole.SYSTEM
        }
        return ChatMessage(
            id = id,
            sessionId = sessionId,
            role = messageRole,
            content = content,
            timestamp = timestamp,
            isStreaming = false,
            isImageLoading = false,
            imageUrl = imageUrl,
            providerInfo = providerInfo,
            feedback = feedback
        )
    }

    companion object {
        fun fromDomain(domain: ChatMessage): MessageEntity {
            return MessageEntity(
                id = domain.id,
                sessionId = domain.sessionId,
                role = domain.role.name.lowercase(),
                content = domain.content,
                timestamp = domain.timestamp,
                imageUrl = domain.imageUrl,
                providerInfo = domain.providerInfo,
                feedback = domain.feedback
            )
        }
    }
}
