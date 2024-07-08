import json, time, os, sys
from typing import Literal, Generator
from abc import ABC, abstractmethod
from localDb import Message, LocalDB

# Type alias
ModelType = Literal["llama3-70b-8192", 
                    "llama3-8b-8192", 
                    "mixtral-8x7b-32768", 
                    "gemma2-9b-it",
                    "gpt-4o", # "gpt-4-turbo", 
                    "gpt-3.5-turbo", 
                    "llama-3-sonar-large-32k-online",
                    "claude-3-5-sonnet-20240620"] #  gemini


class Wrapper:
    def __init__(self, model: ModelType = "llama3-70b-8192") -> None: 
        """
        The initialisation takes a model name and returns a client instance. 
        When the wrapper has no model specified it falls back on llama3-70b-8192.
        
        :params model: "llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it", "gpt-4-turbo", "gpt-3.5-turbo", "llama-3-sonar-large-32k-online", "claude-3-5-sonnet-20240620"
        :returns: the API client.
        """
        self._model: ModelType = model
        
        if model in ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]:
            from groq import Groq
            API_KEY = os.getenv('GROQ_API_KEY')
            if API_KEY:
                self.client = Groq(api_key=API_KEY)
                
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to groq.com and request an API KEY.")
                if res:
                    import subprocess
                    subprocess.run(['setx', 'GROQ_API_KEY', f'{res}'], shell=True)
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))
                raise EnvironmentError("GROQ_API_KEY is not set in the environment variables.")            
            
        elif model in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]:    
            from openai import OpenAI 
            API_KEY = os.getenv('OPENAI_API_KEY')
            if API_KEY:
                self.client = OpenAI(api_key=API_KEY)  
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to openai.com and request an API KEY.")
                if res:
                    import subprocess
                    subprocess.run(['setx', 'OPENAI_API_KEY', f'{res}'], shell=True)
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))            
                raise EnvironmentError("OPENAI_API_KEY is not set in the environment variables.")   
            
        elif model in ["llama-3-sonar-large-32k-online"]:            
            from openai import OpenAI
            API_KEY = os.getenv('PERP_API_KEY')
            if API_KEY:
                self.client = OpenAI(api_key=API_KEY, base_url="https://api.perplexity.ai")
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to perplexity.ai and request an API KEY.")
                if res:
                    import subprocess
                    subprocess.run(['setx', 'PERP_API_KEY', f'{res}'], shell=True)
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))
                raise EnvironmentError("PERP_API_KEY is not set in the environment variables.")  
        
        elif model in ["claude-3-5-sonnet-20240620"]:
            from anthropic import Anthropic
            API_KEY = os.getenv('ANTHROPIC_API_KEY')
            if API_KEY:
                self.client = Anthropic(api_key=API_KEY)
                
                # this is inefficient
                with LocalDB() as db: 
                    if 'system' == db.load_temp()[0].role:
                        db.drop_table()
                        db.create_table(sys_mess=False)
                        
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to anthropic.com and request an API KEY.")
                if res:
                    import subprocess
                    subprocess.run(['setx', 'ANTHROPIC_API_KEY', f'{res}'], shell=True)
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))
                raise EnvironmentError("ANTHROPIC_API_KEY is not set in the environment variables.")  
        
        # TODO
        # elif model in ["gemini-1.5-pro-latest"]: 
        #     import anthropic
        #     API_KEY = os.getenv('ANTHROPIC_API_KEY')
        #     if API_KEY:
        #         self.client = anthropic.Anthropic(API_KEY)
        #     else:
        #         from tkinter import simpledialog
        #         res = simpledialog.askstring("Missing API KEY", "Go to anthropic.com and request an API KEY.")
        #         if res:
        #             import subprocess
        #             subprocess.run(['setx', 'ANTHROPIC_API_KEY', f'{res}'], shell=True)
        #             print(json.dumps({'data': "The API key will work once you restart your PC."}))
        #         raise EnvironmentError("ANTHROPIC_API_KEY is not set in the environment variables.")  
        
        if not self.client:            
            raise ValueError(f"Failed to initialize API client for model: {model}")
        
    @property
    def model(self):
        """Every wrapper instance has a model. This method allows you to get it."""
        return self._model
    
class BaseLLM(ABC):
    @abstractmethod
    def __init__(self, model:ModelType):
        """
        :param model: This is the model that is passed onto Wrapper.
        """
        self._model = model
        self._wrapper = Wrapper(model) if model else Wrapper()   
        pass
    @abstractmethod
    def _request(self, messages:list[Message]):
        """The client object for easy closing - particularly when streaming."""
        pass
    @abstractmethod
    def call(self, prompt: str): 
        """call the LLM with a prompt
        :param prompt: The prompt as str"""
        pass
    @abstractmethod
    def close(self) -> None:        
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()
        pass
  
  
def stream_chunks(text:str) -> Generator[str, None, None]:
    """
    Fake stream. Chops up any text and delivers it in JSON chunks.
    :param text: A simple string.
    :return: Generates JSON strings.
    """
    words = text.split(" ")
    for word in words:
        time.sleep(0.05)
        yield json.dumps({"alt_stream": word + ' '}) # alt_stream

 