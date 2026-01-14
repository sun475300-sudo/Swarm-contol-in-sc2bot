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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MonitorFragment : Fragment() {
    
    private lateinit var statusText: TextView
    private lateinit var gameStateContainer: ViewGroup
    private lateinit var noGameMessage: TextView
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
        
        // Initialize views
        statusText = view.findViewById(R.id.statusText)
        gameStateContainer = view.findViewById(R.id.gameStateContainer)
        noGameMessage = view.findViewById(R.id.noGameMessage)
        mineralsText = view.findViewById(R.id.mineralsText)
        vespeneText = view.findViewById(R.id.vespeneText)
        supplyText = view.findViewById(R.id.supplyText)
        unitsText = view.findViewById(R.id.unitsText)
        
        // Start real-time updates
        startGameStateUpdates()
    }
    
    private fun startGameStateUpdates() {
        lifecycleScope.launch {
            while (true) {
                try {
                    val gameState = apiClient.getGameState()
                    
                    // 게임이 실행 중인지 확인
                    if (gameState != null) {
                        // 게임 상태 표시
                        showGameState(gameState)
                        statusText.text = "서버 연결됨 - 게임 진행 중"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    } else {
                        // 게임 없음 메시지 표시
                        showNoGameMessage()
                        statusText.text = "서버 연결됨 - 게임 없음"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    }
                } catch (e: java.net.ConnectException) {
                    // 서버 연결 실패
                    Log.e(TAG, "서버 연결 실패: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "서버 연결 끊김 - 서버에 연결할 수 없습니다"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                } catch (e: java.net.SocketTimeoutException) {
                    // 타임아웃
                    Log.e(TAG, "서버 응답 타임아웃: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "서버 연결 끊김 - 응답 시간 초과"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                } catch (e: Exception) {
                    // 기타 오류
                    Log.e(TAG, "데이터 수신 오류: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "서버 연결 끊김 - ${e.message ?: "알 수 없는 오류"}"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                }
                delay(1000) // Update every 1 second
            }
        }
    }
    
    private fun showGameState(gameState: com.wickedzerg.mobilegcs.GameState) {
        // 게임 상태 컨테이너 표시
        gameStateContainer.visibility = View.VISIBLE
        noGameMessage.visibility = View.GONE
        
        // 데이터 업데이트
        mineralsText.text = "Minerals: ${gameState.minerals}"
        vespeneText.text = "Vespene: ${gameState.vespene}"
        supplyText.text = "Supply: ${gameState.supplyUsed}/${gameState.supplyCap}"
        
        val totalUnits = gameState.units.values.sum()
        unitsText.text = "Total Units: $totalUnits"
    }
    
    private fun showNoGameMessage() {
        // "현재 진행중인 게임이 없습니다" 메시지 표시
        gameStateContainer.visibility = View.GONE
        noGameMessage.visibility = View.VISIBLE
    }
}
