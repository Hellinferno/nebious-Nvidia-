import os
import json
from openai import OpenAI
from dotenv import load_dotenv

def main():
    load_dotenv(dotenv_path="../.env")
    
    api_key = os.getenv("NEBIUS_API_KEY")
    base_url = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1/")
    
    if not api_key or api_key == "your_api_key_here":
        print("Error: NEBIUS_API_KEY is missing or invalid in .env")
        return

    client = OpenAI(api_key=api_key, base_url=base_url)
    
    print("Fetching model catalog...")
    models = client.models.list()
    for m in models.data:
        print(f"- {m.id}")
        
    target_model = "meta-llama/Meta-Llama-3.1-70B-Instruct" # Typical model on Nebius, adjust as needed
    
    print(f"\nRunning bounded inference on {target_model}...")
    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": "Return the string 'HELLO_NVIDIA' and nothing else."}],
            max_tokens=10
        )
        
        output = response.choices[0].message.content
        usage = response.usage
        
        metadata = {
            "model": target_model,
            "response": output,
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None
        }
        
        os.makedirs("../artifacts", exist_ok=True)
        with open("../artifacts/inference_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        print("Inference successful! Saved metadata to artifacts/inference_metadata.json")
        print(json.dumps(metadata, indent=2))
        
    except Exception as e:
        print(f"Inference failed: {e}")

if __name__ == "__main__":
    main()
