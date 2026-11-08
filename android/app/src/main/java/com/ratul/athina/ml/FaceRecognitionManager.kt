package com.ratul.athina.ml

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.sqrt

sealed class FaceRecognitionState {
    object Idle : FaceRecognitionState()
    object NotEnrolled : FaceRecognitionState()
    data class Scanning(val facesDetected: Int) : FaceRecognitionState()
    data class Recognized(val userName: String, val confidence: Float) : FaceRecognitionState()
    object UnknownPerson : FaceRecognitionState()
}

@Singleton
class FaceRecognitionManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val embeddingDim = 128
    private val similarityThreshold = 0.70f
    private val templateFileName = "ratul_face_template.dat"

    private val _recognitionState = MutableStateFlow<FaceRecognitionState>(FaceRecognitionState.Idle)
    val recognitionState: StateFlow<FaceRecognitionState> = _recognitionState.asStateFlow()

    private var enrolledTemplate: FloatArray? = null

    init {
        loadEnrolledTemplate()
    }

    fun isRatulEnrolled(): Boolean = enrolledTemplate != null

    private fun loadEnrolledTemplate() {
        val file = File(context.filesDir, templateFileName)
        if (file.exists() && file.length() == (embeddingDim * 4).toLong()) {
            val bytes = file.readBytes()
            val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            val template = FloatArray(embeddingDim)
            for (i in 0 until embeddingDim) {
                template[i] = buffer.float
            }
            enrolledTemplate = template
            _recognitionState.value = FaceRecognitionState.Idle
        } else {
            enrolledTemplate = null
            _recognitionState.value = FaceRecognitionState.NotEnrolled
        }
    }

    /**
     * Enrolls Ratul's face strictly on device.
     * Computes on-device spatial feature embedding vector and saves to private sandboxed storage.
     */
    suspend fun enrollRatulFace(faceBitmap: Bitmap): Boolean = withContext(Dispatchers.Default) {
        try {
            val embedding = computeFaceEmbedding(faceBitmap)
            normalizeVector(embedding)

            val buffer = ByteBuffer.allocate(embeddingDim * 4).order(ByteOrder.LITTLE_ENDIAN)
            for (value in embedding) {
                buffer.putFloat(value)
            }

            val file = File(context.filesDir, templateFileName)
            file.writeBytes(buffer.array())

            enrolledTemplate = embedding
            _recognitionState.value = FaceRecognitionState.Recognized("Ratul", 1.0f)
            true
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Clears enrolled face data.
     */
    fun unenroll() {
        val file = File(context.filesDir, templateFileName)
        if (file.exists()) {
            file.delete()
        }
        enrolledTemplate = null
        _recognitionState.value = FaceRecognitionState.NotEnrolled
    }

    /**
     * Verifies live camera frame against enrolled template.
     * ZERO data sent off-device.
     */
    suspend fun verifyLiveFace(faceBitmap: Bitmap): Boolean = withContext(Dispatchers.Default) {
        val enrolled = enrolledTemplate
        if (enrolled == null) {
            _recognitionState.value = FaceRecognitionState.NotEnrolled
            return@withContext false
        }

        try {
            val liveEmbedding = computeFaceEmbedding(faceBitmap)
            normalizeVector(liveEmbedding)

            val similarity = computeCosineSimilarity(enrolled, liveEmbedding)
            if (similarity >= similarityThreshold) {
                _recognitionState.value = FaceRecognitionState.Recognized("Ratul", similarity)
                true
            } else {
                _recognitionState.value = FaceRecognitionState.UnknownPerson
                false
            }
        } catch (e: Exception) {
            _recognitionState.value = FaceRecognitionState.Idle
            false
        }
    }

    /**
     * Computes normalized spatial facial descriptor from pre-processed face crop.
     * Operates purely on-device using local spatial pixel statistics & gradient projections.
     */
    private fun computeFaceEmbedding(bitmap: Bitmap): FloatArray {
        val scaled = Bitmap.createScaledBitmap(bitmap, 64, 64, true)
        val embedding = FloatArray(embeddingDim)

        // Extract localized regional luminance and edge descriptors across 8x8 grid
        val blockSize = 8
        var featureIdx = 0

        for (gridY in 0 until 8) {
            for (gridX in 0 until 8) {
                var sum = 0f
                var count = 0
                for (by in 0 until blockSize) {
                    for (bx in 0 until blockSize) {
                        val px = scaled.getPixel(gridX * blockSize + bx, gridY * blockSize + by)
                        val lum = 0.299f * Color.red(px) + 0.587f * Color.green(px) + 0.114f * Color.blue(px)
                        sum += lum
                        count++
                    }
                }
                if (featureIdx < embeddingDim) {
                    embedding[featureIdx++] = sum / count
                }
            }
        }

        // Second pass: horizontal and vertical gradient differentials for facial features
        for (y in 0 until 8) {
            for (x in 0 until 8) {
                if (featureIdx < embeddingDim) {
                    val px1 = scaled.getPixel(x * blockSize + 2, y * blockSize + 2)
                    val px2 = scaled.getPixel(x * blockSize + 6, y * blockSize + 6)
                    val diff = (Color.red(px1) - Color.red(px2)).toFloat()
                    embedding[featureIdx++] = diff
                }
            }
        }

        return embedding
    }

    private fun normalizeVector(vec: FloatArray) {
        var sumSquares = 0f
        for (v in vec) {
            sumSquares += v * v
        }
        val norm = sqrt(sumSquares.toDouble()).toFloat()
        if (norm > 0f) {
            for (i in vec.indices) {
                vec[i] /= norm
            }
        }
    }

    private fun computeCosineSimilarity(v1: FloatArray, v2: FloatArray): Float {
        var dotProduct = 0f
        for (i in v1.indices) {
            dotProduct += v1[i] * v2[i]
        }
        return dotProduct.coerceIn(-1.0f, 1.0f)
    }
}
