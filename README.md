# ShopTown

**ShopTown** is an e-commerce backend service built using **FastAPI** and **DynamoDB (via LocalStack)**.  
It provides functionality for managing products, users, orders, reviews, and generating product recommendations via collaborative filtering, content-based filtering, and gradient boosting models.

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| **FastAPI** | API development  |
| **DynamoDB (LocalStack)** | NoSQL database for storing app data (users, products, orders, reviews) |
| **Docker + docker-compose** | Containerization and orchestration |
| **XGBoost** | Gradient Boosting model for recommendations |
| **Scikit-learn** | Content-based filtering (TF-IDF, Label Encoding) |
| **Surprise library** | Collaborative filtering (SVD) |
| **pandas / numpy** | Data manipulation |

---

## Project Structure

<pre>
ShopTown/
├── app/
│ ├── api/ # Auth router (for now)
│ ├── core/ # DB connection, security, dependencies
│ ├── models/ # Pydantic models (User, Product, Order, Review)
│ ├── services/ # Business logic (auth, products, orders, recommendations)
│ └── main.py # FastAPI app entry point
├── utils/ # Data population & utility scripts
├── model_data/ # Saved models, encoders, vectorizers
├── docker-compose.yml # Docker orchestration
├── Dockerfile # API image build instructions
├── requirements.txt # Python dependencies
└── README.md # Project documentation
</pre>

## Docker Setup

### Dockerfile
- Uses `python:3.11-slim` as base image.
- Installs build tools and math libraries for packages like `numpy`, `scikit-learn`, `xgboost`.
- Installs Python dependencies from `requirements.txt`.
- Runs FastAPI app via `uvicorn`.

### docker-compose.yml
- **dynamodb:** LocalStack DynamoDB on port `4566`.
- **shoptown:** Builds and runs API container on port `8000`, depends on DynamoDB.

---

## How to Run

If **Docker** and **docker-compose** are installed:

```bash
git clone <repo-url>
cd <repo-folder>
docker-compose up --build
```
The API will be accessible at:
http://localhost:8000

The docs can be explored at:
http://localhost:8000/docs

---

## Mock Data Generation

