import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('posts.db')
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            chat_id TEXT,
            scheduled_time TEXT,
            city TEXT,
            approved_by TEXT,
            status TEXT,
            content TEXT,
            is_published INTEGER DEFAULT 0
        )''')
        self.conn.commit()
    
    def add_post(self, post_data):
        """new post delaem"""
        cursor = self.conn.cursor()
        try:
            # Проверяем и конвертируем message_id если нужно
            message_id = post_data['message_id']
            if not isinstance(message_id, str):
                message_id = str(message_id)

            cursor.execute('''
            INSERT INTO scheduled_posts 
            (id, message_id, chat_id, scheduled_time, city, approved_by, status, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data['post_id'],
                message_id,  # Используем конвертированный message_id
                post_data['chat_id'],
                post_data['scheduled_time'],
                post_data['city'],
                post_data['approved_by'],
                post_data['status'],
                post_data.get('content', '')
            ))
            self.conn.commit()
            print(f"Добавлен пост {post_data['post_id']} на {post_data['scheduled_time']}")  # Добавляем логирование
        except Exception as e:
            print(f"Ошибка при добавлении поста: {e}")
            raise e

    def get_pending_posts(self):
        """done post delaem"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT * FROM scheduled_posts 
            WHERE is_published = 0 
            AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        ''', (now,))
        posts = cursor.fetchall()
        print(f"Найдено {len(posts)} постов для публикации")
        return posts

    def mark_as_published(self, post_id):
        """done"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                UPDATE scheduled_posts 
                SET is_published = 1,
                    scheduled_time = datetime('now', 'localtime')
                WHERE id = ?
            ''', (post_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении статуса поста {post_id}: {e}")
            return False

    def clean_old_posts(self):
        """clean delaem old post"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM scheduled_posts 
                WHERE is_published = 1 
                AND datetime(scheduled_time) < datetime('now', '-1 hour', 'localtime')
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка при очистке старых постов: {e}")

    def close(self):
        self.conn.close()
