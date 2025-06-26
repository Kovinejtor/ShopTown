from surprise import SVD, Dataset, Reader
import pandas as pd
from app.core.databse import dynamodb 

def load_review_data_from_dynamodb():
    table = dynamodb.Table("Reviews")
    response = table.scan()
    items = response.get("Items", [])

    data = [
        {
            "user_id": item["user_id"],
            "product_id": item["product_id"],
            "rating": float(item["rating"]),
        }
        for item in items if "user_id" in item and "product_id" in item and "rating" in item
    ]

    return pd.DataFrame(data)

def train_model():
    df = load_review_data_from_dynamodb()
    if df.empty:
        return None, df

    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(df[["user_id", "product_id", "rating"]], reader)
    trainset = data.build_full_trainset()
    model = SVD()
    model.fit(trainset)
    return model, df

def get_collaborative_based_recommendations(user_id: str, top_n=5):
    model, df = train_model()
    if model is None or df.empty:
        return []

    all_products = df["product_id"].unique()
    rated_products = df[df["user_id"] == user_id]["product_id"].values
    unrated_products = [p for p in all_products if p not in rated_products]

    predictions = [(pid, model.predict(user_id, pid).est) for pid in unrated_products]
    predictions.sort(key=lambda x: x[1], reverse=True)
    top_preds = predictions[:top_n]

    return [{"product_id": pid, "predicted_rating": round(score, 2)} for pid, score in top_preds]
