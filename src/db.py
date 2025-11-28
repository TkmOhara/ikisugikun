import sqlite3
from pathlib import Path

class db():
	def __init__(self):
		# プロジェクトの `src` ディレクトリを基準にデータベースを置く
		base_dir = Path(__file__).resolve().parent
		dbname = str(base_dir / 'audio.db')
		self.conn = sqlite3.connect(dbname)
		self.cur = self.conn.cursor()
		self.cur.execute(
			'CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, name STRING, filepath STRING, guild_id STRING)'
		)
		self.conn.commit()
	
	def insert_record(self, name, filepath, guild_id):
		data = [name, filepath, guild_id]

		self.cur.execute('INSERT INTO files (name, filepath, guild_id) VALUES (?, ?, ?)', data)
		self.conn.commit()

	def get_all_record(self):
		self.cur.execute('SELECT * FROM files')
		data = self.cur.fetchall()
		return data
	
	def get_record_by_id(self, id):
		self.cur.execute("SELECT * FROM files WHERE id = ?", (id,))
		data = self.cur.fetchall()
		return data

	def get_record_by_name(self, name):
		self.cur.execute("SELECT * FROM files WHERE name = ?", (name,))
		data = self.cur.fetchall()
		return data
	
	def delete_record_by_id(self, id):
		self.cur.execute("DELETE FROM files WHERE id = ?", (id,))
		self.conn.commit()
	
	def disconnect(self):
		self.cur.close()
		self.conn.close()