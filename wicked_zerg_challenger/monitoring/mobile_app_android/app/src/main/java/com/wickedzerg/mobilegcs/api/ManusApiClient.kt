package com.wickedzerg.mobilegcs.api

import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.wickedzerg.mobilegcs.models.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

class ManusApiClient {
    
    // Server URL configuration
    // For Android Emulator: use 10.0.2.2 (maps to host's localhost)
    // For Physical Device: use your PC's local IP address (e.g., 192.168.1.100)
    // To find your IP: ipconfig (Windows) or ifconfig (Linux/Mac)
    private val BASE_URL = "http://10.0.2.2:8000" // Emulator IP for Manus
    
    private val client: OkHttpClient
    private val TAG = "ManusApiClient"
    
    init {
        val logging = HttpLoggingInterceptor { message ->
            Log.d(TAG, message)
        }
        logging.setLevel(HttpLoggingInterceptor.Level.BODY)
        client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS) // Increased from 10 to 15 seconds
            .readTimeout(20, TimeUnit.SECONDS) // Increased from 10 to 20 seconds
            .writeTimeout(15, TimeUnit.SECONDS) // Added write timeout
            .retryOnConnectionFailure(true) // Enable automatic retry on connection failure
            .build()
    }
    
    private val gson = Gson()
    
    suspend fun getCurrentGameState(): GameState? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/game-state")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            val data = gson.fromJson(json, Map::class.java) as Map<*, *>
            
            val isRunning = data["is_running"] as? Boolean ?: false
            if (!isRunning) {
                return@withContext null
            }
            
            gson.fromJson(json, GameState::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get game state: ${e.message}", e)
            null
        }
    }
    
    suspend fun getBattleStats(): BattleStats? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/combat-stats")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, BattleStats::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get battle stats: ${e.message}", e)
            null
        }
    }
    
    suspend fun getRecentGames(limit: Int = 20): List<GameRecord> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/recent-games?limit=$limit")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext emptyList()
            }
            
            val json = response.body?.string() ?: return@withContext emptyList()
            val listType = object : TypeToken<List<GameRecord>>() {}.type
            gson.fromJson<List<GameRecord>>(json, listType) ?: emptyList()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get recent games: ${e.message}", e)
            emptyList()
        }
    }
    
    suspend fun getTrainingStats(): TrainingStats? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/learning-progress")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, TrainingStats::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get training stats: ${e.message}", e)
            null
        }
    }
    
    suspend fun getRecentEpisodes(limit: Int = 20): List<TrainingEpisode> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/recent-episodes?limit=$limit")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext emptyList()
            }
            
            val json = response.body?.string() ?: return@withContext emptyList()
            val listType = object : TypeToken<List<TrainingEpisode>>() {}.type
            gson.fromJson<List<TrainingEpisode>>(json, listType) ?: emptyList()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get recent episodes: ${e.message}", e)
            emptyList()
        }
    }
    
    suspend fun getActiveBotConfig(): BotConfig? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/bot-config/active")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, BotConfig::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get active bot config: ${e.message}", e)
            null
        }
    }
    
    suspend fun getAllBotConfigs(): List<BotConfig> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/bot-config/all")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext emptyList()
            }
            
            val json = response.body?.string() ?: return@withContext emptyList()
            val listType = object : TypeToken<List<BotConfig>>() {}.type
            gson.fromJson<List<BotConfig>>(json, listType) ?: emptyList()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get all bot configs: ${e.message}", e)
            emptyList()
        }
    }
    
    suspend fun getArenaStats(): ArenaStats? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/arena/stats")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, ArenaStats::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get Arena stats: ${e.message}", e)
            null
        }
    }
    
    suspend fun getArenaBotInfo(): ArenaBotInfo? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/arena/bot-info")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext null
            }
            
            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, ArenaBotInfo::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get Arena bot info: ${e.message}", e)
            null
        }
    }
    
    suspend fun getRecentArenaMatches(limit: Int = 20): List<ArenaMatch> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/arena/recent-matches?limit=$limit")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext emptyList()
            }
            
            val json = response.body?.string() ?: return@withContext emptyList()
            val listType = object : TypeToken<List<ArenaMatch>>() {}.type
            gson.fromJson<List<ArenaMatch>>(json, listType) ?: emptyList()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get recent Arena matches: ${e.message}", e)
            emptyList()
        }
    }
}
