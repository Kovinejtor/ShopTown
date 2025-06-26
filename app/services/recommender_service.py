from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
import pandas as pd

def load_review_data():
    data = [
        {"user_id": "u1", "product_id": "p1", "rating": 4},
        {"user_id": "u1", "product_id": "p2", "rating": 5},
        {"user_id": "u2", "product_id": "p2", "rating": 3},
        {"user_id": "u3", "product_id": "p1", "rating": 2},
    ]
    return pd.DataFrame(data)

def train_model():
    df = load_review_data()
    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(df[["user_id", "product_id", "rating"]], reader)
    trainset = data.build_full_trainset()
    model = SVD()
    model.fit(trainset)
    return model, df

def get_recommendations_for_user(user_id: str, top_n=5):
    model, df = train_model()
    all_products = df["product_id"].unique()
    rated_products = df[df["user_id"] == user_id]["product_id"].values
    unrated_products = [p for p in all_products if p not in rated_products]
    
    predictions = [(pid, model.predict(user_id, pid).est) for pid in unrated_products]
    predictions.sort(key=lambda x: x[1], reverse=True)
    top_preds = predictions[:top_n]
    
    return [{"product_id": pid, "predicted_rating": round(score, 2)} for pid, score in top_preds]
