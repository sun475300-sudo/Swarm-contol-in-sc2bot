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
import com.wickedzerg.mobilegcs.api.ManusApiClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class HomeFragment : Fragment() {
    
    private lateinit var totalGamesText: TextView
    private lateinit var winRateText: TextView
    private lateinit var currentELOText: TextView
    private lateinit var totalEpisodesText: TextView
    private lateinit var statusText: TextView
    
    private val manusApiClient = ManusApiClient()
    private val TAG = "HomeFragment"
    private var isServerConnected = false
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_home, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        totalGamesText = view.findViewById(R.id.totalGamesText)
        winRateText = view.findViewById(R.id.winRateText)
        currentELOText = view.findViewById(R.id.currentELOText)
        totalEpisodesText = view.findViewById(R.id.totalEpisodesText)
        statusText = view.findViewById(R.id.statusText)
        
        // Load data
        loadSummaryData()
    }
    
    private fun loadSummaryData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // 전투 통계
                    val battleStats = manusApiClient.getBattleStats()
                    battleStats?.let {
                        val totalGames = it.wins + it.losses
                        totalGamesText.text = "Total Games: $totalGames"
                        winRateText.text = "Win Rate: ${String.format("%.1f", it.win_rate * 100)}%"
                    }
                    
                    // Arena 통계
                    val arenaStats = manusApiClient.getArenaStats()
                    arenaStats?.let {
                        // ELO는 ArenaStats에 없으므로 제거하거나 다른 필드 사용
                    }
                    
                    // 학습 통계
                    val trainingStats = manusApiClient.getTrainingStats()
                    trainingStats?.let {
                        totalEpisodesText.text = "Total Episodes: ${it.total_episodes}"
                    }
                    
                    // 서버 연결 성공
                    if (!isServerConnected) {
                        isServerConnected = true
                        statusText.text = "Server Connected"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                        statusText.visibility = View.GONE // 연결되면 숨김
                    }
                } catch (e: java.net.ConnectException) {
                    // 서버 연결 실패
                    Log.e(TAG, "서버 연결 실패: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버에 연결할 수 없습니다")
                } catch (e: java.net.SocketTimeoutException) {
                    // 타임아웃
                    Log.e(TAG, "서버 응답 타임아웃: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버 응답 시간 초과")
                } catch (e: Exception) {
                    // 기타 오류
                    Log.e(TAG, "데이터 수신 오류: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버 연결 오류: ${e.message ?: "알 수 없는 오류"}")
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
    
    private fun showServerDisconnected(message: String) {
        statusText.text = "Server Disconnected: $message"
        statusText.setTextColor(requireContext().getColor(R.color.red))
        statusText.visibility = View.VISIBLE
        
        // 데이터 초기화
        totalGamesText.text = "Total Games: -"
        winRateText.text = "Win Rate: -"
        currentELOText.text = "Current ELO: -"
        totalEpisodesText.text = "Total Episodes: -"
    }
}
