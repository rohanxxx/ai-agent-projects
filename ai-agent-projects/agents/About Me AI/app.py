from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

import os, json, requests

import gradio as gradio

load_dotenv(override=True)

def push(text):
    requests.post("https://ntfy.sh/aboutmeai", data=text)

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

def get_current_datetime():
    return {"datetime": datetime.now().strftime("%B %d, %Y %H:%M")}

get_current_datetime_json = {
    "name": "get_current_datetime",
    "description": "Use this tool to get the current date and time, useful for calculating durations like how long ago something happened",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
}

def get_profile():
    with open("me/summary.txt", "r", encoding="utf-8") as f:
        return {"profile": f.read()}

get_profile_json = {
    "name": "get_profile",
    "description": "Use this tool to retrieve Md Fazle Rabbi's full profile including summary and LinkedIn data, use this to answer any questions about his background, experience, skills, and education",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
    {"type": "function", "function": get_current_datetime_json},
    {"type": "function", "function": get_profile_json}
]

class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Md Fazle Rabbi"

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name

            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            result = {}
            if hasattr(self, tool_name):
                result = getattr(self, tool_name)(**arguments)
            elif globals().get(tool_name):
                result = globals()[tool_name](**arguments)

            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You have NO knowledge about {self.name} stored in memory. The ONLY way to answer ANY question about {self.name} is by calling the get_profile tool first. \
For questions involving time or durations (e.g. how long ago, how many years), you must call BOTH get_profile AND get_current_datetime together before responding. \
Never say you don't know or can't provide information — always call the relevant tools first before responding. \
Be professional and engaging, as if talking to a potential client, recruiter, or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. \
Always stay in character as {self.name}. \
Do not end every response with phrases like 'feel free to ask' or 'if you have any other questions'. Keep responses concise and natural."

        return system_prompt


    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        
        done = False
        
        while done == False:
            
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                
                tool_calls = message.tool_calls
                
                results = self.handle_tool_call(tool_calls)
                
                messages.append(message)
                messages.extend(results)
            else: # .finish_reason = "stop"
                done = True
        
        return response.choices[0].message.content
    

if __name__ == "__main__":
    me = Me()

    with gradio.Blocks(js="() => { document.querySelector('body').classList.add('dark'); }") as demo:
        with gradio.Row(equal_height=True):
            gradio.Image(
                value="me/linkedlnProfilePicture.png",
                show_label=False,
                show_download_button=False,
                show_fullscreen_button=False,
                container=False,
                width=150,
                height=150,
            )
            gradio.Markdown("""
                ## Md Fazle Rabbi
                **AI & SWE Enthusiast**
                
                Welcome! My AI assistant is here to answer any questions about my background, experience, and skills. 
                Feel free to ask anything!
                If you'd like to get in touch, simply leave your email and a note in the chat — I'll reach out to you as soon as possible.
                """
            )
        gradio.ChatInterface(
            me.chat,
            type="messages",
            chatbot=gradio.Chatbot(
                type="messages",
                height=500
            )
        )

    demo.launch()