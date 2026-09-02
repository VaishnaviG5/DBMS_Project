import sqlite3

connection = sqlite3.connect("amazon_reviews.db")
cursor = connection.cursor()

<<<<<<< Updated upstream
# Get total review count
cursor.execute("SELECT COUNT(*) FROM reviews")
count = cursor.fetchone()[0]
print(f"Total reviews in database: {count}")

# Fetch schema info
cursor.execute("PRAGMA table_info(reviews)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {columns}")

# Preview first 3 records
print("\n--- Sample Reviews ---")
cursor.execute("SELECT id, product_name, rate, review, summary FROM reviews LIMIT 3")
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"Product: {row[1]}")
    print(f"Rating: {row[2]}")
    print(f"Review: {row[3]}")
    print(f"Summary: {row[4]}")
    print("-" * 40)
=======
cursor.execute("""
SELECT *
FROM reviews
LIMIT 10
""")
cursor.execute("""
SELECT *
FROM reviews
WHERE review_rating >= 4
LIMIT 10
""")
rows = cursor.fetchall()

for row in rows:
    print(row)
>>>>>>> Stashed changes

connection.close()