import pandas as pd
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer

from extensions import db
from models import Translation
from app import create_app

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Download NLTK resources (run once)
nltk.download("punkt")
nltk.download("punkt_tab")

ps = PorterStemmer()

def clean_and_tokenize(text):
    if pd.isnull(text):
        return ""

    # Lowercase
    text = str(text).lower()

    # Remove unwanted characters
    text = re.sub(r"[^a-zA-Z\u00C0-\u017F\s']", " ", text)

    # Tokenize
    tokens = word_tokenize(text)

    # Stem (reduce to root form)
    stems = [ps.stem(w) for w in tokens]

    return " ".join(stems)

app = create_app()

with app.app_context():
    df = pd.read_csv("data/corpus.csv")

    # Apply cleaning + tokenization
    df["isizulu"] = df["isizulu"].apply(clean_and_tokenize)
    df["english"] = df["english"].apply(clean_and_tokenize)

    # Example: Bag of Words on English corpus
    vectorizer = CountVectorizer()
    bow_matrix = vectorizer.fit_transform(df["english"])
    print("✅ Bag of Words vocabulary size:", len(vectorizer.vocabulary_))

    # Insert into DB
    for _, row in df.iterrows():
        if row["isizulu"] and row["english"]:
            entry = Translation(
                isizulu_text=row["isizulu"],
                english_text=row["english"]
            )
            db.session.add(entry)

    db.session.commit()
    print("✅ Corpus cleaned, tokenized, and imported into DB")