The data used in **ShopTown** was generated through a combination of **[Mockaroo](https://mockaroo.com/)** and programmatically created values.

### Sources:
**Users data**: Generated using Mockaroo and loaded from a CSV file.  
**Products data**: Generated using Mockaroo, linked to users as sellers, with some reviews assigned.  
**Reviews data**: Review text and ratings were generated with ChatGPT, then associated with products and users.  
**Orders data**: Fully generated via code, simulating realistic purchases and occasionally adding reviews.

### CSV files used:
- `USER_MOCK_DATA.csv` — Mockaroo-generated user records (username, email, password)
- `PRODUCT_MOCK_DATA.csv` — Mockaroo-generated product records (name, price, description, quantity)
- `REVIEW_DATA.csv` — ChatGPT-generated reviews (rating, review text)

### How data is loaded:
- **`populate_users_from_csv`**  
  Loads users from the user CSV, assigns a UUID, and saves them to DynamoDB.

- **`populate_products_from_csv`**  
  Loads products from the product CSV, assigns random sellers (users), generates random reviews (from the review pool), and saves them.

- **`populate_mock_orders`**  
  Generates `n` (default 500) random orders:
  - Random buyer + product
  - Random quantity
  - Random date within a specified range
  - Randomly attaches a generated review

- **`populate_all`**  
  Runs the above in sequence: populates users, then products (with reviews), then orders (with possible reviews).

## Database Tables Overview

The project uses four main DynamoDB tables, each represented by a Pydantic model. Below is the logical structure and attribute types:

---

### Users Table
Stores user account data.

| Attribute | Type |
|------------|------|
| `id` | `str` (Partition key) |
| `username` | `str` |
| `email` | `EmailStr` |
| `password` | `str` |

---

### Products Table
Stores product listings.

| Attribute | Type |
|------------|------|
| `id` | `str` (Partition key) |
| `name` | `str` |
| `description` | `str` |
| `price` | `Decimal` |
| `stock` | `int` |
| `seller_id` | `str` |
| `review_ids` | `Optional[List[str]]` (default: empty list) |

---

### Orders Table
Stores purchase records.

| Attribute | Type |
|------------|------|
| `id` | `str` (Partition key) |
| `buyer_id` | `str` |
| `product_id` | `str` |
| `product_name` | `str` |
| `product_price` | `Decimal` |
| `description` | `Optional[str]` |
| `purchase_date` | `str` (ISO date string) |
| `quantity` | `int` |
| `total_price` | `Decimal` |
| `seller_id` | `str` |
| `status` | `Literal["completed", "refunded"]` |
| `review_id` | `Optional[str]` (default: `None`) |

---

### Reviews Table
Stores product reviews.

| Attribute | Type |
|------------|------|
| `review_id` | `str` (Partition key) |
| `product_id` | `str` |
| `user_id` | `str` |
| `rating` | `Decimal` |
| `review` | `str` |

---

## Authentication Logic

The authentication system is built using **FastAPI**, **JWT tokens**, and **bcrypt password hashing**. It consists of several key components working together:

---

### `api/auth.py`
- **`/auth/register` (POST)**  
  Registers a new user by accepting `username`, `email`, and `password`.  
  Calls `register_user()` from `auth_service.py`.

- **`/auth/login` (POST)**  
  Authenticates a user using `email` and `password`.  
  Calls `authenticate_user()` from `auth_service.py`, and returns a JWT token on success.

---

### `services/auth_service.py`
- **`register_user`**  
  - Checks if a user with the provided email exists (DynamoDB scan).  
  - Hashes the password using `hash_password`.  
  - Stores the user data in the `Users` table (with a generated UUID as `id`).  

- **`authenticate_user`**  
  - Scans for the user by email.  
  - Verifies password using `verify_password`.  
  - If valid, generates a JWT token via `create_access_token`.

---

### `core/security.py`
- Handles **password security** and **token management**:
  - `hash_password` → Hashes password with bcrypt.
  - `verify_password` → Verifies a plain password against a bcrypt hash.
  - `create_access_token` → Generates a signed JWT with expiry.
  - `decode_token` → Validates and decodes JWTs (returns payload or `None`).

---

### `core/dependecies.py`
- **`get_current_user`**  
  - Extracts the JWT from the Authorization header (`Bearer <token>`).  
  - Decodes and verifies the token.  
  - Retrieves the user from the `Users` table using `sub` claim (`user_id`).  
  - Raises appropriate `HTTPException` if the token is invalid or user not found.

---

### How It All Fits Together
**User registers** → `POST /auth/register` → User is saved in DynamoDB with hashed password.  
**User logs in** → `POST /auth/login` → Password is verified, JWT is returned.  
**Protected routes** → Client includes `Authorization: Bearer <token>` → `get_current_user` verifies token and loads user.  

---

### Example Auth Flow
1. Register:
    ```http
    POST /auth/register
    {
      "username": "alice",
      "email": "alice@example.com",
      "password": "securepass"
    }
    ```
2. Login:
    ```http
    POST /auth/login
    {
      "email": "alice@example.com",
      "password": "securepass"
    }
    ```
    → Response: `{ "access_token": "...", "token_type": "bearer" }`

3. Access protected route:
    ```
    POST /products
    Authorization: Bearer <access_token>
    ```

This structure ensures that users are securely authenticated, and protected endpoints can verify and authorize requests.

## Main FastAPI Application (`main.py`)

This file defines all API endpoints of **ShopTown**, wires up routes, and connects to services for business logic and database interaction.

---

### Public Endpoints (No auth required)

- **`GET /`**  
  Returns welcome message.  

- **`POST /populate`**  
  Populates DB with dummy data using `populate_all` from `utils.fill_dummy_data.py`. This and the next endpoint do not need auth because they are just for development. In production they would be removed because there would be real data.

- **`DELETE /delete-all`**  
  Clears Products, Users, Orders, Reviews using `delete_all_items` from `utils.delete_all_data.py`.

- **`GET /products`**  
  Lists all products.  
  → Uses `get_products_table` from `product_service.py`.

- **`GET /products/{product_id}`**  
  Fetches a specific product by ID.  
  → Uses `get_products_table` from `product_service.py`.

- **`GET /products/seller/{seller_id}`**  
  Lists products by a seller.  
  → Uses `get_products_by_seller` from `product_service.py`.

- **`GET /products/search?keyword=`**  
  Searches products by keyword in name/description.  
  → Uses `get_products_table`.

- **`GET /products/filtered`**  
  Lists filtered/paginated products (price, search, sort).  
  → Uses `get_products_table`.

- **`GET /reviews/user/{user_id}`**  
  Lists reviews by user.  
  → Uses `get_reviews_table` from `review_service.py`.

- **`GET /reviews/{review_id}`**  
  Gets a review by ID.  
  → Uses `get_reviews_table`.

- **`GET /reviews/product/{product_id}`**  
  Gets reviews for a product (using `review_ids` from product).  
  → Uses `get_products_table`, `get_reviews_table`.

- **`GET /recommendations/collaborative/{user_id}`**  
  Returns collaborative filtering recommendations.  
  → Uses `collaborative_recommender_service.py`.

- **`GET /recommendations/content/{user_id}`**  
  Returns content-based recommendations.  
  → Uses `content_recommender_service.py`.

- **`POST /recommendations/gradientboost/train`**  
  Trains gradient boost model.  
  → Uses `gradient_boost_recommender_service.py`.

- **`GET /recommendations/gradientboost/{user_id}`**  
  Gets gradient boost recommendations for a user.  
  → Uses `gradient_boost_recommender_service.py`.

---

### Protected Endpoints (Require token)

- **`GET /me`**  
  Returns current user profile.  
  → Uses `get_current_user` from `core.dependencies.py`.

- **`POST /products`**  
  Create a new product (as seller).  
  → Uses `get_products_table`, `product_service.py`.

- **`GET /products/low-stock`**  
  Lists products low in stock.  
  → Uses `get_products_table`.

- **`POST /reviews`**  
  Create a review.  
  → Uses `create_review` from `review_service.py`.

- **`GET /users`**  
  Lists all users.  
  → Uses `get_users_table` from `user_service.py`.

- **`POST /purchase/{product_id}`**  
  Purchases a product, updates stock/orders.  
  → Uses `purchase_product` from `order_service.py`.

- **`GET /orders`**  
  Lists all orders.  
  → Uses `get_orders_table`.

- **`GET /orders/{buyer_id}`**  
  Lists orders for a buyer (self).  
  → Uses `get_orders_by_buyer` from `order_service.py`.

- **`POST /refund/{order_id}`**  
  Process a refund (with checks).  
  → Uses `refund_order` from `order_service.py`.

---

### Connections

- **Services:** All core logic (DB ops, business rules) lives in `services/*.py`.
- **Models:** Pydantic schemas in `models/` define request/response shapes.
- **Utils:** `utils/` handles dummy data, cleanup scripts.
- **Security:** `core/security.py` + `core/dependencies.py` manage auth.

## Recommendation Systems

This project implements **three types of recommendation systems**:

### 1. Collaborative Filtering (SVD)
- **How it works:**
  - Uses the `surprise` library’s SVD (Singular Value Decomposition).
  - Learns *latent features* from the `Reviews` table (user_id, product_id, rating).
  - Predicts how much a user will like an unrated product based on patterns in the entire user-product rating matrix.

- **Simple example:**  
  Suppose:
User u1 rated Product p1: 4
User u1 rated Product p2: 5
User u2 rated Product p2: 3
User u3 rated Product p1: 2

The model learns that u1 tends to like products similar to p1 and p2, and predicts ratings for other products accordingly.

---

### 2. Content-Based Filtering (TF-IDF + Cosine Similarity)
- **How it works:**  
- Builds a TF-IDF matrix on product `name + description`.
- Finds products most similar (textually) to what the user liked (rating >= 3).

- **Simple example:**  
If a user liked `Granola - Crunchy oats with honey`, they might be recommended `Honey Oat Bars - Sweet snack`, because of shared terms like *honey* and *oats*.

---

### 3. Gradient Boosting Regressor (XGBoost)
- **How it works:**  
- Trains an XGBoost regressor on:
  - `price`
  - encoded `seller_id`
  - TF-IDF features from `name + description`
- Predicts ratings for unseen products.

- **Simple example:**  
If user reviews show preference for mid-priced products from a certain seller, and descriptions mentioning *eco-friendly*, the model learns this pattern and predicts high ratings for similar future products.

---

### How to Use these Endpoints
- `GET /recommendations/collaborative/{user_id}` → Get SVD-based recommendations.
- `GET /recommendations/content/{user_id}` → Get content-based recommendations.
- `POST /recommendations/gradientboost/train` → Train XGBoost model.
- `GET /recommendations/gradientboost/{user_id}` → Get gradient-boost recommendations.


## Some FastAPI docs images

![start](images/start.png)

![start2](images/start2.png)

![1](images/1.png)

![2](images/2.png)

![3](images/3.png)

![4](images/4.png)

![5](images/5.png)

![6](images/6.png)

![7](images/7.png)

![8](images/8.png)

![9](images/9.png)

![10](images/10.png)

![11](images/11.png)

![12](images/12.png)

![13](images/13.png)

![14](images/14.png)

![15](images/15.png)

![16](images/16.png)

![17](images/17.png)

![18](images/18.png)

![19](images/19.png)

![20](images/20.png)
...