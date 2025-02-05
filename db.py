import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('posts.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                city TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                status TEXT NOT NULL,
                content TEXT,
                is_published INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def add_post(self, post_data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scheduled_posts (
                id, message_id, chat_id, scheduled_time, city, 
                approved_by, status, content, is_published
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (
            post_data['post_id'],
            str(post_data['message_id']), 
            str(post_data['chat_id']),
            post_data['scheduled_time'],
            post_data['city'],
            post_data['approved_by'],
            post_data['status'],
            post_data.get('content', '')
        ))
        self.conn.commit()

    def get_pending_posts(self):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT * FROM scheduled_posts 
            WHERE scheduled_time <= ? AND is_published = 0
        ''', (now,))
        return cursor.fetchall()

    def mark_as_published(self, post_id: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE scheduled_posts 
            SET is_published = 1 
            WHERE id = ?
        ''', (post_id,))
        self.conn.commit()

    def clean_old_posts(self, days=7):
        cursor = self.conn.cursor()
        cleanup_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute('''
            DELETE FROM scheduled_posts 
            WHERE scheduled_time < ? AND is_published = 1
        ''', (cleanup_date,))
        self.conn.commit()

    def close(self):
        self.conn.close()
