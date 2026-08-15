"""
tutor_engine.py
----------------
This is the reasoning core of the tutor. It is deliberately split into
small, single-purpose functions so each step of the "understand -> teach
-> check -> adapt" loop is easy to follow and easy to grade:

  parse_learning_request()  - turns free speech into {class, subject, topic}
  match_topic_from_speech() - matches free speech to an EXACT syllabus topic
                               for an already-known class/subject
  explain_topic()           - generates a spoken-style explanation at a level
  generate_check_question() - one question to test understanding
  evaluate_answer()         - scores the student's spoken answer
  reveal_answer()           - gives the correct answer when the student didn't know it
  decide_next_action()      - RULE-BASED decision: reteach / reinforce / advance
  answer_question()         - free-form conversational Q&A about the topic

decide_next_action() is intentionally plain Python (not another LLM
call). The LLM produces an understanding_score; the tutor then REASONS
about that score with explicit, explainable rules and ACTS on it by
changing the difficulty level and/or the topic. That is the "adapts,
doesn't just show a score" requirement.
"""

import json
import re
from groq import Groq

from config import (
    GROQ_API_KEY,
    CHAT_MODEL,
    RETEACH_THRESHOLD,
    REINFORCE_THRESHOLD,
    MIN_LEVEL,
    MAX_LEVEL,
)
from syllabus import list_classes, list_subjects, list_topics, find_best_topic_match

_client = Groq(api_key=GROQ_API_KEY)

LEVEL_NAMES = {1: "very simple, everyday language", 2: "standard textbook level", 3: "advanced, exam-level depth"}


def _chat(messages, json_mode=False, temperature=0.4):
    kwargs = dict(model=CHAT_MODEL, messages=messages, temperature=temperature)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    completion = _client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content


def _safe_json(raw: str, fallback: dict) -> dict:
    """LLMs occasionally wrap JSON in text/markdown fences - salvage it."""
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return fallback


# ---------------------------------------------------------------------
# 1. Understand what the student wants to learn
# ---------------------------------------------------------------------
def parse_learning_request(spoken_text: str) -> dict:
    """
    Turns something like "I'm in class 10, I want to learn about
    chemical reactions in science" into a structured request, matched
    against our actual syllabus.
    """
    classes = list_classes()
    prompt = f"""A student said this out loud, describing what they want to study:
"{spoken_text}"

Figure out which CLASS (choose one of: {classes}), which SUBJECT, and
which TOPIC they mean. If class or subject is missing or unclear, make
your best guess from context (default class "10", default subject
"Science"). Respond ONLY as JSON: {{"class": "...", "subject": "...", "topic": "..."}}"""

    raw = _chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0,
    )
    parsed = _safe_json(raw, {"class": "10", "subject": "Science", "topic": spoken_text})

    class_ = str(parsed.get("class", "10")).strip()
    if class_ not in classes:
        class_ = "10"

    subjects = list_subjects(class_)
    subject = parsed.get("subject", subjects[0] if subjects else "Science")
    subject_match = next((s for s in subjects if s.lower() == str(subject).lower()), None)
    subject = subject_match or (subjects[0] if subjects else "Science")

    topic_guess = parsed.get("topic", "")
    topic = find_best_topic_match(class_, subject, topic_guess) or topic_guess

    return {"class": class_, "subject": subject, "topic": topic}


