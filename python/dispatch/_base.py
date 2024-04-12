import json, time, os, sys
from typing import Literal, Generator
from abc import ABC, abstractmethod
from localDb import Message

# Type alias
ModelType = Literal["llama2-70b-4096", "mixtral-8x7b-32768", "gemma-7b-it",
                    "gpt-4-turbo-preview", "gpt-3.5-turbo", "sonar-medium-online"]

class Wrapper:
    def __init__(self, model: ModelType = "mixtral-8x7b-32768"):
        
        self._model: ModelType = model
             
        if model in ["llama2-70b-4096", "mixtral-8x7b-32768", "gemma-7b-it"]:
            from groq import Groq
            API_KEY = os.getenv('GROQ_API_KEY')
            if API_KEY:
                self.client = Groq(api_key=API_KEY)
                
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to groq.com and request an API KEY.")
                if res:
                    os.environ['GROQ_API_KEY'] = res
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))
                raise EnvironmentError("GROQ_API_KEY is not set in the environment variables.")            
            
        elif model in ["gpt-4-turbo-preview", "gpt-3.5-turbo"]:    
            from openai import OpenAI 
            API_KEY = os.getenv('OPENAI_API_KEY')
            if API_KEY:
                self.client = OpenAI(api_key=API_KEY)  
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to openai.com and request an API KEY.")
                if res:
                    os.environ['OPENAI_API_KEY'] = res
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))               
                raise EnvironmentError("OPENAI_API_KEY is not set in the environment variables.")   
            
        elif model in ["sonar-medium-online"]:            
            from openai import OpenAI
            API_KEY = os.getenv('PERP_API_KEY')
            if API_KEY:
                self.client = OpenAI(api_key=API_KEY, base_url="https://api.perplexity.ai")        
            else:
                from tkinter import simpledialog
                res = simpledialog.askstring("Missing API KEY", "Go to perplexity.ai and request an API KEY.")
                if res:
                    os.environ['PERP_API_KEY'] = res
                    print(json.dumps({'data': "The API key will work once you restart your PC."}))               
                raise EnvironmentError("PERP_API_KEY is not set in the environment variables.")  
        
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

 