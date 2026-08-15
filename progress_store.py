"""
progress_store.py
------------------
Very small JSON "database" so a student's mastery per topic survives
between app restarts / sessions. No SQL needed for a project this size.
"""

import json
import os
from datetime import datetime

from config import PROGRESS_FILE, DATA_DIR


def _ensure_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"students": {}}, f)


def load_progress():
    _ensure_file()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(data):
    _ensure_file()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _topic_key(class_, subject, topic):
    return f"{class_}|{subject}|{topic}"


def get_topic_record(student, class_, subject, topic):
    data = load_progress()
    student_rec = data["students"].get(student, {"topics": {}})
    key = _topic_key(class_, subject, topic)
    return student_rec["topics"].get(key, {"level": 1, "mastery": 0, "attempts": []})


def record_attempt(student, class_, subject, topic, score, action, new_level):
    """Save the outcome of one question-answer round and update mastery."""
    data = load_progress()
    students = data.setdefault("students", {})
    student_rec = students.setdefault(student, {"topics": {}})
    key = _topic_key(class_, subject, topic)
    topic_rec = student_rec["topics"].setdefault(
        key, {"level": 1, "mastery": 0, "attempts": []}
    )

    topic_rec["attempts"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "score": score,
            "action": action,
        }
    )
    prev_mastery = topic_rec.get("mastery", 0)
    topic_rec["mastery"] = round(0.6 * prev_mastery + 0.4 * score)
    topic_rec["level"] = new_level

    save_progress(data)
    return topic_rec


def get_student_summary(student):
    """Returns a flat list of (topic_key, mastery, attempts_count) for dashboards."""
    data = load_progress()
    student_rec = data["students"].get(student, {"topics": {}})
    rows = []
    for key, rec in student_rec["topics"].items():
        rows.append(
            {
                "topic": key.replace("|", " > "),
                "mastery": rec.get("mastery", 0),
                "level": rec.get("level", 1),
                "attempts": len(rec.get("attempts", [])),
            }
        )
    return rows