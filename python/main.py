"""
See dispatch init for notes.
"""

from dispatch import dispatcher
import sys, json
# from util import logger
from localDb import LocalDB, SummaryAndMessages, Message
from typing import List
    
res = ''
try:
    line = sys.stdin.read()
    
    print(f'line came in:', str(line), file=sys.stderr)
    
    input_dict = json.loads(line)
        
    if "prompt" in input_dict:
        prompt = input_dict['prompt']
        
        if "model_name" in input_dict:             
            model_name, model_type = input_dict.get('model_name')                  
            llm = dispatcher(model_name, model_type) 
            try: 
                keys = []
                for json_chunk in llm.call(prompt):
                    print(json_chunk)   
                    sys.stdout.flush()   
            except Exception as e:
                raise Exception(f'Prompt:', e.args)
                
            finally: 
                print(json.dumps({"end_of_stream": True}))
                sys.stdout.flush() 
                llm.close()
            
    if "drop_table" in input_dict:
        with LocalDB() as db: 
            # try: 
            db.drop_table()
            # finally: db.create_table()
        print('drop_table', file=sys.stderr)
        sys.stdout.flush()
    
    if "drop_all" in input_dict:
        with LocalDB() as db: 
            # try: 
            db.drop_all()
            # finally: db.create_table()
        print('drop_all', file=sys.stderr)
        sys.stdout.flush()
    
    if "load_master" in input_dict:
        with LocalDB() as db: 
            sum_mes:List[SummaryAndMessages] = db.load_master()
            
        messages_ = [mes.model_dump() for mes in sum_mes] # transforms to dict
        print(json.dumps({"load_master": messages_}))
        
        sys.stdout.flush() 
        
    if "summary_ids" in input_dict:     # this drops the current table and loads one from conversation history
        summary_ids = input_dict.get('summary_ids')           
        with LocalDB() as db:
            db.drop_table() # we could start by summarizing this one too but that creates lag
            db.create_table()
            messages:List[Message] = db.load_temp_from_history(summary_ids=summary_ids)
       
        messages_ = [mes.model_dump() for mes in messages] 
        
        print(json.dumps({"load_history": messages_}))
        
        sys.stdout.flush() 
        
except Exception as e:
    print(f'Main:', e.args, file=sys.stderr)

finally:
    sys.stdout.flush() 
    
"""
To activate the env:
cd Z:/electron_groq/python/env/Scripts
activate
"""