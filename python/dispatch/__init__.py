from ._supermodel import SuperModel
from ._tooluser import ToolUser, ToolUserNoStream
from ._agent import Agent
from ._base import ModelType

def notimplemented(model_type):
    from tkinter import messagebox
    return messagebox.showinfo("Not implemented", f"{model_type.capitalize()} hasn't been implemented yet, sorry. Falling back on dze French SuperModel: Mixtral.")

def dispatcher(model_name:str, model_type:ModelType) -> SuperModel | ToolUserNoStream | ToolUser | Agent: 
    """
    Choose the model name and type.
    :param model_name: The name, Supermodel, Tooluser, or Agent.
    :param model_type: The type of LLM, GPT-4-Turbo, LLaMA or Mixtral.
    :return: a model.
    """
    try:
        if "SuperModel" in model_name:            
            if "llama2" in model_type:                
                llm = SuperModel("llama2-70b-4096")                
            elif "gemma" in model_type:
                llm = SuperModel("gemma-7b-it")
            elif "gpt4" in model_type:
                llm = SuperModel("gpt-4-turbo-preview")
            elif "gpt3" in model_type:
                llm = SuperModel("gpt-3.5-turbo") 
            elif "mixtral" in model_type or model_type is None:
                llm = SuperModel("mixtral-8x7b-32768") 
            else: 
                notimplemented(model_type)
                    
        if "ToolUser" in model_name:  
            if "llama2" in model_type:
                llm = ToolUserNoStream("llama2-70b-4096")                
            elif "gemma" in model_type:
                llm = ToolUserNoStream("gemma-7b-it")
            elif "gpt4" in model_type:
                llm = ToolUser("gpt-4-turbo-preview")
            elif "gpt3" in model_type:
                llm = ToolUser("gpt-3.5-turbo")
            elif "mixtral" in model_type or model_type is None:
                llm = ToolUserNoStream("mixtral-8x7b-32768") 
            else: 
                notimplemented(model_type)
            
        if "Agent" in model_name:
            if "llama2" in model_type:
                llm = Agent(model_name_1="llama2-70b-4096")                
            elif "gemma" in model_type:
                llm = Agent(model_name_1="gemma-7b-it")
            elif "gpt4" in model_type:
                llm = Agent(model_name_1="gpt-4-turbo-preview")
            elif "gpt3" in model_type:
                llm = Agent(model_name_1="gpt-3.5-turbo")
            elif "mixtral" in model_type or model_type is None:
                llm = Agent(model_name_1="mixtral-8x7b-32768") 
            else: 
                notimplemented(model_type)
                
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