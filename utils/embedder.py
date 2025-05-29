import requests

GEMINI_API_KEY = "AIzaSyCPWTq7pyJWg1lcVD2Mh-V0-R_eyCOlY8k"
GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key=" + GEMINI_API_KEY
GEMINI_CHAT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY

def embed_text(text_list):
    embeddings = []
    for text in text_list:
        payload = {
            "model": "models/embedding-001",
            "content": {"parts": [{"text": text}]}
        }
        res = requests.post(GEMINI_EMBED_URL, json=payload)
        res_json = res.json()
        embeddings.append(res_json['embedding']['values'])
    return embeddings


def get_gemini_response(user_query, context_chunks):
    final_prompt = "Answer using context below:\n\n" + "\n".join(context_chunks) + "\n\nQuestion: " + user_query
    content = [{"parts": [{"text": final_prompt}]}]

    try:
        res = requests.post(GEMINI_CHAT_URL, json={"contents": content})
        print("Gemini Status Code:", res.status_code)
        print("Gemini Response:", res.text)

        # Handle non-200 status
        if res.status_code != 200:
            return f"❌ Gemini API returned {res.status_code}: {res.text}"

        # Try to parse response
        res_json = res.json()

        # Handle error field in JSON
        if 'error' in res_json:
            return f"❌ Gemini API Error: {res_json['error'].get('message', 'No message')}"

        # Handle missing 'candidates'
        if 'candidates' not in res_json:
            return "❌ Gemini API response missing 'candidates'."

        # Try to get the actual response
        return res_json['candidates'][0]['content']['parts'][0]['text']

    except requests.exceptions.RequestException as e:
        return f"❌ Request failed: {str(e)}"

    except ValueError as e:
        return f"❌ Failed to parse JSON: {str(e)}"

    except KeyError as e:
        return f"❌ Unexpected response format, missing key: {str(e)}"

    except Exception as e:
        return f"❌ An unexpected error occurred: {str(e)}"

