from datetime import datetime
from flask import Flask, jsonify, request, render_template 
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# -------- MOCK DATABASE --------
topics = [
    {"id": 1, "title": "Interview: Java Developer", "status": "draft", "source": "AIDE HR"},
    {"id": 2, "title": "Interview: Frontend Fresher", "status": "draft", "source": "AIDE HR"},
    {"id": 3, "title": "Trend: 2026 Hiring Freeze", "status": "active", "source": "Glassdoor"}
]

# -------- HELPERS --------
def response(success, data, meta=None):
    return jsonify({"success": success, "data": data, "meta": meta or {}})

# -------- ROUTES --------

# MAIN PAGE: Ye aapka Frontend dikhayega
@app.route("/") 
def home():
    return render_template("index.html")

# 1. API: Get All Topics
@app.route("/api/gd-topics", methods=["GET"])
def get_topics():
    status = request.args.get('status')
    if status:
        filtered = [t for t in topics if t['status'] == status]
        return response(True, filtered, {"count": len(filtered)})
    return response(True, topics, {"count": len(topics)})

# 2. API: Get Specific Topic
@app.route("/api/gd-topics/<int:tid>", methods=["GET"])
def get_topic(tid):
    t = next((x for x in topics if x['id'] == tid), None)
    return response(True, t) if t else (response(False, [], {"error": "Not Found"}), 404)

# 3. ADMIN: View Drafts
@app.route("/api/admin/drafts", methods=["GET"])
def get_drafts():
    drafts = [t for t in topics if t['status'] == 'draft']
    return response(True, drafts, {"count": len(drafts)})

# 4. ADMIN: Approve Logic
@app.route("/api/admin/drafts/<int:tid>/approve", methods=["POST"])
def approve(tid):
    for t in topics:
        if t['id'] == tid:
            t['status'] = 'active'
            return response(True, t, {"message": "Approved"})
    return response(False, [], {"error": "Not Found"}), 404

# 5. ADMIN: Reject Logic
@app.route("/api/admin/drafts/<int:tid>/reject", methods=["POST"])
def reject(tid):
    global topics
    topics = [t for t in topics if t['id'] != tid]
    return response(True, [], {"message": "Deleted"})

# 6. AI: Generation Logic
@app.route("/api/generate-questions", methods=["POST"])
def generate():
    role = request.json.get('text', 'General')
    new_id = len(topics) + 1
    new_item = {"id": new_id, "title": f"Interview: {role}", "status": "draft", "source": "AI Generated"}
    topics.append(new_item)
    return response(True, new_item)

# 7. RSS: Sync Trends
@app.route("/api/admin/sync-trends", methods=["POST"])
def sync():
    return response(True, [], {"message": "Synced 5 HR trends"})

# -------- RUN --------
def print_dash():
    print("\n" + "="*40 + "\n🚀 SERVER LIVE: http://127.0.0.1:5000\n" + "="*40)

if __name__ == "__main__":
    print_dash()
    app.run(debug=True, port=5000)