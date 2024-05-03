import sqlite3
from sqlite3 import Error
from typing import Literal, List
import sys, os
from pydantic import BaseModel

class Message(BaseModel):
    id: int = 0
    role: Literal["system", "user", "assistant"]
    content: str
    summary_id: int = 0

class Summary(BaseModel):
    id: int
    title: str
    summary: str
    entities: List[str]
    
class SummaryAndMessages(BaseModel):
    summary: Summary
    messages: List[Message]
    
class LocalDB:
    def __init__(self):
        cwd = os.getcwd()
        # print("cwd is", cwd, file=sys.stderr)
        if cwd.endswith("electron_groq"):            
            self.db_file=os.path.join(cwd, "database.db")
        else: 
            self.db_file=os.path.join(cwd, "resources", "database.db")
        
        self.system_message = """
        You are **SuperModels**, an ingenious human-computer interface that combines all the best AI models out there. You are fast, eloquent, and succinct. And you incorporate various research and analysis tools in your workflow. Furthermore, you have agency.
        """
        # You can write markdown and html.        
        # Keep your answers consise. 
        # The user works on Windows 11, uses chrome for browsing, knows some Javascript, but focusses on Python, SQL, and Python's many packages for data analysis. 

    def __enter__(self):
        """Open the database connection."""        
        conn = sqlite3.connect(self.db_file)
        
        # print("database connection made", file=sys.stderr)
        
        # conn.row_factory = sqlite3.Row
        self.conn = conn
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            
    def create_table(self, sys_mess=True):
        """Create a table in the SQLite database"""
        try:
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS temp_chat (
                                id integer PRIMARY KEY,
                                role text NOT NULL,
                                content text NOT NULL                                
                            );""")
            self.conn.commit()
            
            if sys_mess and not self.cursor.execute("SELECT COUNT(*) FROM temp_chat;").fetchone()[0]:
                self.insert_data("system", self.system_message)
                
        except Error as e:
            raise Exception("Failed to create table", e)

    def insert_data(self, role, content):
        try:
            self.cursor.execute("""
                        INSERT INTO temp_chat (role, content) 
                        VALUES (?, ?);""", (role, content))
            self.conn.commit()
        except Error as e:
            raise Exception("Failed to insert data", e)

    def load_temp(self) -> List[Message]:
        """Load the data as a dictionary."""
        try:
            conn = self.conn
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM temp_chat")
            rows = cursor.fetchall()
            data = [Message(role=row['role'], content=row['content']) for row in rows]
            return data
        except Error as e: # table does not exist  
            raise Exception("Failed to load_temp", e)
           
    def load_temp_from_history(self, summary_ids:List[str]) -> List[Message]:
        """Load the data as a dictionary."""
        try:
            conn = self.conn
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            messages = []
            for summary_id in summary_ids:
                master_rows = cursor.execute("""
                                             SELECT id, role, content 
                                             FROM master 
                                             WHERE summary_id = ?;
                                             """, (int(summary_id),)).fetchall()
                cursor.execute("""
                        INSERT INTO temp_chat (role, content) 
                        SELECT role, content 
                        FROM master WHERE summary_id = ?;
                        """, (int(summary_id),))
                conn.commit()
                
                messages += [Message(id=row['id'], role=row['role'], content=row['content']) for row in master_rows]

            return messages
        except Error as e: # table does not exist  
            raise Exception("Failed to load_temp_from_history", e)
             
        
    def drop_table(self):
        try:
            self.cursor.execute("DROP TABLE IF EXISTS temp_chat")
            self.conn.commit()
        except Error as e:
            raise Exception("Failed to drop_table", e)
            
    def load_master(self) -> List[SummaryAndMessages]:
        """Load the data as a dictionary."""
        try:
            sum_mes = []
            conn = self.conn
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            summary_rows = cursor.execute("SELECT * FROM summary;").fetchall()
            for summary_row in summary_rows:
                summary = Summary(id=summary_row['id'], title=summary_row['title'], summary=summary_row['summary'], entities=summary_row['entities'].split(', '))
                master_rows = cursor.execute("SELECT * FROM master WHERE summary_id = ?;", (summary.id,)).fetchall()
                messages = [Message(id=row['id'], role=row['role'], content=row['content'], summary_id=row['summary_id']) for row in master_rows]
                sum_mes.append(SummaryAndMessages(summary=summary, messages=messages))
            return sum_mes
        except Error as e: # table does not exist  
            raise Exception("Failed to load_as_dict", e)

    
    def drop_all(self):
        try:
            self.cursor.execute("DROP TABLE IF EXISTS temp_chat;")
            self.cursor.execute("DROP TABLE IF EXISTS summary;")
            self.cursor.execute("DROP TABLE IF EXISTS master;")
            self.conn.commit()
        except Error as e:
            raise Exception("Failed to drop_all", e)
            
if __name__ == '__main__':
    with LocalDB() as localdb: # a context manager implementation of a class to automatically handle opening and closing using 'with'
        localdb.create_table()
        localdb.insert_data("user", "hello this is my content")
        data_dict = localdb.load_temp()
        print(data_dict)
