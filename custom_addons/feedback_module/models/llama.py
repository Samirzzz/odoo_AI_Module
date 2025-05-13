import logging
import requests
import urllib3

_logger = logging.getLogger(__name__)
# Disable only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OllamaClient:
    """Ollama HTTP client (no SSL verification)."""
    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",  # Ollama endpoint
        model: str = "llama3.2:3b",                       # use the NAME from `ollama list`
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/generate",
                json={
                    "model": self.model,     # e.g. "llama3.2"
                    "prompt": prompt,
                    "stream": False,
                    "options": {"max_tokens": max_tokens},
                },
                timeout=300,  # 5 minutes timeout
                verify=False,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.Timeout:
            _logger.error("Ollama API timeout")
            return "Error: Ollama service timed out. The request took too long to process."
        except requests.exceptions.ConnectionError:
            _logger.error("Ollama API connection error")
            return "Error: Cannot connect to Ollama service. Please ensure it's running."
        except Exception as e:
            _logger.error("Ollama API error: %s", str(e))
            return f"Error: Unable to generate response. {str(e)}"

# ─── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = OllamaClient(model="llama3.2")
    answer = client.generate("Explain the impact of interest rates on real estate investments.")
    print(answer)
