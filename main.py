from fastapi import FastAPI  , File , UploadFile
from supabase import Client, create_client
from openai import OpenAI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import re
import os
from dotenv import load_dotenv


load_dotenv()

class Data(BaseModel):
    question: str
    response : str
    like: bool


class DataFeedback(BaseModel):
    question: str
    response : str
    like: bool
    correct_answer:str
url = os.getenv("url")
api_key = os.getenv("api_key")
openai_api_key =os.getenv("openai_api_key")

supabase: Client = create_client(url, api_key)


client = OpenAI(api_key=openai_api_key)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def ask(chat_history: str , number:str):
    system_prompt = """
        You are an expert real estate assistant. Your task is to analyze a conversation between a user and a chatbot.
        From the chat history, generate a JSON report containing the following fields:
        1. user_intent: Describe the property or type of real estate the user is interested in.
        2. user_mood: Indicate if the user seems happy, frustrated, or neutral.
        3. probability_to_buy: Estimate a percentage probability (0-100%) that the user will buy a property, based on the conversation.
        Always base your answers only on the provided chat history. Return the output strictly in JSON format.
        """

    user_prompt = f"""
            Here is the chat history:

                {chat_history}
            """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    print(res.choices[0].message.content)


@app.get("/")
def hello():
    return "hello"


@app.get("/chats")
def chats(num: str):
    response = supabase.table("whatsapp_chat").select("*").execute()

    grouped = {}
    for chat in response.data:
        number = chat["number"]
        if number not in grouped:
            grouped[number] = []
        grouped[number].append(chat)

    for i in grouped.keys():
        ask(grouped[i] , i)
    return grouped[num]


@app.post("/like")
def handel_like(data :Data):
    res =  supabase.table("testing").insert({"question":data.question,"response":data.response,"like":True}).execute()
    return {"status": "ok", "data": res.data}


@app.post("/dislike")
def handel_like(data: DataFeedback):
    res = (
        supabase.table("testing")
        .insert({"question": data.question, "response": data.response, "like": False , "corrected_response":data.correct_answer})
        .execute()
    )
    return {"status": "ok", "data": res.data}


def chunking(text:str , size:int = 500, overlab:int = 100):
    start = 0
    chunks=[]
    while start < len(text):
        end = start+size
        chunk = text[start:end]
        chunks.append(chunk)
        start = start +size - overlab

        supabase.table("chunks").insert({"chunk": chunk , "size":len(chunk)}).execute()

    return chunks


@app.post("/upload")
async def upload(file: UploadFile = File(...), timestamp=File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    print(text)

    
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,!?;:\s]", " ", text)
    text = re.sub(r"\s+", " ", text)


    chunks = chunking(text , 500 , 100)

    print({"length": len(chunks), "first chunk": chunks[0], "last chunk": chunks[-1]})
    return {"length": len(chunks), "first chunk": chunks[0]}