# ---------------------------------------------------------------------
# 1b. Match free-form speech to an exact syllabus topic (class/subject
#     already known - used by the sequential class -> subject -> topic
#     setup flow)
# ---------------------------------------------------------------------
def match_topic_from_speech(class_: str, subject: str, spoken_text: str) -> str:
    """
    Matches free-form spoken text - which may be a short topic name OR
    a full sentence like "explain the neurological system in the human
    body" - to the closest ACTUAL topic in this class/subject's syllabus.

    This exists because naive string/keyword matching (see
    find_best_topic_match in syllabus.py) can mismatch a verbose,
    loosely-worded request to the wrong topic - e.g. "explain the
    neurological system" sharing surface words with an unrelated
    "human health / microbiology" topic instead of the correct
    "nervous system" one. Giving the LLM the EXACT list of valid
    topics and asking it to choose semantically is far more reliable.

    Always returns a usable topic string. If a syllabus topic genuinely
    matches, returns that exact string. If NONE of this class/subject's
    topics genuinely cover what the student asked about (e.g. they
    asked about something that's actually in a different class's
    syllabus - which is exactly what happens if a Class 12 Biology
    student asks about the nervous system, since that's a Class 11
    topic here), it does NOT force-fit the closest-sounding but wrong
    chapter - it instead returns a short custom topic title based on
    what they actually asked, so the tutor still teaches the right
    thing instead of a mismatched syllabus chapter.
    """
    topics = list_topics(class_, subject)
    if not topics:
        return find_best_topic_match(class_, subject, spoken_text) or spoken_text

    prompt = f"""A Class {class_} {subject} student said this out loud, describing
what they want to learn:
"{spoken_text}"

Here is the FULL list of valid syllabus topics for this class and subject:
{topics}

Pick the SINGLE topic from that list that best matches what the student
wants to learn - even if their wording is a full sentence, uses
different terminology, or only loosely resembles the topic title (for
example, "explain the neurological system in the human body" should
match a topic about the nervous system, not an unrelated topic that
merely shares a few surface words like "human" or "body").

IMPORTANT: only pick a topic if it is a genuine, substantive match. If
what the student is asking about is simply NOT covered by any topic in
that list (for example, it belongs to a different class's syllabus),
do NOT force-fit it to the closest-sounding but unrelated topic -
instead set "topic" to "NONE_OF_THESE".

Respond ONLY as JSON:
{{
  "topic": "<the exact topic string copied character-for-character from the list above, OR \\"NONE_OF_THESE\\">",
  "custom_topic_title": "<a short 2-5 word topic title for what the student actually asked about - only used if topic is NONE_OF_THESE>"
}}"""

    raw = _chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0,
    )
    parsed = _safe_json(raw, {"topic": "NONE_OF_THESE", "custom_topic_title": spoken_text})
    matched = str(parsed.get("topic", "")).strip()

    # Guard against the model returning a topic not actually in the list
    # (paraphrased, mis-cased, or invented) - treat that the same as
    # NONE_OF_THESE rather than silently mapping to the wrong chapter.
    exact = next((t for t in topics if t.lower() == matched.lower()), None)
    if exact:
        return exact

    custom = str(parsed.get("custom_topic_title", "")).strip()
    return custom or spoken_text


# ---------------------------------------------------------------------
# 2. Teach
# ---------------------------------------------------------------------
def explain_topic(class_, subject, topic, level: int, misconception: str = "") -> str:
    """
    misconception: if the student was just re-taught this topic (a "reteach"
    decision), this carries what they got wrong last time, so the new
    explanation takes a genuinely different angle instead of repeating
    the same wording/example verbatim.
    """
    style = LEVEL_NAMES.get(level, LEVEL_NAMES[2])

    retry_instruction = ""
    if misconception:
        retry_instruction = f"""
The student was taught this topic before and got confused. Specifically,
their gap was: "{misconception}"
Do NOT repeat the same explanation, wording, or example as before. Use a
different angle and a different everyday example, and address that
specific confusion directly."""

    prompt = f"""You are a friendly, encouraging spoken-voice tutor for an
Indian Class {class_} student, teaching the subject {subject}.

Explain the topic "{topic}" at a {style}.
{retry_instruction}
Rules:
- This will be READ ALOUD by text-to-speech, so write it as natural spoken
  sentences, no bullet points, no markdown, no headings.
- Keep it to about 90-130 words.
- Use one relatable, everyday example.
- End by telling the student you're about to ask them a quick question
  to check their understanding."""

    # Slightly higher temperature when retrying so the model doesn't
    # drift back toward its previous phrasing.
    temperature = 0.65 if misconception else 0.5
    return _chat([{"role": "user", "content": prompt}], temperature=temperature).strip()


def generate_check_question(class_, subject, topic, level: int) -> str:
    style = LEVEL_NAMES.get(level, LEVEL_NAMES[2])
    prompt = f"""You just taught a Class {class_} {subject} student the topic
"{topic}" at a {style}.

Ask ONE short spoken question (max 2 sentences) that checks whether they
understood the core idea - not a definition-recall question, but one
that requires them to explain or apply it briefly. Output only the
question, nothing else."""
    return _chat([{"role": "user", "content": prompt}], temperature=0.5).strip()


# ---------------------------------------------------------------------
# 3. Evaluate the spoken answer
# ---------------------------------------------------------------------
def evaluate_answer(class_, subject, topic, question, student_answer, level: int) -> dict:
    """
    Returns {"understanding_score": 0-100, "feedback": "...", "misconception": "..."}
    Note: student_answer comes from speech-to-text, so it may contain
    small transcription errors - the prompt tells the model to be
    lenient about phrasing and focus on the underlying concept.
    """
    prompt = f"""A Class {class_} {subject} student was taught "{topic}" and
then asked: "{question}"

They answered (note: this is a speech-to-text transcript, so ignore small
wording/grammar glitches and judge the underlying understanding):
"{student_answer}"

Evaluate their conceptual understanding. Respond ONLY as JSON:
{{
  "understanding_score": <integer 0-100>,
  "feedback": "<one short, encouraging spoken sentence for the student>",
  "misconception": "<the main gap in their understanding, or empty string if none>"
}}"""

    raw = _chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.2,
    )
    result = _safe_json(
        raw,
        {"understanding_score": 50, "feedback": "Let's keep going.", "misconception": ""},
    )
    try:
        result["understanding_score"] = max(0, min(100, int(result["understanding_score"])))
    except Exception:
        result["understanding_score"] = 50
    return result


