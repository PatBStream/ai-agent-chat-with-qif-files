# ---------------------------
# app/main.py
# ---------------------------
import os
import requests
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_experimental.sql import SQLDatabaseChain
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama
from sqlalchemy import text
from app.qif_indexer import QIFIndexer

# Configure logging
default_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, default_level))
logger = logging.getLogger(__name__)

# Environment variables
qif_dir = os.getenv('QIF_DIR', '/qifs')
db_path = os.getenv('DB_PATH', '/db/transactions.db')
ollama_url = os.getenv('OLLAMA_URL')

import re
from langchain_experimental.sql import SQLDatabaseChain

class PatchedSQLDatabaseChain(SQLDatabaseChain):
    def _call(self, inputs, run_manager=None):
        # Use the standard _call logic, but patch SQL execution
        response = super()._call(inputs, run_manager=run_manager)
        if 'result' in response and isinstance(response['result'], str):
            # Clean any triple-backtick code fences
            cleaned = re.sub(r'```sql\\s*', '', response['result'], flags=re.IGNORECASE)
            cleaned = re.sub(r'```', '', cleaned)
            response['result'] = cleaned.strip()
        return response

# Create FastAPI app
app = FastAPI()

# Ensure database
indexer = QIFIndexer(qif_dir, db_path)
indexer.ensure_database()
logger.info(f"Database ready at {db_path}")

# Setup LLM + SQL chain
db_uri = f"sqlite:///{db_path}"
db = SQLDatabase.from_uri(db_uri)
llm = Ollama(model="phi4-mini:3.8b", base_url=ollama_url)
sql_chain = PatchedSQLDatabaseChain.from_llm(llm, db, verbose=True)
logger.info("SQLDatabaseChain initialized")

class Query(BaseModel):
    question: str

@app.post('/chat')
async def chat(query: Query):
    try:
        answer = sql_chain.run(query.question)
        logger.info(f"/chat answered question: {query.question}")
        return {'answer': answer}
    except Exception as e:
        logger.exception("SQL chain error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/transactions/{year}')
async def list_transactions(year: int):
    try:
        conn = indexer.engine.connect()
        q = text(
            "SELECT date, payee, category, memo, amount "
            "FROM transactions WHERE strftime('%Y', date)=:yr"
        )
        res = conn.execute(q, {"yr": f"{year}"})
        logger.info(f"Listing transactions for year {year}")
        if res.rowcount == 0:
            logger.warning(f"No transactions found for year {year}")
            return {'transactions': []}
        # Convert result to list of dicts
        res = res.fetchall()
        if not res:
            logger.warning(f"No transactions found for year {year}")
            return {'transactions': []}
        # Format results
        logger.info(f"Found {len(res)} transactions for year {year}")
        rows = []
        for row in res:
            r = dict(row._mapping)
            date_val = r.get('date')
            if hasattr(date_val, 'isoformat'):
                r['date'] = date_val.isoformat()
            else:
                r['date'] = str(date_val) if date_val else None
#            r['date'] = r['date'].isoformat() if r['date'] else None
            r['amount'] = f"${r['amount']:,.2f}" if r['amount'] is not None else None
            rows.append(r)
        conn.close()
        logger.info(f"Returned {len(rows)} transactions for year {year}")
        return {'transactions': rows}
    except Exception as e:
        logger.exception("Transaction listing error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/health')
def health_check():
    try:
        r = requests.get(f"{ollama_url}/v1/models")
        r.raise_for_status()
        logger.info("Health check OK")
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get('/chat')
def chat_get():
    return {'message': "Please POST JSON {'question':'...'} to this endpoint."}

@app.get('/count')
async def count_transactions():
    """Return total number of transactions in the database."""
    try:
        conn = indexer.engine.connect()
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM transactions"))
        row = result.fetchone()
        count = row[0] if row is not None else 0
        conn.close()
        logger.info(f"Total transactions count: {count}")
        return {'count': count}
    except Exception as e:
        logger.exception("Error counting transactions")
        raise HTTPException(status_code=500, detail=str(e))
    
    # New endpoint: count transactions for a given year
@app.get('/transactions/count/{year}')
async def count_transactions_year(year: int):
    """Return the number of transactions for the specified year."""
    try:
        conn = indexer.engine.connect()
        result = conn.execute(text(
            "SELECT COUNT(*) FROM transactions "
            "WHERE strftime('%Y', date)=:yr"
        ), {"yr": f"{year}"})
        row = result.fetchone()
        count = row[0] if row is not None else 0
        conn.close()
        logger.info(f"Transactions count for {year}: {count}")
        return {'year': year, 'count': count}
    except Exception as e:
        logger.exception(f"Error counting transactions for year {year}")
        raise HTTPException(status_code=500, detail=str(e))


