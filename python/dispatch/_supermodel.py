import json, time, os, sys
from localDb import LocalDB
from typing import Generator
from ._base import BaseLLM, Wrapper, stream_chunks
     
class SuperModel(BaseLLM):
    def __init__(self, model=None):        
        self._wrapper = Wrapper(model=model) if model else Wrapper()
        
        print('model passed to SuperModel:', self._wrapper.model, file=sys.stderr)
        
    def _request(self, messages):
        """
        :param messages: A list of messages.
        :return: The main_request object.
        """
        self.main_request = self._wrapper.client.chat.completions.create(model=self._wrapper.model, 
                                            messages=messages, # type:ignore
                                            stream=True)
        
    def call(self, prompt:str) -> Generator[str, None, None]:
        """
        The main call.
        :param prompt: A simple string.
        :return: JSON string.
        """
        with LocalDB() as db:
            db.create_table()
            db.insert_data("user", prompt)
            messages = db.load_temp()
            
        print(f'making call', str(messages), file=sys.stderr)
        
        self._request(messages) 
        
        full_response = ""        
        try:                                  
            for res in self.main_request:       
                delta = res.choices[0].delta
                if delta.content: 
                    content_chunk = delta.content
                    full_response += content_chunk
                    yield json.dumps({"data": content_chunk})                                
               
            with LocalDB() as db: 
                db.insert_data('assistant', full_response)

        except Exception as e:            
            yield from stream_chunks("Sorry, I'm having some trouble. I forwarded the error to our tech team.")
            raise Exception(f"Call exception: {e.args}")        
               
    def close(self) -> None:
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()

class SuperModelClaude(BaseLLM):
    def __init__(self, model):
        self._wrapper = Wrapper(model=model) if model else Wrapper()
        print('model passed to SuperModel:', self._wrapper.model, file=sys.stderr)
        # super().__init__(model)
    
    def _request(self, messages):
        pass
    
    def call(self, prompt: str) -> Generator[str, None, None]:     
        with LocalDB() as db:
            db.create_table(sys_mess=False)
            db.insert_data("user", prompt)
            messages_ = db.load_temp()
            
        # print(f'making call', str(messages_), file=sys.stderr)
        
        full_response = ""        
        try:
            with self._wrapper.client.messages.stream(model=self._wrapper.model,
                                                      max_tokens=1000,
                                                      system="You are a supermodel.",
                                                      messages=messages_) as stream:
                for text in stream.text_stream:
                    if text: 
                        content_chunk = text
                        full_response += content_chunk
                        yield json.dumps({"data": text})    
                    
            with LocalDB() as db: 
                db.insert_data('assistant', full_response)

        except Exception as e:            
            yield from stream_chunks("Sorry, I'm having some trouble. I forwarded the error to our tech team.")
            raise Exception(f"Call exception: {e.args}")  
              
    def close(self) -> None:
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()