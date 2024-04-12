from typing import List, Generator, Literal, Dict, Iterable
import os, json, sys, io
from util import logger
from abc import ABC, abstractmethod
from localDb import LocalDB
from ._base import Wrapper

online_llm = {
    "type": "function",
    "function":
    {
        "name": "online_llm",
        "description": "Use this function to search the internet.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Pass the entire string here, in the user's language."
                },
            },
            "required": ["search_term"]
        }
    }
}
python_wizzard = {
    "type": "function",
    "function":
    {
        "name": "python_wizzard",
        "description": "Use this function to calculate, find the date and time, and reason logically more generally.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pass a clear and concise instruction on how to approach the solution."
                },
            },
            "required": ["query"]
        }
    }
}

tools_json = [online_llm, python_wizzard]

class BaseTool(ABC):
    @abstractmethod
    def __init__(self):
        pass
    # def request(self):
    #     pass
    @abstractmethod
    def run(self):
        pass
    # def close(self):
    #     pass
        
class Online_llm(BaseTool):
    def __init__(self):
        self._wrapper = Wrapper("sonar-medium-online")
        
    def _request(self, search_term):
        self._pp_response = self._wrapper.client.chat.completions.create(
            model=self._wrapper.model,
            messages=[{"role": "user", "content": search_term + "\n\n**Note:** \n- The user is located in London, UK. \n- They use the metric system and Celcius for temperature. \n- **Always cite sources in your answer.**"}],
            stream=True,
            )
        
    def run(self, search_term) -> Generator[str, None, None]:
        try:
            full_response = ''
            self._request(search_term)
            for response in self._pp_response:
                content_chunk = response.choices[0].delta.content or ''
                full_response += content_chunk
                yield json.dumps({"data": content_chunk})                 
            
            with LocalDB() as db:
                db.insert_data('assistant', full_response)
                
        except Exception as e:
            raise Exception(f"interpreting_data returned an unexpected error.", e.with_traceback)
    
    def close(self):
        """Close the connection."""
        if getattr(self, '_pp_response', None) is not None: 
            self._pp_response.close()      

class Coder(BaseTool):    
    def __init__(self):
        self._wrapper = Wrapper('mixtral-8x7b-32768')
        self.analyser_system_message = """
        Write some python code to solve the user's problem. 
        Return only python code in the following Markdown format, e.g.:
        ```python
        ....
        ```
        """        
        
    def _sanitize_output(self, text: str):
        codelist = text.split("```python")
        return codelist[1].split("```")[0]
    
    def _sanitize_streaming_output(self, text) -> Generator[str, None, None]:
        raise NotImplemented
        try:
            full_t = new_t = ''  
            in_code_block= False      
            for t in text:
                full_t += t
                if "```python" in full_t:
                    in_code_block = True
                    new_t = full_t[full_t.find("```python"):]                
                elif in_code_block:
                    new_t += t
                    yield t 
                                    
                    if "```" in new_t and new_t.count("```") > 1:                
                        new_t = ''
                        in_code_block = False
        except Exception as e:
            raise Exception('_sanitize_streaming_output',e.args)            

    def _format_result(self, code, json_output):
        """to feed the results back into the model"""
        return f"""
    **You wrote the following code:**
    
    ```python
    {code}
    ```
    
    **Producing the following result:**
    
    ```json
    {json_output}
    ```
    """     

    def run(self, query) -> Generator[Dict[str, str], None, None]: 
        response = self._wrapper.client.chat.completions.create(
            model=self._wrapper.model,  
            messages=[{"role":"system","content": self.analyser_system_message},
                    {"role":"user","content": query}],
            temperature=0, 
            stream=True)
        
        try:
            full_code = ''
            for res in response:
                content_chunk = res.choices[0].delta.content or ''
                full_code += content_chunk
                # clean_code = self._sanitize_streaming_output(content_chunk)
                yield {'stream': content_chunk}
    
            code = self._sanitize_output(full_code) 
            
            try:
                output_buffer = io.StringIO()
                current_stdout = sys.stdout
                sys.stdout = output_buffer
                exec(code)
                
                output = output_buffer.getvalue()
            finally:
                sys.stdout = current_stdout
                
            yield {'code': "```python" + code + "\n```\n"}    
            yield {'result': "\t Raw output: " + output + "\n"}            
            yield {'data': self._format_result(code, output)} 
            
    
        except Exception as e:
            raise Exception("Coder.run ran into:", e.args)

    # def generate_embedding(text: str) -> list[float]:    
    #     resp = openai_client.embeddings.create(
    # 		input=text, 
    # 		model="text-embedding-ada-002")
    #     return resp.data[0].embedding
    #
    # def similarity_search(search_term, results = 3):
    #     pass
    #     """This is the function called by the LLM"""
    #     df = get_df() 
    #     embeddings = df.embeddings.tolist()
    #     user_text_embedding = generate_embedding(search_term)
    #     cosine_similarities = cosine_similarity(np.array([user_text_embedding]), embeddings)
    #     df['similarity'] = cosine_similarities.flatten()
    #     df_sim = df.sort_values(by='similarity', ascending=False)
        
    #     print("This is the number of similarity_search results: ", len(df_sim))
    #     if len(df_sim) > 0:
    #         # get scores and texts
    #         scores = df_sim[df_sim['similarity'] >= 0.8]['similarity'].tolist()
    #         texts = df_sim[df_sim['similarity'] >= 0.8]['texts'].iloc[:7]
    #         # combine them to present them as strings
    #         text_scores = [text + f"(cosine similarity: {str(round(f,3))})" for text, f in zip(texts, scores)]
    #         df_string = "- " + '\n- '.join(text_scores)[:5000]
    #         print(f"These are the search results: \n", df_string)
    #         return df_string
    #     else: 
    #         return "No results came back from the tool call"

# if __name__ == "__main__":