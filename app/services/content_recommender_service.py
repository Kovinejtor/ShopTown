from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.core.databse import dynamodb
import pandas as pd

def load_products_from_dynamodb():
    table = dynamodb.Table("Products")
    response = table.scan()
    items = response.get("Items", [])
    return pd.DataFrame(items)

def load_user_reviews(user_id):
    table = dynamodb.Table("Reviews")
    response = table.scan(
        FilterExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id}
    )
    return pd.DataFrame(response.get("Items", []))

def get_content_based_recommendations(user_id: str, top_n=5):
    products_df = load_products_from_dynamodb()
    reviews_df = load_user_reviews(user_id)

    if products_df.empty or reviews_df.empty:
        return []

    liked_products = reviews_df[reviews_df["rating"].astype(float) >= 3.0]["product_id"].tolist()
    liked_df = products_df[products_df["id"].isin(liked_products)]

    if liked_df.empty:
        return []

    products_df["text"] = products_df["name"].fillna('') + " " + products_df["description"].fillna('')
    liked_df["text"] = liked_df["name"].fillna('') + " " + liked_df["description"].fillna('')

    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(products_df["text"])
    liked_matrix = tfidf.transform(liked_df["text"])

    sim_scores = cosine_similarity(liked_matrix, tfidf_matrix).mean(axis=0)
    products_df["score"] = sim_scores

    recommended = products_df[~products_df["id"].isin(liked_products)] \
        .sort_values(by="score", ascending=False) \
        .head(top_n)

    return [
        {
            "product_id": row["id"],
            "name": row.get("name"),
            "description": row.get("description"),
            "score": round(row["score"], 3)
        }
        for _, row in recommended.iterrows()
    ]