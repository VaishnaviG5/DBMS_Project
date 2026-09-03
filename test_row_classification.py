import os
import sys
import csv
import json
import urllib.request
import urllib.error

# Ensure UTF-8 output in Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_FILE = "flipkart_product.csv"
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.6-flash"]

def get_api_key():
    """Retrieve Gemini API Key from environment, .env file, or user input."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        return api_key.strip()
    
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    k = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    if k and k != "YOUR_GEMINI_API_KEY_HERE":
                        return k
    
    print("\n[!] GEMINI_API_KEY not found in environment or .env file.")
    api_key = input("Please enter your Gemini API Key: ").strip()
    if api_key:
        save = input("Save key to local .env file for future use? (y/n): ").strip().lower()
        if save == 'y':
            with open(".env", "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")
            print("Saved to .env.")
    return api_key

def get_csv_row(row_index):
    """
    Fetch a row by index (1-based index for data rows, 1 to 500).
    Returns dictionary with product details and review text.
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return None

    with open(CSV_FILE, "r", encoding="utf-8", errors="ignore") as f:
        reader = list(csv.reader(f))
        total_data_rows = len(reader) - 1
        
        if row_index < 1 or row_index > total_data_rows:
            print(f"Error: Row index must be between 1 and {total_data_rows}.")
            return None
        
        row = reader[row_index]
        product_name = row[0] if len(row) > 0 else "Unknown Product"
        rating = row[2] if len(row) > 2 else "N/A"
        review_title = row[3] if len(row) > 3 else ""
        review_summary = row[4] if len(row) > 4 else ""
        
        if review_title and review_summary:
            full_review = f"{review_title}. {review_summary}"
        else:
            full_review = review_title or review_summary
            
        return {
            "row_index": row_index,
            "product": product_name,
            "rating": rating,
            "review": full_review,
            "total_rows": total_data_rows
        }

def ask_gemini_yes_no(review_text, question, api_key):
    """
    Sends only the review text and the question to Gemini API.
    Returns strictly 'YES' or 'NO'.
    """
    prompt = (
        f"You are a text classification assistant.\n"
        f"Review text: \"{review_text}\"\n"
        f"Question: {question}\n\n"
        f"Instructions: Answer strictly with only one word: 'YES' or 'NO'."
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 200
        }
    }
    
    headers = {"Content-Type": "application/json"}
    data_bytes = json.dumps(payload).encode("utf-8")
    
    last_error = None
    for model_name in FALLBACK_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if not candidates:
                    continue
                
                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = ""
                for part in parts:
                    if not part.get("thought", False):
                        raw_text += part.get("text", "")
                
                cleaned = raw_text.strip().upper()
                if "YES" in cleaned:
                    return "YES"
                elif "NO" in cleaned:
                    return "NO"
                return cleaned or "UNKNOWN"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP_{e.code}: {error_body}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return f"ERROR: {last_error}"

def test_interactive():
    """Interactive CLI loop to test any row from CSV."""
    api_key = get_api_key()
    if not api_key:
        print("Error: Valid Gemini API key required.")
        return

    print("\n================ CSV ROW AI CLASSIFIER ================")
    print(f"Dataset: {CSV_FILE} (Rows 1 to 500)")
    print("Type 'exit' or 'q' at any prompt to quit.")
    print("========================================================\n")

    while True:
        user_input = input("\nEnter row index (1 - 500): ").strip()
        if user_input.lower() in ['exit', 'q']:
            print("Exiting.")
            break
            
        if not user_input.isdigit():
            print("Please enter a valid integer number (e.g., 1, 2, 42).")
            continue
            
        row_idx = int(user_input)
        row_data = get_csv_row(row_idx)
        if not row_data:
            continue
            
        print("\n" + "-" * 60)
        print(f"Row #{row_data['row_index']} | Product: {row_data['product'][:50]}... | Rating: {row_data['rating']}/5")
        print(f"Review Content: \"{row_data['review']}\"")
        print("-" * 60)
        
        default_q = "Is this review about shipping or delivery?"
        custom_q = input(f"Enter question [Press Enter for: '{default_q}']: ").strip()
        question = custom_q if custom_q else default_q
        
        print("\nSending review + question to Gemini API...")
        answer = ask_gemini_yes_no(row_data['review'], question, api_key)
        
        print("\n" + "=" * 35)
        print(f"QUESTION : {question}")
        print(f"AI ANSWER: {answer}")
        print("=" * 35)

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1].isdigit():
        row_idx = int(sys.argv[1])
        question = sys.argv[2] if len(sys.argv) >= 3 else "Is this review about shipping or delivery?"
        
        api_key = get_api_key()
        row_data = get_csv_row(row_idx)
        if row_data and api_key:
            print(f"\nRow #{row_data['row_index']} Review: \"{row_data['review']}\"")
            print(f"Question: \"{question}\"")
            answer = ask_gemini_yes_no(row_data['review'], question, api_key)
            print(f"AI Answer: {answer}\n")
    else:
        test_interactive()
