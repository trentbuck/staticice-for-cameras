import sqlite3

import scrapy.exporters

class SqliteExporter(scrapy.exporters.BaseItemExporter):
    def __init__(self):
        super().__init__(**kwargs)
    def start_exporting(self):
        self.conn = sqlite3.connect('tmp.db')
        self.conn.execute('CREATE TABLE IF NOT EXISTS quotes(author TEXT NOT NULL, quote TEXT PRIMARY KEY, tagsoup TEXT NOT NULL)')
    def export_item(self, item, spider):
        self.conn.execute('REPLACE INTO quotes(author, quote, tagsoup) VALUES (:author, :text, :tags)', item.__dict__)
    def stop_exporting(self):
        self.conn.close()
