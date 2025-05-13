import requests

class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",  # Ollama endpoint
        model: str = "llama3.2:3b",                       # use the NAME from `ollama list`
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        url = f"{self.base_url}/generate"
        payload = {
            "model": self.model,     # e.g. "llama3.2"
            "prompt": prompt,
            "stream": False,
            "options": {"max_tokens": max_tokens},
        }
        # send the request
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns your text under the "response" key
        return data.get("response", "")

# ─── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = OllamaClient(model="llama3.2")
    answer = client.generate("Explain the impact of interest rates on real estate investments.")
    print(answer)
