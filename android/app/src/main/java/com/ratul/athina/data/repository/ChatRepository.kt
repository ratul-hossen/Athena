package com.ratul.athina.data.repository

import com.ratul.athina.data.local.MessageDao
import com.ratul.athina.data.local.MessageEntity
import com.ratul.athina.data.remote.ApiService
import com.ratul.athina.data.remote.ChatStreamEvent
import com.ratul.athina.data.remote.SSEChatClient
import com.ratul.athina.domain.model.AthinaState
import com.ratul.athina.domain.model.ChatMessage
import com.ratul.athina.domain.model.MessageRole
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val messageDao: MessageDao,
    private val sseClient: SSEChatClient,
    private val apiService: ApiService
) {
    fun getMessages(sessionId: String): Flow<List<ChatMessage>> {
        return messageDao.getMessagesForSession(sessionId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    suspend fun saveUserMessage(sessionId: String, text: String): String {
        val userMsgId = UUID.randomUUID().toString()
        val userEntity = MessageEntity(
            id = userMsgId,
            sessionId = sessionId,
            role = "user",
            content = text,
            timestamp = System.currentTimeMillis()
        )
        messageDao.insertMessage(userEntity)
        return userMsgId
    }

    suspend fun saveAssistantMessage(
        messageId: String,
        sessionId: String,
        content: String,
        providerInfo: String? = null,
        imageUrl: String? = null
    ) {
        val entity = MessageEntity(
            id = messageId,
            sessionId = sessionId,
            role = "assistant",
            content = content,
            timestamp = System.currentTimeMillis(),
            providerInfo = providerInfo,
            imageUrl = imageUrl
        )
        messageDao.insertMessage(entity)
    }

    fun streamAssistantResponse(sessionId: String, messageText: String): Flow<ChatStreamEvent> {
        return sseClient.streamChat(sessionId, messageText)
    }

    suspend fun updateFeedback(messageId: String, feedback: Int) {
        messageDao.updateFeedback(messageId, feedback)
    }

    suspend fun transcribeAudio(wavBytes: ByteArray): String? {
        return try {
            val body = wavBytes.toRequestBody("audio/wav".toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", "speech.wav", body)
            val res = apiService.transcribeVoice(part)
            res.text.trim()
        } catch (e: Exception) {
            null
        }
    }

    suspend fun getAthinaState(): AthinaState? {
        return try {
            val response = apiService.getHealth()
            val state = response.current_state
            AthinaState(
                mood = state.mood,
                location = state.location,
                energy = state.energy,
                relationshipWarmth = state.relationship_warmth
            )
        } catch (e: Exception) {
            null
        }
    }
}
