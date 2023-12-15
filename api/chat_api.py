from openai import OpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat_requeset_schema import ChatRequest

app = FastAPI(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SYSTEM_MSG = "You are a helpful summation assistant"

client = OpenAI()

@app.post("/chat/gpt3")
@app.post("/chat/gpt4")
def chat_gpt3(req: ChatRequest):
    try:
        print(f"Received message: {req.message}")
        completion = client.chat.completions.create(
            model=req.model,
            messages=req.message,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )

        response_content = completion.choices[0].message.content
        total_tokens = completion.usage.total_tokens
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens

        return {
            "message": response_content,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        }
    except Exception as e:
        print(f"Error during API call: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

