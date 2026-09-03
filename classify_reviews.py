import os
import sys
import time
import json
import csv
import sqlite3
import urllib.request
import urllib.error

# Ensure UTF-8 output in Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_FILE = "flipkart_product.csv"
DB_FILE = "amazon_reviews.db"
MODEL_NAME = "gemini-2.5-flash"  # Supports gemini-2.5-flash, gemini-2.5-flash-lite, etc.

def get_api_key():
    """Retrieve Gemini API Key from environment, .env file, or user input."""
    # 1. Check environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        return api_key.strip()
    
    # 2. Check local .env file
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    k = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    if k and k != "YOUR_GEMINI_API_KEY_HERE":
                        return k
    
    # 3. Prompt user if not found
    print("\n[!] GEMINI_API_KEY not found in environment or .env file.")
    api_key = input("Please enter your Gemini API Key: ").strip()
    
    if api_key:
        save = input("Save key to local .env file for future use? (y/n): ").strip().lower()
        if save == 'y':
            with open(".env", "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")
            print("Saved to .env (Note: .env is git-ignored for safety).")
    
    return api_key

def classify_review_with_ai(review_text, question="Is this review about shipping or delivery?", api_key=None, max_retries=3):
    """
    Sends review text to the Gemini API and asks a YES/NO question.
    Handles rate limiting (429) with automatic backoff retry.
    Returns: 'YES', 'NO', or error explanation.
    """
    if not api_key:
        return "ERROR: Missing API Key"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
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
    
    for attempt in range(max_retries):
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                
                # Extract text parts, ignoring thoughts if any
                candidates = res_data.get("candidates", [])
                if not candidates:
                    return "NO_RESPONSE"
                
                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = ""
                for part in parts:
                    if not part.get("thought", False):  # Skip thought tokens
                        raw_text += part.get("text", "")
                
                cleaned = raw_text.strip().upper()
                if "YES" in cleaned:
                    return "YES"
                elif "NO" in cleaned:
                    return "NO"
                return cleaned or "UNKNOWN"
                
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (attempt + 1) * 3
                time.sleep(wait_time)
                continue
            error_body = e.read().decode("utf-8", errors="ignore")
            return f"HTTP_ERROR_{e.code}: {error_body}"
        except Exception as e:
            return f"ERROR: {str(e)}"
            
    return "ERROR: Rate limit exceeded after retries"

def get_row_from_csv(row_index):
    """
    Fetch a single row from flipkart_product.csv by 1-based index (1 to 500).
    Returns dict with row data or None.
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return None
        
    with open(CSV_FILE, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # ['ProductName', 'Price', 'Rate', 'Review', 'Summary']
        
        current_idx = 0
        for row in reader:
            current_idx += 1
            if current_idx == row_index:
                product_name = row[0] if len(row) > 0 else ""
                price = row[1] if len(row) > 1 else ""
                rate = row[2] if len(row) > 2 else ""
                review_title = row[3] if len(row) > 3 else ""
                summary = row[4] if len(row) > 4 else ""
                full_review = f"{review_title}. {summary}" if summary else review_title
                return {
                    "index": current_idx,
                    "product_name": product_name,
                    "price": price,
                    "rate": rate,
                    "review_title": review_title,
                    "summary": summary,
                    "full_review": full_review
                }
    return None

def interactive_single_row_test():
    """Interactive CLI to pick any row index, view review, ask question, and get YES/NO answer."""
    api_key = get_api_key()
    if not api_key:
        print("Error: No API key provided.")
        return

    print("\n" + "=" * 60)
    print("      INTERACTIVE AI REVIEW CLASSIFICATION TESTER")
    print("=" * 60)
    print(f"CSV File : {CSV_FILE} (Contains rows 1 to 500)")
    print(f"AI Model : {MODEL_NAME}")
    print("Type 'exit' or 'q' at any prompt to quit.\n")

    default_question = "Is this review about shipping or delivery?"

    while True:
        try:
            user_input = input("Enter row index (1 - 500) [or 'q' to quit]: ").strip()
            if user_input.lower() in ('q', 'exit', 'quit'):
                print("Exiting test. Goodbye!")
                break
            
            if not user_input.isdigit():
                print(">> Please enter a valid number between 1 and 500.\n")
                continue
                
            row_idx = int(user_input)
            if row_idx < 1 or row_idx > 500:
                print(">> Row index must be between 1 and 500.\n")
                continue
                
            row_data = get_row_from_csv(row_idx)
            if not row_data:
                print(f">> Row {row_idx} could not be found.\n")
                continue
            
            print("\n" + "-" * 60)
            print(f"ROW #{row_data['index']} DETAILS:")
            print(f"  Product : {row_data['product_name']}")
            print(f"  Price   : {row_data['price']}")
            print(f"  Rating  : {row_data['rate']}/5")
            print(f"  Title   : {row_data['review_title']}")
            print(f"  Summary : {row_data['summary']}")
            print(f"  Full Review Text: \"{row_data['full_review']}\"")
            print("-" * 60)
            
            # Prompt for question with default option
            print(f"\nEnter YES/NO question to ask the AI (Press Enter for default: \"{default_question}\"):")
            q_input = input("Question: ").strip()
            if q_input.lower() in ('q', 'exit', 'quit'):
                print("Exiting test. Goodbye!")
                break
                
            question = q_input if q_input else default_question
            
            print(f"\nSending to Gemini API...")
            start_time = time.time()
            result = classify_review_with_ai(row_data['full_review'], question, api_key)
            elapsed = time.time() - start_time
            
            print("\n" + "=" * 40)
            print(f"  QUESTION : {question}")
            print(f"  ANSWER   : {result}")
            print(f"  (Response received in {elapsed:.2f}s)")
            print("=" * 40 + "\n")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting tester.")
            break

if __name__ == "__main__":
    interactive_single_row_test()
