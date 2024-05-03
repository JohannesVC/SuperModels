import json, time, os, sys
from localDb import LocalDB, Message
from typing import Generator
from groq._types import NOT_GIVEN
from ._base import BaseLLM, Wrapper, stream_chunks
from ._tools import tools_json, Online_llm, Coder

class ToolUser(BaseLLM):
    def __init__(self, model=None):
        self._wrapper = Wrapper(model) if model else Wrapper()   
        print('model passed to ToolUser:', self._wrapper.model, file=sys.stderr) 
        self._tools = tools_json if tools_json else NOT_GIVEN
        self._online_llm = Online_llm()
        self._coder = Coder()

    def _request(self, messages):   
        return self._wrapper.client.chat.completions.create(model=self._wrapper.model, 
                                            messages=messages, # type:ignore
                                            stream=True, 
                                            tools=self._tools, # type: ignore
                                            max_tokens=1000, 
                                            # tool_choice={"type": "function", "function": {"name": "python_wizzard"}}
                                            )
        
    def call(self, prompt:str) -> Generator[str, None, None]: 
        """
        This to stream the tooluser.
        
        Uses the BreakDownInSteps schema to force the model into steps.
        :params prompt: The user's string.
        :return: Generates JSON strings.
        """
        # print("calling the tooluser", file=sys.stderr)
        tool_list = []
        full_response = self.arguments = self.name = self.tool_call_id = ''        
        system_message = "Your job is to 1. dispatch tool calls, and 2. process and analyse the data produced by a tool call. If the result is unsatisfying, explain what happened and try again. An iterative approach that takes small steps works best, especially when using the python tool."
        
        with LocalDB() as db:
            db.create_table(sys_mess=False)
            db.insert_data("system", system_message)
            db.insert_data("user", prompt)
            self.messages = db.load_temp()
               
        try:
            for res in self._request(self.messages):  
                choice = res.choices[0]      
                delta = choice.delta
                if delta.content: 
                    content_chunk = delta.content
                    full_response += content_chunk
                    yield json.dumps({"data": content_chunk})  
                                
                elif delta.tool_calls:                     
                    # this needs to loop over tool calls and collect args etc for each                    
                    # tools = delta.tool_calls
                    # print(f"tools", tools, file=sys.stderr) 
                    old_index = 0  
                    for tool_call in delta.tool_calls:                            
                        index = tool_call.index                        
                        if index != old_index: 
                            print("ToolUser tried using more than one tool in this run.", file=sys.stderr) 
                            break
                            # tool_list.extend((name, arguments, tool_call_id))
                            # name, arguments, tool_call_id = '','',''                            
                            # old_index = index     
                        self.name += tool_call.function.name or ''
                        self.arguments += tool_call.function.arguments or ''
                        self.tool_call_id += tool_call.id or '' 
                        
            if choice.finish_reason and 'tool_calls' in choice.finish_reason:            
                # for (name, arguments, tool_call_id) in tool_list:                
                print(f"tool {index} {self.name} with args {self.arguments} and tool_call_id {self.tool_call_id}", file=sys.stderr)
                yield from self.toolcall()
                    
            elif choice.finish_reason and choice.finish_reason not in ['tool_calls', 'stop']:
                raise Exception("Other choice.finish_reason:", choice.finish_reason)
                
            if full_response: 
                with LocalDB() as db: 
                    db.insert_data('assistant', full_response)

        except Exception as e: 
            raise Exception(f"ToolUser: {e.args}")
                
    def toolcall(self):
        """
        Implementing the streaming version is tricky as it requires accumulating the chunks of name, arguments, id. 
        """
        print('tool_call in tool call', file=sys.stderr)
        yield json.dumps({"data": f"\tCalling {self.name} with {self.arguments}\n"})
        try:
            if 'online_llm' in self.name:
                data = self._online_llm.run(self.arguments)
                
                if data:
                    yield from data
                    
            if "python_wizzard" in self.name:
                for coder_run in self._coder.run(query=self.arguments):
                    
                    # if 'stream' in coder_run:
                    #     stream = coder_run.get('stream')
                    #     yield json.dumps({"stream": stream})  
                        
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
                        
                        yield from self.interpreting_toolcall(self.tool_call_id, self.name, self.arguments, data_)
                
            elif self.name not in ['online_llm', "python_wizzard"]: 
                raise Exception(f'The name of the function call is, {self.name}')

        except Exception as e:
            # if 'Error code' in e.args:
            yield from stream_chunks(f"There's an error with the tool call: {str(e.args)}") # e.args['error']['message'])
            # else: 
            raise Exception('Toolcall:', e.args)
        
    def interpreting_toolcall(self, tool_call_id, name:str, args:str, data:str) -> Generator[str, None, None]: 
        """
        :return: Generates JSON strings.
        """
        self.arguments = self.name = self.tool_call_id = full_response = ''
        
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
        
        # print('messages in interpreting_toolcall', messages, file=sys.stderr)
        
        completion_res = self._wrapper.client.chat.completions.create(
            model=self._wrapper.model, 
            # temperature=0,
            messages=messages, # type: ignore
            stream=True, # groq doesn't support streaming
            tools=self._tools,  # type: ignore
            max_tokens=1000)
        try:            
            for res in completion_res:
                choice = res.choices[0]
                delta = choice.delta
                content_chunk = delta.content
                if content_chunk:
                    full_response += content_chunk
                    # print(f"'data' chunk in interpreting_toolcall", content_chunk, file=sys.stderr)
                    yield json.dumps({"data": content_chunk})
                
                elif delta.tool_calls:                    
                    # this needs to loop over tool calls and collect args etc for each                    
                    # tools = delta.tool_calls
                    # print(f"tools", tools, file=sys.stderr) 
                    old_index = 0                    
                    try:            
                        for tool_call in choice.delta.tool_calls:
                            index = tool_call.index                        
                            if index != old_index: 
                                print("ToolUser tried using more than one tool in this run.", file=sys.stderr) 
                                break
                                # tool_list.extend((name, arguments, tool_call_id))
                                # name, arguments, tool_call_id = '','',''                            
                                # old_index = index     
                            self.name += tool_call.function.name or ''
                            self.arguments += tool_call.function.arguments or ''
                            self.tool_call_id += tool_call.id or '' 
                    
                    except Exception as e:
                        raise Exception("interpreting_toolcall toolcall completion", e.args)
                        
            if choice.finish_reason and 'tool_calls' in choice.finish_reason:            
                # for (name, arguments, tool_call_id) in tool_list:                
                print(f"tool {index} {self.name} with args {self.arguments} and tool_call_id {self.tool_call_id}", file=sys.stderr)
                yield from self.toolcall()
                
            elif choice.finish_reason and choice.finish_reason not in ['tool_calls', 'stop']:
                raise Exception("Other choice.finish_reason:", choice.finish_reason)
            
            if full_response:
                print("full_response interpreting_toolcall: ", full_response, file=sys.stderr)
        
        except Exception as e:
            raise Exception(f"interpreting_toolcall returned an unexpected error.", e.args)
        
    def close(self):
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()
