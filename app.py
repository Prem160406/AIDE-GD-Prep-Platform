from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# -------- MOCK DATABASE --------
topics = [
    {
        "id": 1,
        "title": "AI replacing jobs in 2026",
        "summary": "Debate on automation",
        "source": "TOI",
        "source_url": "https://example.com/1",
        "source_name": "Times of India",
        "status": "draft",
        "created_at": "2026-04-21T10:00:00Z",
        "issue_type": "technology",
        "validation_score": 7,
        "model_used": "gemini",
        "prompt_version": "v1.0"
    },
    {
        "id": 2,
        "title": "Should college attendance be mandatory?",
        "summary": "Education debate",
        "source": "HT",
        "source_url": "https://example.com/2",
        "source_name": "Hindustan Times",
        "status": "draft",
        "created_at": "2026-04-21T11:00:00Z",
        "issue_type": "education",
        "validation_score": 8,
        "model_used": "gemini",
        "prompt_version": "v1.0"
    },
    {
        "id": 3,
        "title": "India's GDP growth: sustainable?",
        "summary": "Economic discussion",
        "source": "Economic Times",
        "source_url": "https://example.com/3",
        "source_name": "ET",
        "status": "active",
        "created_at": "2026-04-21T12:00:00Z",
        "issue_type": "economy",
        "validation_score": 9,
        "model_used": "gemini",
        "prompt_version": "v1.0"
    }
]

# -------- HELPER FUNCTION --------
def response(success, data, meta={}):
    return jsonify({
        "success": success,
        "data": data,
        "meta": meta
    })


# -------- ENDPOINTS --------

# 1. GET active topics
@app.route("/api/gd-topics", methods=["GET"])
def get_active_topics():
    active = [t for t in topics if t["status"] == "active"]
    return response(True, active, {"count": len(active)})


# 2. GET topic by ID
@app.route("/api/gd-topics/<int:id>", methods=["GET"])
def get_topic(id):
    topic = next((t for t in topics if t["id"] == id), None)
    if not topic:
        return response(False, [], {"error": "Topic not found"}), 404
    return response(True, topic, {})


# 3. GET draft topics
@app.route("/api/admin/drafts", methods=["GET"])
def get_drafts():
    drafts = [t for t in topics if t["status"] == "draft"]
    return response(True, drafts, {"count": len(drafts)})


# 4. APPROVE draft
@app.route("/api/admin/drafts/<int:id>/approve", methods=["POST"])
def approve_draft(id):
    topic = next((t for t in topics if t["id"] == id and t["status"] == "draft"), None)
    if not topic:
        return response(False, [], {"error": "Draft not found"}), 404

    topic["status"] = "active"
    return response(True, topic, {"message": "Approved"})


# 5. REJECT draft
@app.route("/api/admin/drafts/<int:id>/reject", methods=["POST"])
def reject_draft(id):
    topic = next((t for t in topics if t["id"] == id and t["status"] == "draft"), None)
    if not topic:
        return response(False, [], {"error": "Draft not found"}), 404

    topic["status"] = "archived"
    return response(True, topic, {"message": "Rejected"})


# -------- ERROR HANDLING --------

@app.errorhandler(404)
def not_found(e):
    return response(False, [], {"error": "Not Found"}), 404


@app.errorhandler(500)
def server_error(e):
    return response(False, [], {"error": "Internal Server Error"}), 500

from flask import request

@app.route("/api/analyze", methods=["POST"])
def analyze():
    from flask import request

    data = request.get_json()
    text = data.get("text", "")

    if not text:
        return response(False, [], {"error": "No text provided"})

    # AI logic (dummy for now)
    summary = text[:50]
    score = len(text) % 10

    # CREATE NEW TOPIC
    new_id = len(topics) + 1

    new_topic = {
        "id": new_id,
        "title": text[:30],
        "summary": summary,
        "source": "AI Generated",
        "source_url": "N/A",
        "source_name": "AI",
        "status": "draft",
        "created_at": "2026-04-22T10:00:00Z",
        "issue_type": "general",
        "validation_score": score,
        "model_used": "gemini",
        "prompt_version": "v1.0"
    }

    topics.append(new_topic)

    return response(True, new_topic, {"message": "Draft created by AI"})

# -------- RUN --------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

