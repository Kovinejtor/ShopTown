from xgboost import XGBRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from app.core.databse import dynamodb
import pandas as pd
import numpy as np
import joblib

def load_products():
    table = dynamodb.Table("Products")
    response = table.scan()
    return pd.DataFrame(response.get("Items", []))

def load_reviews():
    table = dynamodb.Table("Reviews")
    response = table.scan()
    return pd.DataFrame(response.get("Items", []))

def build_training_data():
    products_df = load_products()
    reviews_df = load_reviews()

    if products_df.empty or reviews_df.empty:
        return None, None
    merged = pd.merge(reviews_df, products_df, left_on="product_id", right_on="id", how="inner")

    merged["price"] = merged["price"].astype(float)
    merged["rating"] = merged["rating"].astype(float)

    seller_le = LabelEncoder()
    merged["seller_encoded"] = seller_le.fit_transform(merged["seller_id"].astype(str))

    merged["text"] = merged["name"].fillna('') + " " + merged["description"].fillna('')
    tfidf = TfidfVectorizer(max_features=50, stop_words="english")
    tfidf_matrix = tfidf.fit_transform(merged["text"]).toarray()

    X = pd.concat([
        merged[["price", "seller_encoded"]].reset_index(drop=True),
        pd.DataFrame(tfidf_matrix)
    ], axis=1)

    y = merged["rating"]

    joblib.dump(seller_le, "model_data/seller_encoder.pkl")
    joblib.dump(tfidf, "model_data/tfidf.pkl")

    return X, y

def train_gradient_boost_model():
    X, y = build_training_data()
    if X is None:
        return None

    model = XGBRegressor()
    model.fit(X, y)
    model.save_model("model_data/gb_model.json")
    return model

def get_gb_recommendations(user_id: str, top_n=5):
    model = XGBRegressor()
    model.load_model("model_data/gb_model.json")
    seller_le = joblib.load("model_data/seller_encoder.pkl")
    tfidf = joblib.load("model_data/tfidf.pkl")

    products_df = load_products()
    reviews_df = load_reviews()

    if products_df.empty:
        return []

    rated_products = reviews_df[reviews_df["user_id"] == user_id]["product_id"].tolist()
    candidate_df = products_df[~products_df["id"].isin(rated_products)].copy()

    if candidate_df.empty:
        return []

    candidate_df["price"] = candidate_df["price"].astype(float)
    
    seller_classes = seller_le.classes_
    seller_map = {cls: idx for idx, cls in enumerate(seller_classes)}
    candidate_df["seller_encoded"] = candidate_df["seller_id"].apply(
        lambda x: seller_map.get(str(x), -1)  
    )

    candidate_df = candidate_df[candidate_df["seller_encoded"] != -1]
    if candidate_df.empty:
        return []

    candidate_df["text"] = candidate_df["name"].fillna('') + " " + candidate_df["description"].fillna('')
    tfidf_matrix = tfidf.transform(candidate_df["text"]).toarray()

    X_pred = pd.concat([
        candidate_df[["price", "seller_encoded"]].reset_index(drop=True),
        pd.DataFrame(tfidf_matrix)
    ], axis=1)

    preds = model.predict(X_pred)

    candidate_df["predicted_rating"] = preds
    top = candidate_df.sort_values(by="predicted_rating", ascending=False).head(top_n)

    return [
        {
            "product_id": row["id"],
            "name": row.get("name"),
            "description": row.get("description"),
            "predicted_rating": round(row["predicted_rating"], 2)
        }
        for _, row in top.iterrows()
    ]