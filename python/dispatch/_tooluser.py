import json, time, os, sys
from localDb import LocalDB, Message
from typing import Generator
from groq._types import NOT_GIVEN
from ._base import BaseLLM, Wrapper
from ._tools import tools_json, Online_llm, Coder

class ToolUserNoStream(BaseLLM):
    """The non streaming ToolUser"""
    def __init__(self, model=None):        
        self._wrapper = Wrapper(model=model) if model else Wrapper() 
        print('model passed to ToolUserNoStream:', self._wrapper.model, file=sys.stderr)
        self._tools = tools_json
        
    def _request(self, messages):   
        return self._wrapper.client.chat.completions.create(model=self._wrapper.model, 
                                            messages=messages, # type:ignore                                            
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
        
        arguments = name = tool_call_id = ""         
        # system_message = "Your job is to 1. dispatch tool calls, and 2. process and analyse the data produced by a tool call."
        with LocalDB() as db:
            db.create_table()
            # db.insert_data("system", system_message)
            db.insert_data("user", prompt)
            self.messages = db.load_temp()
            
        print(self.messages, file=sys.stderr)
               
        try:                                  
            res = self._request(self.messages)  
            
            message = res.choices[0].message
            if message.content: 
                yield json.dumps({"data": message.content})  
              
            elif message.tool_calls:          
                tool_list = []         
                for tool_call in message.tool_calls:    
                    name = tool_call.function.name or ''
                    arguments = tool_call.function.arguments or ''
                    tool_call_id = tool_call.id or ''
                    
                    tool_list.append((name, arguments, tool_call_id))
                    
            choice = res.choices[0]        
            if choice.finish_reason and 'tool_calls' in choice.finish_reason:                
                for (name, arguments, tool_call_id) in tool_list:                    
                    # print(f"tool {index} {name} with args {arguments} and tool_call_id {tool_call_id}", file=sys.stderr)                
                    yield json.dumps({"data": f"\tCalling {name} with {arguments}\n"})
                    
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
                                
                                yield from self.interpreting_toolcall(tool_call_id, name, arguments, data_)
                        
                    if name not in ['online_llm', "python_wizzard"]: 
                        raise Exception(f'The name of the function call is, {name}')
            
            elif choice.finish_reason and 'tool_calls' not in choice.finish_reason:
                print("Other choice.finish_reason:", choice.finish_reason, file=sys.stderr)

            if message.content:
                with LocalDB() as db: 
                    db.insert_data('assistant', message.content)

        except Exception as e: 
            raise Exception(f"ToolUser: {e.args}")        


    def interpreting_toolcall(self, tool_call_id, name:str, args:str, data:str) -> Generator[str, None, None]: 
        """
        :return: Generates JSON strings.
        """
        full_response = ''
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
            # stream=True, # groq doesn't support streaming
            tools=self._tools,  # type: ignore
            max_tokens=1000)
        try:
            content = completion_res.choices[0].message.content
            if content:                
                yield json.dumps({"data": content})
                           
            print("full_response interpreting_toolcall: ", full_response, file=sys.stderr)
        
        except Exception as e:
            raise Exception(f"interpreting_toolcall returned an unexpected error.")
        
    def close(self):
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()


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
        
        full_response = arguments = name = tool_call_id = "" 
        tool_list = []
        # system_message = "You are a helpful assistant. It is your responsibility to 1. dispatch tool calls, and 2. process and analyse the data produced by a tool call."
        with LocalDB() as db:
            db.create_table()
            db.insert_data("user", prompt)
            self.messages = db.load_temp()
        # self.messages = [{"role": "system", "content": system_message}, 
                        # {"role": "user", "content": prompt}]
               
        try:                                  
            for res in self._request(self.messages):       
                delta = res.choices[0].delta
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
                        name += tool_call.function.name or ''
                        arguments += tool_call.function.arguments or ''
                        tool_call_id += tool_call.id or ''                        
                     
                choice = res.choices[0]        
                if choice.finish_reason and 'tool_calls' in choice.finish_reason:
                    
                    # for (name, arguments, tool_call_id) in tool_list:
                        
                    # print(f"tool {index} {name} with args {arguments} and tool_call_id {tool_call_id}", file=sys.stderr)                
                
                    yield json.dumps({"data": f"\tCalling {name} with {arguments}\n"})
                    
                    if 'online_llm' in name:
                        data = self._online_llm.run(arguments)
                        
                        if data:
                            yield from data
                            
                    if "python_wizzard" in name: 
                        for coder_run in self._coder.run(query=arguments):
                            
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
                                
                                yield from self.interpreting_toolcall(tool_call_id, name, arguments, data_)
                        
                    if name not in ['online_llm', "python_wizzard"]: 
                        raise Exception(f'The name of the function call is, {name}')
                
                elif choice.finish_reason and 'tool_calls' not in choice.finish_reason:
                    print("Other choice.finish_reason:", choice.finish_reason, file=sys.stderr)

            if full_response: 
                with LocalDB() as db: 
                    db.insert_data('assistant', full_response)

        except Exception as e: 
            raise Exception(f"ToolUser: {e.args}")        


    def interpreting_toolcall(self, tool_call_id, name:str, args:str, data:str) -> Generator[str, None, None]: 
        """
        :return: Generates JSON strings.
        """
        full_response = ''
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
                content_chunk = res.choices[0].delta.content
                if content_chunk:
                    full_response += content_chunk
                    # print(f"'data' chunk in interpreting_toolcall", content_chunk, file=sys.stderr)
                    yield json.dumps({"data": content_chunk})
                           
            print("full_response interpreting_toolcall: ", full_response, file=sys.stderr)
        
        except Exception as e:
            raise Exception(f"interpreting_toolcall returned an unexpected error.")
        
    def close(self):
        """Close the connection.""" 
        if hasattr(self, '_wrapper') and getattr(self._wrapper, 'client', None) is not None:
            self._wrapper.client.close()