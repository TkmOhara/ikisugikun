import sqlite3
import json

settings_json = open('/home/ikisugikun/settings.json', 'r')
settings = json.load(settings_json)

class db():
	def __init__(self):
		dbname = settings['currentDirectory'] + '/audio.db'
		self.conn = sqlite3.connect(dbname)
		self.cur = self.conn.cursor()
		self.cur.execute(
			'CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, name STRING, filepath STRING)'
		)
		self.conn.commit()
	
	def insert_record(self, name, filepath):
		data = [name, filepath]

		self.cur.execute('INSERT INTO files (name, filepath) VALUES (?, ?)', data)
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