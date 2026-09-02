import pandas as pd
import sqlite3

df = pd.read_csv("db.csv")

connection = sqlite3.connect("amazon_reviews.db")

df.to_sql(
    "reviews",
    connection,
    if_exists="replace",
    index=False
)
connection.close()

print("Database created successfully!")