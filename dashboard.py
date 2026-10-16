from flask import Flask, jsonify, request, render_template
import asyncio
import db

app = Flask(__name__)


def run_async(coro):
    return asyncio.run(coro)


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/complaint/<complaint_number>")
def complaint_detail(complaint_number):
    return render_template("complaint.html", complaint_number=complaint_number)


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/complaints")
def get_complaints():
    category = request.args.get("category")
    status   = request.args.get("status")
    search   = request.args.get("search")
    results  = run_async(db.get_all_complaints(category=category, status=status, search=search))
    return jsonify(results)


@app.route("/api/complaint/<complaint_number>")
def get_complaint(complaint_number):
    complaint  = run_async(db.get_complaint_full(complaint_number))
    transcript = run_async(db.get_transcript(complaint_number))
    if complaint is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"complaint": complaint, "transcript": transcript})


@app.route("/api/complaint/<complaint_number>/status", methods=["POST"])
def update_status(complaint_number):
    data   = request.get_json()
    status = data.get("status") if data else None
    if status not in ("Pending", "In Progress", "Resolved"):
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    ok = run_async(db.update_complaint_status(complaint_number, status))
    return jsonify({"ok": ok})


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
