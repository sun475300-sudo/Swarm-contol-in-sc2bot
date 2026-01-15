package com.wickedzerg.mobilegcs.models

import java.util.Date

data class ArenaMatch(
    val opponent_name: String,
    val result: String,
    val eloAfter: Int,
    val eloChange: Int,
    val played_at: Date
)
