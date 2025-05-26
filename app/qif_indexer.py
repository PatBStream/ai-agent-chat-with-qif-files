# app/qif_indexer.py
import os
from qifparse.parser import QifParser
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import FAISS

class QIFIndexer:
    def __init__(self, qif_dir, vectorstore_dir):
        self.qif_dir = qif_dir
        self.vectorstore_dir = vectorstore_dir
        self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

    def load_transactions(self):
        """Returns list of tuples (text, metadata dict) for embedding."""
        transactions = []
        for fname in os.listdir(self.qif_dir):
            if not fname.lower().endswith('.qif'):
                continue
            with open(os.path.join(self.qif_dir, fname), 'r', encoding='utf-8', errors='ignore') as f:
                lines = [l.strip() for l in f if l.strip()]
            current = {}
            for line in lines:
                if line == '^':
                    meta = {
                        'date': current.get('date',''),
                        'payee': current.get('payee',''),
                        'category': current.get('category',''),
                        'memo': current.get('memo',''),
                        'amount': float(current.get('amount','0').replace(',',''))
                    }
                    text = f"{meta['date']} {meta['payee']} {meta['category']} {meta['memo']} {meta['amount']}"
                    transactions.append((text, meta))
                    current = {}
                else:
                    key, val = line[0], line[1:]
                    if key == 'D': current['date'] = val
                    elif key == 'P': current['payee'] = val
                    elif key == 'L': current['category'] = val
                    elif key == 'M': current['memo'] = val
                    elif key == 'T': current['amount'] = val
            # final txn
            if current:
                meta = {
                    'date': current.get('date',''),
                    'payee': current.get('payee',''),
                    'category': current.get('category',''),
                    'memo': current.get('memo',''),
                    'amount': float(current.get('amount','0').replace(',',''))
                }
                text = f"{meta['date']} {meta['payee']} {meta['category']} {meta['memo']} {meta['amount']}"
                transactions.append((text, meta))
        return transactions

    def build_index(self):
        trans = self.load_transactions()
        if not trans:
            raise RuntimeError("No transactions found.")
        docs, metas = zip(*trans)
        db = FAISS.from_texts(docs, self.embeddings, metas)
        db.save_local(self.vectorstore_dir)
        return db

    def load_index(self):
        return FAISS.load_local(
            self.vectorstore_dir,
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    def load_dataframe(self):
        """Return all transactions as pandas DataFrame."""
        import pandas as pd
        records = [meta for _, meta in self.load_transactions()]
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df