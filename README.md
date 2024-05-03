# *`__SuperModels`*

SuperModels is an open-source project for running LLM agents in a user-friendly desktop app.

![Not a llama](examples/output.gif)

Give it a try! [Download the executable here!](https://storage.googleapis.com/supermodels/SuperModels-1.0.0%20Setup.zip)

## *purpose*: 

`A self-reflecting machine:` 

- Think Wittgenstein not Frankenstein
- Built-in reflection mechanism to steer *thinking*
- Fully customisable

*__in short*
`A lightweight, simple, and easy to adapt Agent.`

Stack: `Python`, `Electronjs`, and `TailwindCSS`.

---

## *walk-through:*

#### 1. SuperModel
- I implemented a series of powerful LLM APIs for you to play with.
- Most notably, [Groq](https://groq.com/) which is faster than any other LLM. 

#### 2. ToolUser
The tools are basic but performant:
- The `python_wizzard` generates and executes Python on your system. 
  *Note that running generated code is not without risk. - Be prepared for SuperModels to take control over your OS and start operating your home automation.*
- A second tool, `online_llm` uses Perplexity AI under the hood for natural language web results. 

#### 3. Agent
The **real magic** happens [here](https://github.com/JohannesVC/supermodels/tree/master/python/dispatch/_agent) (click for source code): 

1. This is where the agent breaks down complex problems into steps:
```python
self._break_down = BreakdownReflection(prompt, model=self._model)
...
```
2. Every step is then passed to the tooluser:
```python
for step in break_down_call.steps:
    self._answer = self._tooluser.call(step)
```
3. The tooluser's answer is fed back into the model:
```python
new_prompt = "Let's take a moment to consider."
            + "We just tried to answer: \n"
            + step + "\n\n"
            + "This as part of: \n"
            + f"- {"\n- ".join(step for step in break_down_call.steps)} \n\n"
            + f"This to answer the original question: {prompt}."
```
4. The agent is then forced into a yes or no reflection:
```python
self._should_continue = YesNoReflection(new_prompt, self._answer, model=self._model)
```
5. The output can is then again forced into this shape:
```python
if reflection.userInputRequired:
    ...
elif reflection.answer: 
    ...
```
In short: `The combination of a super fast tooluser and nominally typed answers allows for quite impressive reflections and reasoning.` Although I still haven't got it to turn the lights off.

---

## *instructions*

Give it a try! [Download the executable here!](https://drive.google.com/file/d/1-Gxk9jkKhGLpx7jq6kFIVsU9OTPjgDfv/view?usp=sharing) (Note that you may get malware warnings.)

Then:

- Join the FREE beta at [groq.com](https://groq.com/) to get a free API KEY 
- Input the API key when the app prompts you
