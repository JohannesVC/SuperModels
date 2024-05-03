import json, sys
from localDb import LocalDB, Message
from typing import Generator
from ._base import BaseLLM, Wrapper, stream_chunks
from ._tools import tools_json, Online_llm, Coder

class NoS_ToolUser(BaseLLM):
    """The non streaming ToolUser"""
    def __init__(self, model=None):        
        self._wrapper = Wrapper(model=model) if model else Wrapper() 
        print('model passed to ToolUserNoStream:', self._wrapper.model, file=sys.stderr)
        self._tools = tools_json
        
    def _request(self, messages):   
        return self._wrapper.client.chat.completions.create(model=self._wrapper.model,  # type: ignore
                                            messages=messages, # type:ignore                                            
                                            tools=self._tools, # type: ignore
                                            max_tokens=1000, 
                                            # tool_choice={"type": "function", "function": {"name": "python_wizzard"}}
                                            )
        
    def call(self, prompt:str) -> Generator[str, None, None]: 
        """
        This streams the results despite being `stream=False`.
        
        :params prompt: The user's string.
        :return: Generates JSON strings.
        """
        # print("calling the tooluser", file=sys.stderr)        
        
        system_message = "Your job is to 1. think about what needs to be done, 2. dispatch tool calls, and 3. process and analyse the data produced by a tool call. Always start with a thought or reflection before using a tool. If the result is unsatisfying, explain what happened and try again. An iterative approach that takes small steps works best, especially when using the python tool. Never pass code to the python tool."
        with LocalDB() as db:
            db.create_table(sys_mess=False)
            db.insert_data("system", system_message)
            db.insert_data("user", prompt)
            self.messages = db.load_temp()
            
        print(self.messages, file=sys.stderr)
               
        try: 
            choice = self._request(self.messages).choices[0]              
            if choice.message.content: 
                yield json.dumps({"data": choice.message.content})  
                
                with LocalDB() as db: 
                    db.insert_data('assistant', choice.message.content)
                    
            elif choice.message.tool_calls and choice.finish_reason and 'tool_calls' in choice.finish_reason: 
                    yield from self._toolcall_nostream(choice)
            
            elif choice.finish_reason and choice.finish_reason not in ['tool_calls', 'stop']:
                raise Exception("Other choice.finish_reason:", choice.finish_reason)

        except Exception as e: 
            raise Exception(f"ToolUser: {e.args}")        

    def _tool_list(self, choice) -> list:
        arguments = name = tool_call_id = ""         
        tool_list = []         
        message = choice.message       
        for tool_call in message.tool_calls:    
            name = tool_call.function.name 
            arguments = tool_call.function.arguments 
            tool_call_id = tool_call.id           
            tool_list.append((name, arguments, tool_call_id))   
        return tool_list  
        
    def _toolcall_nostream(self, choice):
        """
        This processes the toolcalls.
        
        :params prompt: The model's choice object.
        :return: Generates JSON strings and returns them to interpreting_toolcall.
        """
        for (name, arguments, tool_call_id) in self._tool_list(choice):                    
            print(f"tool {name} with args {arguments} and tool_call_id {tool_call_id}", file=sys.stderr)                
            
            yield json.dumps({"data": f"\tCalling {name} with {arguments}\n"})
            try:
                if 'online_llm' in name:
                    online_llm = Online_llm()
                    data = online_llm.run(arguments)
                    if data:
                        yield from data
                        
                if "python_wizzard" in name: 
                    coder = Coder()
                    for coder_run in coder.run(query=arguments):
                        
                        if 'stream' in coder_run:
                            stream = coder_run.get('stream')
                            yield json.dumps({"stream": stream})  
                            
                        if 'result' in coder_run:
                            result = coder_run.get('result') 
                            yield json.dumps({"result": result})
                            
                        if 'code' in coder_run:
                            code = coder_run.get('code') 
                            yield json.dumps({"code": code})
                        
                        if 'data' in coder_run:
                            data_ = coder_run.get('data', '')
                            # yield json.dumps({"data": data_})                                
                            # print("data dump", data_, file=sys.stderr)                            
                            yield from self._interpreting_toolcall(tool_call_id, name, arguments, data_)
                    
                if name not in ['online_llm', "python_wizzard"]: 
                    raise Exception(f'The name of the function call is, {name}')
                
            except Exception as e:
                # if 'Error code' in e.args:
                yield from stream_chunks(f"There's an error with the tool call: {str(e.args[0])}") # e.args['error']['message'])
                # else: 
                raise Exception('Toolcall:', e.args)
                        
    def _interpreting_toolcall(self, tool_call_id, name:str, args:str, data:str) -> Generator[str, None, None]: 
        """
        :return: Generates JSON strings.
        """
        messages = self.messages
        messages += [{"role": "assistant", 
                      "content": 'null', 'tool_calls': [
                          {'id': tool_call_id, 'function': 
                              {"name": name,'arguments': str(args)}, 
                              'type': 'function'
                              }
                          ]
                      },
                     {"tool_call_id": tool_call_id, 
                      "role": "tool", "name": name, "content": data}]
        
        print('messages in interpreting_toolcall', messages, file=sys.stderr)
        
        completion_res = self._wrapper.client.chat.completions.create( # type: ignore
            model=self._wrapper.model, 
            # temperature=0,
            messages=messages, # type: ignore
            tools=self._tools,  # type: ignore
            max_tokens=2000
            )
        try:
            choice = completion_res.choices[0]
            content = choice.message.content
            if content:                
                yield json.dumps({"data": content})
                print("full_response interpreting_toolcall: ", content, file=sys.stderr)
                
            elif choice.message.tool_calls:     
                yield from self._toolcall_nostream(choice) # this creates the loop    
        
        except Exception as e:
            raise Exception(f"interpreting_toolcall returned an unexpected error.")
        
    def close(self):
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()
