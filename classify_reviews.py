import os
import sys
import time
import json
import sqlite3
import urllib.request
import urllib.error

# Ensure UTF-8 output in Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_FILE = "amazon_reviews.db"
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
            print("Saved to .env (Note: .env is git-ignored for safety).")
    
    return api_key

def classify_review_with_ai(review_text, question="Is this review about shipping or delivery?", api_key=None):
    """
    Sends review text to the Gemini API and asks a YES/NO question.
    Falls back gracefully across models.
    Returns: 'YES', 'NO', or error explanation.
    """
    if not api_key:
        return "ERROR: Missing API Key"

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

def classify_sample_reviews(num_samples=5, question="Is this review about shipping or delivery?"):
    """Fetch sample reviews from the SQLite DB and run AI classification."""
    api_key = get_api_key()
    if not api_key:
        print("Error: No API key provided.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, product_name, rate, review, summary FROM reviews LIMIT ?", (num_samples,))
    rows = cursor.fetchall()
    conn.close()

    print(f"\n================ AI REVIEW CLASSIFICATION ================")
    print(f"Question: \"{question}\"")
    print(f"Evaluating {len(rows)} reviews from database...")
    print("==========================================================\n")

    results = []
    for i, row in enumerate(rows):
        rev_id, product, rating, title, summary = row
        full_review = f"{title}. {summary}" if summary else title
        
        classification = classify_review_with_ai(full_review, question, api_key)
        
        print(f"Review #{rev_id} [{product[:40]}... | Rating: {rating}/5]")
        print(f"Text: \"{full_review}\"")
        print(f"-> Classification: {classification}")
        print("-" * 58)
        
        results.append({
            "id": rev_id,
            "product": product,
            "review": full_review,
            "classification": classification
        })
        
        if i < len(rows) - 1:
            time.sleep(0.5)

    print("\nClassification complete!")
    return results

if __name__ == "__main__":
    classify_sample_reviews(num_samples=5, question="Is this review about shipping or delivery?")
