"""
avoid using model names across the project, only use them here and in _base.  

TODO: 
    - use model_type variables for each model, define them all in one place for easy updating. Preferably top-level. 
    - use map() or another way of writing the dispatcher below
    
    - also fix how claude initiates a temp chat table
"""

from ._supermodel import SuperModel, SuperModelClaude
from ._tooluser import ToolUser
from ._nos_tooluser import NoS_ToolUser
from ._agent import Agent
from ._base import ModelType

def notimplemented(model_type, model_name):
    from tkinter import messagebox
    return messagebox.showinfo("Not implemented", f"{model_type.capitalize()} hasn't been implemented yet for {model_name}, sorry. Falling back on LLaMA 3 70B.")

def dispatcher(model_name:str, model_type:ModelType) -> SuperModel | SuperModelClaude | NoS_ToolUser | ToolUser | Agent: 
    """
    Choose the model name and type.
    :param model_name: The name, Supermodel, Tooluser, or Agent.
    :param model_type: The type of LLM, GPT-4-Turbo, LLaMA3 or Mixtral.
    :return: a model.
    """
    try:
        if "SuperModel" in model_name:            
            if "mixtral" in model_type:                
                llm = SuperModel("mixtral-8x7b-32768") 
            elif "llama3-8b" in model_type:                
                llm = SuperModel("llama3-8b-8192")
            elif "llama-3-sonar" in model_type:                
                llm = SuperModel("llama-3-sonar-large-32k-online")
            elif "gemma" in model_type:
                llm = SuperModel("gemma2-9b-it")
            elif "gpt4" in model_type:
                llm = SuperModel("gpt-4o") # "gpt-4-turbo")
            elif "gpt3" in model_type:
                llm = SuperModel("gpt-3.5-turbo") 
            elif "claude" in model_type:
                llm = SuperModelClaude("claude-3-5-sonnet-20240620")
            elif "llama3" in model_type or model_type is None:                
                llm = SuperModel("llama3-70b-8192")
            
            else: 
                notimplemented(model_type, model_name)
                llm = SuperModel("llama3-70b-8192")
                    
        if "ToolUser" in model_name:  
            if "mixtral" in model_type:
                llm = NoS_ToolUser("mixtral-8x7b-32768")         
            elif "llama3-8b" in model_type:
                llm = NoS_ToolUser("llama3-8b-8192")          
            elif "gemma" in model_type:
                llm = NoS_ToolUser("gemma2-9b-it")
            elif "gpt4" in model_type:
                llm = ToolUser("gpt-4o") # "gpt-4-turbo")
            elif "gpt3" in model_type:
                llm = ToolUser("gpt-3.5-turbo")
            elif "llama3" in model_type or model_type is None:
                llm = NoS_ToolUser("llama3-70b-8192") 
            else: 
                notimplemented(model_type, model_name)
                llm = SuperModel("llama3-70b-8192")
            
        if "Agent" in model_name:
            if "mixtral" in model_type:
                llm = Agent(model_name_1="mixtral-8x7b-32768")    
            elif "llama3-8b" in model_type:
                llm = Agent(model_name_1="llama3-8b-8192")            
            elif "gemma" in model_type:
                llm = Agent(model_name_1="gemma2-9b-it")
            elif "gpt4" in model_type:
                llm = Agent(model_name_1="gpt-4o") # "gpt-4-turbo")
            elif "gpt3" in model_type:
                llm = Agent(model_name_1="gpt-3.5-turbo")
            elif "llama3" in model_type or model_type is None:
                llm = Agent(model_name_1="llama3-70b-8192") 
            else: 
                notimplemented(model_type, model_name)
                llm = SuperModel("llama3-70b-8192")
                
        return llm
    
    except IndexError as e:
        raise Exception("the model name should come in two parts.", e) 

    
# from dotenv import load_dotenv
# import os, sys

# cwd = os.getcwd()
# if cwd.endswith("electron_groq"):            
#     env_path=os.path.join(cwd, "python", ".env")
# else: 
#     env_path=os.path.join(cwd, "resources", "python", ".env")

# load_dotenv(env_path)