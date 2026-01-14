package com.wickedzerg.mobilegcs.api

import com.google.gson.Gson
import com.wickedzerg.mobilegcs.models.GameState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class ApiClient {
    
    // TODO: Change this to your PC's IP address
    // Find your IP: ipconfig (Windows) or ifconfig (Linux/Mac)
    private val BASE_URL = "http://192.168.0.100:8000"
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .build()
    
    private val gson = Gson()
    
    suspend fun getGameState(): GameState = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$BASE_URL/api/game-state")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        
        val json = response.body?.string() ?: throw Exception("Empty response")
        gson.fromJson(json, GameState::class.java)
    }
    
    suspend fun getCombatStats(): Map<String, Any> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$BASE_URL/api/combat-stats")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        
        val json = response.body?.string() ?: throw Exception("Empty response")
        gson.fromJson(json, Map::class.java) as Map<String, Any>
    }
    
    suspend fun getLearningProgress(): Map<String, Any> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$BASE_URL/api/learning-progress")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        
        val json = response.body?.string() ?: throw Exception("Empty response")
        gson.fromJson(json, Map::class.java) as Map<String, Any>
    }
}
