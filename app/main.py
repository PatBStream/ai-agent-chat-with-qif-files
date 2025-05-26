# app/main.py
import os
import re
import requests
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from app.qif_indexer import QIFIndexer

class Query(BaseModel):
    question: str

app = FastAPI()

# Setup
qif_dir = os.getenv("QIF_DIR", "/qifs")
vectorstore_dir = os.getenv("VECTORSTORE_DIR", "/vectorstore")
ollama_url = os.getenv("OLLAMA_URL")

indexer = QIFIndexer(qif_dir, vectorstore_dir)
if not os.path.isdir(vectorstore_dir) or not os.listdir(vectorstore_dir):
    indexer.build_index()
vectorstore = indexer.load_index()

df = indexer.load_dataframe()

# Ollama LLM via base_url
llm = Ollama(model="phi4-mini:3.8b", base_url=ollama_url)
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=vectorstore.as_retriever())

@app.post("/chat")
async def chat(query: Query):
    q = query.question.lower()
    # Pattern: spent on X in YEAR
    m = re.search(r"spent on ([\w\s]+) in (\d{4})", q)
    if m:
        cat = m.group(1).strip().title()
        year = int(m.group(2))
        mask = (df['category'] == cat) & (df['date'].dt.year == year)
        total = df.loc[mask, 'amount'].sum()
        return {"answer": f"Total spent on {cat} in {year}: ${total:,.2f}"}
    # fallback to LLM
    try:
        ans = qa.run(query.question)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    try:
        r = requests.get(f"{ollama_url}/v1/models")
        r.raise_for_status()
        return {"status":"ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/chat")
async def chat_get():
    return {"message": "POST JSON { 'question': '...' }"}
