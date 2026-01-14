package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ManusApiClient
import com.wickedzerg.mobilegcs.models.TrainingEpisode
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class TrainingFragment : Fragment() {
    
    private lateinit var totalEpisodesText: TextView
    private lateinit var averageRewardText: TextView
    private lateinit var averageWinRateText: TextView
    private lateinit var totalGamesText: TextView
    private lateinit var recentEpisodesRecyclerView: RecyclerView
    private lateinit var statusText: TextView
    
    private val manusApiClient = ManusApiClient()
    private val episodeAdapter = TrainingEpisodeAdapter(emptyList())
    private var isServerConnected = false
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_training, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        totalEpisodesText = view.findViewById(R.id.totalEpisodesText)
        averageRewardText = view.findViewById(R.id.averageRewardText)
        averageWinRateText = view.findViewById(R.id.averageWinRateText)
        totalGamesText = view.findViewById(R.id.totalGamesText)
        recentEpisodesRecyclerView = view.findViewById(R.id.recentEpisodesRecyclerView)
        statusText = view.findViewById(R.id.statusText)
        
        // Setup RecyclerView
        recentEpisodesRecyclerView.layoutManager = LinearLayoutManager(requireContext())
        recentEpisodesRecyclerView.adapter = episodeAdapter
        
        // Load data
        loadTrainingData()
    }
    
    private fun loadTrainingData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // ?? ??
                    val stats = manusApiClient.getTrainingStats()
                    stats?.let {
                        totalEpisodesText.text = "Total Episodes: ${it.total_episodes}"
                        averageRewardText.text = "Average Reward: ${String.format("%.2f", it.average_reward)}"
                        averageWinRateText.text = "Average Win Rate: ${String.format("%.1f", it.win_rate * 100)}%"
                        totalGamesText.text = "Total Games: -" // TrainingStats? total_games? ??
                    }
                    
                    // ?? ????
                    val recentEpisodes = manusApiClient.getRecentEpisodes(20)
                    episodeAdapter.updateEpisodes(recentEpisodes)
                    
                    // ?? ?? ??
                    if (!isServerConnected) {
                        isServerConnected = true
                        statusText.visibility = View.GONE
                    }
                } catch (e: java.net.ConnectException) {
                    // ?? ?? ??
                    Log.e("TrainingFragment", "?? ?? ??: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("??? ??? ? ????")
                } catch (e: java.net.SocketTimeoutException) {
                    // ????
                    Log.e("TrainingFragment", "?? ?? ????: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("?? ?? ?? ??")
                } catch (e: Exception) {
                    // ?? ??
                    Log.e("TrainingFragment", "??? ?? ??: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("?? ?? ??: ${e.message ?: "? ? ?? ??"}")
                }
                delay(5000) // 5??? ????
            }
        }
    }
    
    private fun showServerDisconnected(message: String) {
        statusText.text = "Server Disconnected: $message"
        statusText.setTextColor(requireContext().getColor(R.color.red))
        statusText.visibility = View.VISIBLE
        
        // ??? ???
        totalEpisodesText.text = "Total Episodes: -"
        averageRewardText.text = "Average Reward: -"
        averageWinRateText.text = "Average Win Rate: -"
        totalGamesText.text = "Total Games: -"
        episodeAdapter.updateEpisodes(emptyList())
    }
    
    // RecyclerView Adapter
    private class TrainingEpisodeAdapter(private var episodes: List<TrainingEpisode>) :
        RecyclerView.Adapter<TrainingEpisodeAdapter.ViewHolder>() {
        
        fun updateEpisodes(newEpisodes: List<TrainingEpisode>) {
            episodes = newEpisodes
            notifyDataSetChanged()
        }
        
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }
        
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val episode = episodes[position]
            holder.text1.text = "Episode ${episode.episode}"
            holder.text2.text = "Reward: ${String.format("%.2f", episode.reward)}, Win Rate: ${String.format("%.1f", episode.winRate * 100)}%"
        }
        
        override fun getItemCount() = episodes.size
        
        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val text1: TextView = view.findViewById(android.R.id.text1)
            val text2: TextView = view.findViewById(android.R.id.text2)
        }
    }
}
