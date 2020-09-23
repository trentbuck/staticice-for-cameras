import sqlite3

class MySqliteWriter:
    def __init__(self):
        self.conn = sqlite3.connect('tmp.db')
        self.conn.execute('CREATE TABLE IF NOT EXISTS quotes(author TEXT NOT NULL, quote TEXT PRIMARY KEY, tagsoup TEXT NOT NULL)')
        sqlite3.register_adapter(list, lambda l: ','.join(l))  # FIXME: filthy hack
    def process_item(self, item, spider):
        self.conn.execute('REPLACE INTO quotes(author, quote, tagsoup) VALUES (:author, :text, :tags)', item.__dict__)
        self.conn.commit()  # FIXME: close conn properly, so this isn't needed
        return item
