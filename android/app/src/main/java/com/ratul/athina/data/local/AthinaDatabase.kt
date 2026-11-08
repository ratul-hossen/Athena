package com.ratul.athina.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [MessageEntity::class], version = 1, exportSchema = false)
abstract class AthinaDatabase : RoomDatabase() {
    abstract val messageDao: MessageDao
}