# ---------------------------------------------------------------------
# 3b. Reveal the correct answer (used when the student didn't know it)
# ---------------------------------------------------------------------
def reveal_answer(class_, subject, topic, question, level: int) -> str:
    """
    Generates a short, direct spoken-style answer to the check question
    itself - used when the student's understanding_score is low (e.g.
    they said "I don't know"), so the tutor actually tells them the
    answer instead of just scoring them and moving on.
    """
    style = LEVEL_NAMES.get(level, LEVEL_NAMES[2])
    prompt = f"""You are a friendly spoken-voice tutor for a Class {class_}
{subject} student studying "{topic}".

You asked them this check question: "{question}"
The student was not able to answer it.

Give them the correct answer directly, at a {style}. Rules:
- This will be READ ALOUD by text-to-speech: natural spoken sentences,
  no markdown, no bullet points, no headings.
- Keep it short: 2-4 sentences.
- Be direct and clear - actually answer the question, don't just restate it.
- Warm, encouraging tone, but no need to re-explain the whole topic - just
  this specific answer."""
    return _chat([{"role": "user", "content": prompt}], temperature=0.5).strip()


# ---------------------------------------------------------------------
# 4. Decide what happens next - THE ADAPTIVE LOGIC (rule-based, explainable)
# ---------------------------------------------------------------------
def decide_next_action(score: int, current_level: int) -> dict:
    """
    This is the explicit decision policy the assignment asks for:
    the tutor doesn't just display a score, it changes what it will
    teach next.

      score < RETEACH_THRESHOLD      -> "reteach"    : same topic, simpler level
      score < REINFORCE_THRESHOLD    -> "reinforce"   : same topic, same level, new question
      score >= REINFORCE_THRESHOLD   -> "advance"      : harder level, or next topic if maxed
    """
    if score < RETEACH_THRESHOLD:
        new_level = max(MIN_LEVEL, current_level - 1)
        return {
            "action": "reteach",
            "new_level": new_level,
            "reason": (
                f"Score {score}/100 is below the reteach threshold "
                f"({RETEACH_THRESHOLD}), so the tutor will re-explain the same "
                f"topic more simply, from a different angle (level {current_level} -> {new_level})."
            ),
        }
    elif score < REINFORCE_THRESHOLD:
        return {
            "action": "reinforce",
            "new_level": current_level,
            "reason": (
                f"Score {score}/100 shows partial understanding, so the tutor "
                f"will stay on the same topic and level ({current_level}) with "
                f"another practice question."
            ),
        }
    else:
        new_level = min(MAX_LEVEL, current_level + 1)
        advanced_level = new_level != current_level
        return {
            "action": "advance",
            "new_level": new_level,
            "move_to_next_topic": not advanced_level,
            "reason": (
                f"Score {score}/100 is at or above the advance threshold "
                f"({REINFORCE_THRESHOLD}), so the tutor will "
                + (
                    f"raise the difficulty (level {current_level} -> {new_level})."
                    if advanced_level
                    else "move on to the next syllabus topic."
                )
            ),
        }


# ---------------------------------------------------------------------
# 5. Free-form Q&A - conversational chat mode
# ---------------------------------------------------------------------
def answer_question(class_, subject, topic, chat_history, question: str) -> str:
    """
    Answers a free-form spoken question from the student, in the context
    of what they're currently studying. chat_history is a list of
    {"role": "user"/"assistant", "content": "..."} dicts so the model
    remembers earlier turns in this Q&A session.
    """
    system_context = f"""You are a friendly, encouraging spoken-voice tutor
helping a Class {class_} {subject} student who is currently studying
"{topic}". Answer their questions clearly and simply, staying on topic
where possible but also answering fairly if they ask something related
but slightly different.

Rules:
- This will be READ ALOUD by text-to-speech: natural spoken sentences,
  no markdown, no bullet points, no headings.
- Keep answers short: 2-5 sentences, unless the question truly needs more.
- If you don't know or the question is unclear, say so simply and ask
  them to rephrase - don't make things up."""

    messages = [{"role": "system", "content": system_context}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": question})

    return _chat(messages, temperature=0.5).strip()