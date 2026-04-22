from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Import your services
from services.ai_service import process_text_to_topic
from services.rss_service import fetch_news_to_topics

app = Flask(__name__)
CORS(app)

# -------- MOCK DATABASE --------
topics = [
    {"id": 1, "title": "AI replacing jobs in 2026", "status": "draft", "source": "TOI"},
    {"id": 2, "title": "Should college attendance be mandatory?", "status": "draft", "source": "HT"},
    {"id": 3, "title": "India's GDP growth: sustainable?", "status": "active", "source": "ET"}
]

# -------- HELPER FUNCTION --------
def response(success, data, meta={}):
    return jsonify({"success": success, "data": data, "meta": meta})

# -------- ENDPOINTS --------

@app.route("/api/gd-topics", methods=["GET"])
def get_active_topics():
    active = [t for t in topics if t.get("status") == "active"]
    return response(True, active, {"count": len(active)})

@app.route("/api/gd-topics/<int:id>", methods=["GET"])
def get_topic(id):
    topic = next((t for t in topics if t["id"] == id), None)
    if not topic:
        return response(False, [], {"error": "Topic not found"}), 404
    return response(True, topic)

@app.route("/api/admin/drafts", methods=["GET"])
def get_drafts():
    drafts = [t for t in topics if t.get("status") == "draft"]
    return response(True, drafts, {"count": len(drafts)})

@app.route("/api/admin/drafts/<int:id>/approve", methods=["POST"])
def approve_draft(id):
    topic = next((t for t in topics if t["id"] == id), None)
    if topic:
        topic["status"] = "active"
        return response(True, topic, {"message": "Approved"})
    return response(False, [], {"error": "Not found"}), 404

@app.route("/api/admin/drafts/<int:id>/reject", methods=["POST"])
def reject_draft(id):
    topic = next((t for t in topics if t["id"] == id), None)
    if topic:
        topic["status"] = "archived"
        return response(True, topic, {"message": "Rejected"})
    return response(False, [], {"error": "Not found"}), 404

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "")
    if not text or len(text) < 10:
        return response(False, [], {"error": "Text too short"}), 400
    
    # Using your service
    new_topic = process_text_to_topic(text, len(topics))
    topics.append(new_topic)
    return response(True, new_topic)



@app.route("/api/admin/sync-news", methods=["POST"])
def sync_news():
    # Adding silent=True prevents the 415 error if no JSON is sent
    data = request.get_json(silent=True) or {} 
    
    rss_url = data.get("url", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms")
    # ... rest of your code
    source = data.get("source", "TOI")

    try:
        new_news_items = fetch_news_to_topics(rss_url, source)
        for item in new_news_items:
            item["id"] = len(topics) + 1
            topics.append(item)
        return response(True, [], {"message": f"Synced {len(new_news_items)} items from {source}"})
    except Exception as e:
        return response(False, [], {"error": str(e)}), 500

# -------- ERROR HANDLING --------
@app.errorhandler(404)
def not_found(e):
    return response(False, [], {"error": "Not Found"}), 404

# -------- RUN (Keep this at the VERY BOTTOM) --------
if __name__ == "__main__":
    # Now this will actually print!
    with app.test_request_context():
        print("\n--- REGISTERED ROUTES ---")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule.rule}")
        print("-------------------------\n")
        
    app.run(debug=True, port=5000)