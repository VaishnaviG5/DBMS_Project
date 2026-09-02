import csv
import sqlite3

CSV_FILE = "flipkart_product.csv"
DB_FILE = "amazon_reviews.db"

# Connect to SQLite database
connection = sqlite3.connect(DB_FILE)
cursor = connection.cursor()

# Recreate the reviews table
cursor.execute("DROP TABLE IF EXISTS reviews")
cursor.execute("""
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    price TEXT,
    rate TEXT,
    review TEXT,
    summary TEXT
)
""")

# Load the first 500 rows from flipkart_product.csv
with open(CSV_FILE, "r", encoding="utf-8", errors="ignore") as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header row: ['ProductName', 'Price', 'Rate', 'Review', 'Summary']
    
    rows_to_insert = []
    for row in reader:
        if len(row) >= 5:
            rows_to_insert.append((row[0], row[1], row[2], row[3], row[4]))
        elif len(row) > 0:
            # Handle any padded or shorter rows safely
            padded = row + [""] * (5 - len(row))
            rows_to_insert.append(tuple(padded[:5]))

cursor.executemany("""
INSERT INTO reviews (product_name, price, rate, review, summary)
VALUES (?, ?, ?, ?, ?)
""", rows_to_insert)

connection.commit()
connection.close()

print(f"Database '{DB_FILE}' updated successfully with {len(rows_to_insert)} reviews from '{CSV_FILE}'!")