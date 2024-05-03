from abc import ABC, abstractmethod
import json, sys
from pydantic import BaseModel, ValidationError
from localDb import Message
from typing import Generator, Union, Type, Optional
from ._base import Wrapper, ModelType
from ._tools import tools_json
from ._nos_tooluser import NoS_ToolUser
from ._tooluser import ToolUser

    
def agent_dispatcher(model_name_1:ModelType) -> (ToolUser | NoS_ToolUser):
    """
    This is slightly unelegant. Ideally the tooluser knows what to do.
    """
    if model_name_1 in ["gpt-4-turbo", "gpt-3.5-turbo"]:
        return ToolUser(model_name_1)
    elif model_name_1 in ["llama3-70b-8192", "llama3-8b-8192", "gemma-7b-it", "mixtral-8x7b-32768"]:
        return NoS_ToolUser(model_name_1)                
    else: 
        raise Exception("model_name_1 not found in tooluser", model_name_1) 
    
    
class BreakDownInSteps(BaseModel):
    steps: list[str]    

class YesOrNo(BaseModel):
    answer: bool
    reason: str
    userInputRequired: Optional[bool] = None
    
 # this is making it reflect on an anwser using the schema
class ReflectionBase(ABC):
    def __init__(self, prompt, model:ModelType): 
        self._model = model
        self._wrapper = Wrapper(model=self._model) if self._model else Wrapper()    
        self._schema = json.dumps(self.class_.model_json_schema(), indent=2)        
        self._prompt = prompt
        self._tools = json.dumps(tools_json, indent=2)
        self._messages = [Message(role="system", 
                            content=f"""
                            You are a highly critical reasoning engine that outputs JSON.
                            You have access to the following tools: {self._tools}.
                            The JSON object must use the schema: {self._schema}
                            """), 
                         Message(role="user", content= f"""
                                You were asked: \n{self._prompt}.""")]
    @property
    @abstractmethod
    def class_(self) -> Type[BaseModel]:
        """Subclasses should return their specific Pydantic model class."""
        pass
    
    def _request(self):
        self._main_request = self._wrapper.client.chat.completions.create(model=self._wrapper.model,
                                                               response_format={"type": "json_object"},
                                                               messages=self._messages) # type: ignore
  
    def call(self) -> Union[YesOrNo, BreakDownInSteps]: 
        """
        Forces the model into a schema. 
        :return: Either YesOrNo or BreakDownInSteps.
        """
        print(f'Starting reflection', file=sys.stderr)       
        
        try:
            self._request()             
            response = self._main_request.choices[0].message.content
            reflect_object = self.class_.model_validate_json(str(response))
            return reflect_object # type: ignore
        
        except ValidationError as e:
            raise Exception(f"Reflection call: {repr(e.errors(include_url=False, include_input=False))}. \n\nBefore validation: {response}")
                    
        except Exception as e:            
            # yield from stream_chunks("Sorry, I'm having some trouble. I forwarded the error to our tech team.")
            raise Exception(f"Reflection Call exception: {e.args}") 
            
    def close(self):
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()

class YesNoReflection(ReflectionBase):
    def __init__(self, prompt:str, answer:str, model:ModelType):
        """
        Uses the YesOrNo schema to force the model into True or False.
        :params prompt: The user's string.
        :params answer:The model's string.
        :params model: the model type with its full name.
        """
        super().__init__(prompt, model)   
        self._answer = answer
        print('YesNoReflection initialised with', self._wrapper._model, file=sys.stderr)
        self._messages = [Message(role="system", 
                        content=f"""
                        You have expert judgement that outputs JSON.
                        The JSON object must use the schema: {self._schema}
                        """),
                Message(role="system", 
                        content= f"""
                        The user requested: \n{self._prompt}. \n\nThe assistant answered: \n{self._answer}. \n\nIs this complete, accurate, balanced, and satisfactory in all possible ways, or is it partial or incomplete, or not satisfying all aspects of the original question? Answer this in 'true' or 'false' - as per your JSON schema - and give a short reason of max 25 words for your answer. Ask user input if required.
                        """)]
        # print("YesNoReflection messages:", self._messages, file=sys.stderr)
        
    @property
    def class_(self) -> Type[BaseModel]:
        """Return a Pydantic model class."""
        return YesOrNo
        
