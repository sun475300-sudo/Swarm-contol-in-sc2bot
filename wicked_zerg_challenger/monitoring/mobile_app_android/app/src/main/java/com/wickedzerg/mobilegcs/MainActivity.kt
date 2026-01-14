package com.wickedzerg.mobilegcs

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.wickedzerg.mobilegcs.api.ApiClient
import com.wickedzerg.mobilegcs.models.GameState
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    
    private lateinit var mineralsText: TextView
    private lateinit var vespeneText: TextView
    private lateinit var supplyText: TextView
    private lateinit var unitsText: TextView
    private lateinit var winRateText: TextView
    private lateinit var statusText: TextView
    
    private val apiClient = ApiClient()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Initialize views
        mineralsText = findViewById(R.id.mineralsText)
        vespeneText = findViewById(R.id.vespeneText)
        supplyText = findViewById(R.id.supplyText)
        unitsText = findViewById(R.id.unitsText)
        winRateText = findViewById(R.id.winRateText)
        statusText = findViewById(R.id.statusText)
        
        // Start real-time updates
        startGameStateUpdates()
    }
    
    private fun startGameStateUpdates() {
        lifecycleScope.launch {
            while (true) {
                try {
                    val gameState = apiClient.getGameState()
                    updateUI(gameState)
                    statusText.text = "Connected"
                    statusText.setTextColor(getColor(R.color.green))
                } catch (e: Exception) {
                    statusText.text = "Disconnected: ${e.message}"
                    statusText.setTextColor(getColor(R.color.red))
                }
                delay(1000) // Update every 1 second
            }
        }
    }
    
    private fun updateUI(gameState: GameState) {
        mineralsText.text = "Minerals: ${gameState.minerals}"
        vespeneText.text = "Vespene: ${gameState.vespene}"
        supplyText.text = "Supply: ${gameState.supplyUsed}/${gameState.supplyCap}"
        
        val totalUnits = gameState.units.values.sum()
        unitsText.text = "Total Units: $totalUnits"
        
        val winRate = gameState.winRate
        winRateText.text = "Win Rate: ${String.format("%.1f", winRate)}%"
    }
}
