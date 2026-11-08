package com.ratul.athina.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SSEChatClient @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val baseUrl: String
) {
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    fun streamChat(sessionId: String, messageText: String): Flow<ChatStreamEvent> = flow {
        val payload = JSONObject().apply {
            put("session_id", sessionId)
            put("message", messageText)
            put("channel", "android")
        }

        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}/api/chat")
            .post(payload.toString().toRequestBody(jsonMediaType))
            .addHeader("Accept", "text/event-stream")
            .build()

        try {
            val response = okHttpClient.newCall(request).execute()
            if (!response.isSuccessful) {
                emit(ChatStreamEvent.Error("Server returned code ${response.code}"))
                return@flow
            }

            val body = response.body
            if (body == null) {
                emit(ChatStreamEvent.Error("Empty response body from server"))
                return@flow
            }

            val reader = BufferedReader(InputStreamReader(body.byteStream()))
            var line: String? = reader.readLine()

            while (line != null) {
                val trimmed = line.trim()
                if (trimmed.startsWith("data:")) {
                    val data = trimmed.removePrefix("data:").trim()
                    if (data == "[DONE]") {
                        emit(ChatStreamEvent.Done)
                        break
                    }

                    try {
                        val json = JSONObject(data)
                        val type = json.optString("type")
                        when (type) {
                            "token" -> {
                                val text = json.optString("text")
                                if (text.isNotEmpty()) emit(ChatStreamEvent.Token(text))
                            }
                            "provider" -> {
                                val provider = json.optString("provider")
                                val model = json.optString("model")
                                emit(ChatStreamEvent.Provider(provider, model))
                            }
                            "image_job" -> {
                                val jobId = json.optString("job_id")
                                val prompt = json.optString("prompt")
                                emit(ChatStreamEvent.ImageJob(jobId, prompt))
                            }
                            "error" -> {
                                val err = json.optString("error")
                                emit(ChatStreamEvent.Error(err))
                            }
                        }
                    } catch (e: Exception) {
                        // Skip non-json lines
                    }
                }
                line = reader.readLine()
            }
            emit(ChatStreamEvent.Done)
        } catch (e: Exception) {
            emit(ChatStreamEvent.Error(e.message ?: "Network error occurred"))
        }
    }.flowOn(Dispatchers.IO)
}