class BreakdownReflection(ReflectionBase):
    def __init__(self, prompt:str, model:ModelType, answer=None):
        """
        Uses the BreakDownInSteps schema to force the model into steps.
        :params prompt: The user's string.
        :params answer:The model's string.
        """
        super().__init__(prompt, model)
        self._messages[0].content=f"""
        You are a reasoning engine that outputs JSON. 
        You break down complex requests in simpler, actionable steps.
        You have access to the following tools: {self._tools}.
        If anything is in need of clarification, ask for user input using the optional keyword argument. 
        If the problem is simple, do not break it down, simple reformulate it for better understanding. Only complex requests require breaking down. So at all times, reduce complexity, do not add complexity. Never give more than 3 steps.
        The JSON object must use the following JSON schema: \n{self._schema}
        """
        self._messages[1].content = (
            f"You were asked: \n{self._prompt}.\n" 
            + (f'The answer you came up with is: \n{answer}. \n' if answer else '')
            + "Break this down in steps as per JSON schema."
            ) 
        
    @property
    def class_(self) -> Type[BaseModel]:
        """Return a Pydantic model class."""
        return BreakDownInSteps
    
    def test(self):
        response = '{"steps": ["Go to the shops.", "Buy fruit."]}'            
        return self.class_.model_validate_json(response)     

class Agent:
    def __init__(self, model_name_1:ModelType, maxIter = 3):
        self._maxIter = maxIter        
        self._tooluser = agent_dispatcher(model_name_1)
            
        self._model:ModelType = self._tooluser._wrapper._model     
        self._should_continue = None
        self._answer = ''
        print("Agent _tooluser_call initialised with :", self._model, file=sys.stderr) 
      
    def call(self, prompt) -> Generator[str, None, None]:
        """
        Break down the user's question before answering.
        
        :params prompt: The user's string.
        :params answer:The model's string.
        :return: Generates JSON strings.
        """
        print(f'Starting Agent', file=sys.stderr)
        try:
            FLAG = True
            counter = 0
            while FLAG:
                self._break_down = BreakdownReflection(prompt, model=self._model)
                break_down_call:BreakDownInSteps = self._break_down.call()  # type: ignore
                
                print(f'Breaking down in {len(break_down_call.steps)} steps ', file=sys.stderr) 
                
                yield json.dumps({"reflection": f"\n>Let's break this down:\n>- {'\n>- '.join(step for step in break_down_call.steps)}\n\n"})                
                
                for step in break_down_call.steps:
                    counter += 1
                    if counter > self._maxIter:
                        print("Max iter reached!", file=sys.stderr)
                        FLAG = False
                        break
                    
                    print("Agent _tooluser_call, with step:", step, file=sys.stderr) 
                    
                    for res in self._tooluser.call(step):
                        self._answer += json.loads(res).get('data', '')
                        yield res
                        
                    print("Agent tooluser_response", self._answer, file=sys.stderr)                    
                    
                    new_prompt = f"Let's take a moment to consider. We just tried to answer: \n {step} \n\nThis as part of \n- {"\n- ".join(step for step in break_down_call.steps)} \n\nThis to answer the original question: {prompt}. Are all steps answered with the anwer to this first step?"
                            
                    self._should_continue = YesNoReflection(new_prompt, self._answer, model=self._model)
                    
                    reflection:YesOrNo = self._should_continue.call() # type: ignore
                    
                    yield json.dumps({
                        'reflection': "\n>Let's take a moment to consider." 
                        + f"\n\n\tStep {counter}. " + step }) 
                    
                    if reflection.userInputRequired:
                        yield json.dumps({"reflection": f"\n>We need user input. {reflection.reason}\n\n"})
                        FLAG = False
                        break
                                        
                    elif reflection.answer: 
                        yield json.dumps({'reflection':  f"\n\n>We're happy with this answer 😊 \n\n\tThe reason is: {reflection.reason}" })  
                        FLAG = False
                        break
                                   
                    else:                     
                        yield json.dumps({"reflection": f"\n>{reflection.reason}\n\n"})
                        
                if not FLAG:
                    # the tooluser is currently handling the memory. It is loading reflections as user messages. 
                    # we should set a flag that the tooluser isn't supposed to log and instead log here, after every cycle. 
                    # ideally we accumulate the steps to give the model procedural memory.
                    self._answer = ''
                    break
                    
            
        except Exception as e:
            raise Exception("Agent:", e.args)
               
        finally:
            self.close()
    
    def close(self):
        self._tooluser.close()
        self._break_down.close()
        # self._should_continue.close()
        self._tooluser.close()     
    
