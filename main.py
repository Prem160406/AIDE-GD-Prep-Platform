from fastapi import FastAPI

app = FastAPI()

# Mock data (fake topics)
mock_topics = [
    {
        "id": 1,
        "title": "AI in Healthcare",
        "description": "How AI is changing medical field",
        "status": "active"
    },
    {
        "id": 2,
        "title": "Climate Change 2025",
        "description": "Latest updates on climate",
        "status": "active"
    },
    {
        "id": 3,
        "title": "Space Exploration",
        "description": "Mars mission updates",
        "status": "draft"
    }
]

@app.get("/")
def home():
    return {"message": "AIDE Backend is running!"}

@app.get("/topics")
def get_topics():
    return {"topics": mock_topics}