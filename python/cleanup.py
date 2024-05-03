from localDb import LocalDB, Message
from sqlite3 import Error, PrepareProtocol
from util import logger
from pydantic import BaseModel
from typing import Literal, Generator, List
from dispatch._base import BaseLLM, Wrapper
import json

class Summary(BaseModel):
    # id: int 
    title: str
    summary: str
    entities: List[str]
    
schema = {json.dumps(Summary.model_json_schema(), indent=2)}

class CleanupLLM(BaseLLM):
    def __init__(self):
        logger.debug('Started CleanupLLM.')
        self.wrapper = Wrapper() # was mixtral, now default aka llama3
        self._model = self.wrapper.model
        
    def _request(self, messages): 
        pass
        
    def call(self, messages, schema) -> str:
        messages.append(Message(role="system", content=f"You are a summary database that outputs summaries in JSON.\n\
            The JSON object must use the schema: {schema}"))
            
        messages.append(Message(role="user", content="Summarise the above conversation in max 50 words and list up all (max 10) named entities."))

        try: 
            main_request = self.wrapper.client.chat.completions.create(model=self._model,
                                                    messages=messages,
                                                    response_format={"type": "json_object"})
                    
            return main_request.choices[0].message.content or ''
            
        except Exception as e:
            logger.error(f"summary_call exception: {e.args}") 
            return ''
               
    def close(self):
        """Close the connection."""
        if getattr(self, 'client', None) is not None:
            self.wrapper.client.close()
            
with LocalDB() as db: 
    try:
        # generate a summary
        messages:List[Message] = db.load_temp()
        
        if len(messages) > 1: # taking into account the sys message
            cleanup = CleanupLLM()
            res = cleanup.call(messages, schema)
            
            summary = Summary.model_validate_json(res)
            
            # insert the summary table
            db.cursor.execute("""CREATE TABLE IF NOT EXISTS summary (
                                id integer PRIMARY KEY,
                                title text NOT NULL,
                                summary text NOT NULL, 
                                entities text NOT NULL
                                );""")
            
            db.cursor.execute("""
                INSERT INTO summary (title, summary, entities) 
                VALUES (?, ?, ?);""", (summary.title, summary.summary, ', '.join(summary.entities)))
            
            logger.debug('loaded a summary.')
            
            # write the temp_chat table to the master
            sum_id = db.cursor.execute("""SELECT MAX(id) FROM summary;""").fetchone()[0]        
            
            db.cursor.execute("CREATE TABLE IF NOT EXISTS master (id, role, content, summary_id);")
            
            db.cursor.execute("""
                            INSERT INTO master (id, role, content, summary_id)
                            SELECT id, role, content, ? FROM temp_chat;
                            """, (sum_id,))
            
            db.cursor.execute("DROP TABLE IF EXISTS temp_chat;")
            
            db.conn.commit()
            
            logger.debug('Cleanup succeeded.')
        else: 
            logger.debug('No messages in temp_table. No summary attempted.')
        
    except Error as e:
        logger.error('Cleanup ran into error: ', str(e.args))
        db.conn.rollback()