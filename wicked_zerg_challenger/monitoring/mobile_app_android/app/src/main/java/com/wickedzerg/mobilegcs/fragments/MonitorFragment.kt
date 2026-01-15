package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ApiClient
import com.wickedzerg.mobilegcs.models.GameState
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MonitorFragment : Fragment() {
    
    private lateinit var statusText: TextView
    private lateinit var gameStateContainer: ViewGroup
    private lateinit var noGameMessage: View
    private lateinit var mineralsText: TextView
    private lateinit var vespeneText: TextView
    private lateinit var supplyText: TextView
    private lateinit var unitsText: TextView
    
    private val apiClient = ApiClient()
    private val TAG = "MonitorFragment"
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_monitor, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        statusText = view.findViewById(R.id.statusText)
        gameStateContainer = view.findViewById(R.id.gameStateContainer)
        noGameMessage = view.findViewById(R.id.noGameMessage)
        mineralsText = view.findViewById(R.id.mineralsText)
        vespeneText = view.findViewById(R.id.vespeneText)
        supplyText = view.findViewById(R.id.supplyText)
        unitsText = view.findViewById(R.id.unitsText)
        
        startGameStateUpdates()
    }
    
    private fun startGameStateUpdates() {
        lifecycleScope.launch {
            while (true) {
                try {
                    val gameState = apiClient.getGameState()
                    
                    if (gameState != null) {
                        showGameState(gameState)
                        statusText.text = "Status: Connected - Game is running"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    } else {
                        showNoGameMessage()
                        statusText.text = "Status: Connected - No game running"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    }
                } catch (e: java.net.ConnectException) {
                    Log.e(TAG, "Connection failed: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "Status: Disconnected - Could not connect to server"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                } catch (e: java.net.SocketTimeoutException) {
                    Log.e(TAG, "Connection timed out: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "Status: Disconnected - Connection timed out"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                } catch (e: Exception) {
                    Log.e(TAG, "An error occurred: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "Status: Error - ${e.message ?: "Unknown error"}"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                }
                delay(1000) // Update every 1 second
            }
        }
    }
    
    private fun showGameState(gameState: GameState) {
        gameStateContainer.visibility = View.VISIBLE
        noGameMessage.visibility = View.GONE
        
        mineralsText.text = "Minerals: ${gameState.minerals}"
        vespeneText.text = "Vespene: ${gameState.vespene}"
        supplyText.text = "Supply: ${gameState.supplyUsed}/${gameState.supplyCap}"
        
        val totalUnits = gameState.units.values.sum()
        unitsText.text = "Total Units: $totalUnits"
    }
    
    private fun showNoGameMessage() {
        gameStateContainer.visibility = View.GONE
        noGameMessage.visibility = View.VISIBLE
    }
}
