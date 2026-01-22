from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3

app = FastAPI()
db_path = "/data/memory.db"
conn = sqlite3.connect(db_path)
conn.execute("""CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input TEXT,
    response TEXT
)""")
conn.commit()
conn.close()

class MemoryItem(BaseModel):
    input: str
    response: str

@app.post("/store")
def store(item: MemoryItem):
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO memory (input,response) VALUES (?,?)",
                 (item.input, item.response))
    conn.commit()
    conn.close()
    return {"status": "ok"}
