import sqlite3

connection = sqlite3.connect("amazon_reviews.db")

cursor = connection.cursor()

cursor.execute("SELECT COUNT(*) FROM reviews")

count = cursor.fetchone()[0]

print("Number of reviews:", count)

connection.close()