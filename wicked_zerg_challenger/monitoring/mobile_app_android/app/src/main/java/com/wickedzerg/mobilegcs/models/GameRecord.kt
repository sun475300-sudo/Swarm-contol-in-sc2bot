package com.wickedzerg.mobilegcs.models

import java.util.Date

data class GameRecord(
    val map_name: String,
    val opponent_id: String,
    val opponent_race: String,
    val result: String,
    val game_duration_seconds: Int,
    val played_at: Date
)
