package com.wickedzerg.mobilegcs.models

data class TrainingEpisode(
    val episode_number: Int,
    val reward: Float,
    val duration_seconds: Int,
    val result: String
)
