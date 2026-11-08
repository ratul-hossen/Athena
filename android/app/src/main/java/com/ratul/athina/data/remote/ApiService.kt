package com.ratul.athina.data.remote

import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

data class HealthResponse(
    val status: String,
    val companion: String,
    val current_state: StateResponse,
    val keypool_slots: Int
)

data class StateResponse(
    val mood: String,
    val energy: Float,
    val location: String,
    val relationship_warmth: Float
)

data class SessionDto(
    val id: String,
    val title: String,
    val channel: String,
    val created_at: String,
    val updated_at: String,
    val message_count: Int
)

data class TranscribeResponse(
    val text: String,
    val language: String?
)

interface ApiService {
    @GET("api/health")
    suspend fun getHealth(): HealthResponse

    @GET("api/sessions")
    suspend fun getSessions(): List<SessionDto>

    @Multipart
    @POST("api/voice/transcribe")
    suspend fun transcribeVoice(
        @Part file: MultipartBody.Part
    ): TranscribeResponse
}
