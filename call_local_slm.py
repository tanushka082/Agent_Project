# call_local_slm.py
import json
import ollama

def call_local_slm(prompt: str, temperature: float = 0.0, num_predict: int = 1024) -> str:
    """
    Central API utility calling local Llama 3.2 3B.
    All agents route through this single function to enforce parameters and JSON output.
    """
    try:
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={
                "temperature": temperature,
                "num_predict": num_predict
            }
        )
        content = response['message']['content']
        if not content or not content.strip():
            raise ValueError("Ollama returned an empty response string.")
        return content.strip()
    except Exception as e:
        print(f" [OLLAMA EXCEPTION] Local SLM call failed: {e}")
        return json.dumps({})
