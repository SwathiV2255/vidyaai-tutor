"""
app.py
------
Streamlit UI. Owns the session "state machine" that drives one full
teach -> check -> adapt loop, plus a free-form voice Q&A chat mode:

    setup -> explain -> ask_question -> evaluate -> (loop) -> ... -> finished
                  ^                                     |
                  |________________ chat ________________|
                    (💬 Ask anything, embedded on every stage)

Voice is the primary channel in and out:
  - IN:  st.audio_input (mic recording) -> voice_io.transcribe()
  - OUT: tutor_engine text -> voice_io.synthesize() -> play_audio()

play_audio() falls back to the BROWSER's built-in Web Speech API
(speechSynthesis) if Groq's TTS quota is exhausted, so a rate limit
never crashes the app mid-demo AND the student still hears the tutor
speak - just with a more robotic voice instead of Orpheus.

A global mute toggle (top of the page) silences all tutor audio - both
Groq/Orpheus playback and the browser speech fallback - showing text
only instead.
"""

import json

import streamlit as st
import streamlit.components.v1 as components

import syllabus
import tutor_engine
import voice_io
from progress_store import record_attempt, get_topic_record
from config import GROQ_API_KEY

st.set_page_config(page_title="Voice AI Tutor", page_icon="🎙️", layout="centered")

# ----------------------------------------------------------------------
# Theme: deep navy-to-blue gradient background, white text, glass
# cards, pill buttons, chat bubbles.
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    /* App background: deep navy fading into a rich blue */
    .stApp {
        background: linear-gradient(160deg, #050b1f 0%, #0b1d3a 30%, #123059 60%, #1b4a86 85%, #2563ac 100%);
        background-attachment: fixed;
    }

    /* White text reads well on the dark background */
    .stApp, .stApp p, .stApp span, .stApp label, .stMarkdown, .stCaption {
        color: #f4f8ff;
    }
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Sidebar: darker navy glass panel */
    section[data-testid="stSidebar"] {
        background: rgba(5, 12, 30, 0.6);
        backdrop-filter: blur(18px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    section[data-testid="stSidebar"] * {
        color: #f4f8ff !important;
    }

    /* Bordered containers ("cards") become navy glass panels */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 24px !important;
        padding: 8px 4px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }

    /* Buttons: pill-shaped, bright blue gradient */
    .stButton > button {
        background: linear-gradient(90deg, #2f80ed, #56ccf2) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 0.6em 1.6em !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 18px rgba(47, 128, 237, 0.45);
        transition: transform 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px) scale(1.02);
        box-shadow: 0 6px 22px rgba(47, 128, 237, 0.6);
    }

    /* Form submit buttons (e.g. the sidebar "Start" button) render under a
       different wrapper than .stButton, so they didn't pick up the button
       styling above and were showing white text on white - fix that here. */
    div[data-testid="stFormSubmitButton"] button {
        color: #2f80ed !important;
        font-weight: 600 !important;
        border-radius: 999px !important;
    }
    div[data-testid="stFormSubmitButton"] button p {
        color: #2f80ed !important;
    }

    /* Text input + selectboxes: dark glass style, blue typed text */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.10) !important;
        color: #56ccf2 !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
    }

    /* Mic / audio recorder widget: rounded glass frame around it */
    div[data-testid="stAudioInput"] {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 999px;
        padding: 10px 18px;
        box-shadow: 0 0 24px rgba(86, 204, 242, 0.25);
    }

    /* Progress bars */
    div[data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #2f80ed, #56ccf2) !important;
    }

    /* Chat bubbles (custom HTML, used in chat stage) */
    .chat-row { display: flex; margin: 10px 0; }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.assistant { justify-content: flex-start; }
    .chat-bubble {
        max-width: 78%;
        padding: 12px 18px;
        border-radius: 20px;
        line-height: 1.4;
        font-size: 0.95rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    }
    .chat-bubble.user {
        background: linear-gradient(135deg, #2f80ed, #56ccf2);
        color: #ffffff;
        border-bottom-right-radius: 6px;
    }
    .chat-bubble.assistant {
        background: rgba(255, 255, 255, 0.10);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #f4f8ff;
        border-bottom-left-radius: 6px;
    }
    .chat-label {
        font-size: 0.7rem;
        opacity: 0.65;
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_chat_bubble(role: str, content: str):
    """Renders one chat turn as a styled message bubble (user right, tutor left)."""
    label = "You" if role == "user" else "Tutor"
    st.markdown(
        f"""
        <div class="chat-row {role}">
            <div class="chat-bubble {role}">
                <div class="chat-label">{label}</div>
                {content}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def speak_in_browser(text: str):
    """
    Fallback voice path: speaks `text` using the browser's built-in
    Web Speech API (window.speechSynthesis). This has NO daily quota
    since it runs entirely client-side - it's the backup for when
    Groq's Orpheus TTS free-tier limit is exhausted.
    """
    if not text:
        return

    safe_text = json.dumps(text)

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const win = window.parent;
                const synth = win.speechSynthesis;
                if (!synth) return;
                const TEXT = {safe_text};

                function doSpeak() {{
                    try {{ synth.resume(); }} catch (e) {{}}
                    const utter = new win.SpeechSynthesisUtterance(TEXT);
                    utter.rate = 1.0;
                    utter.pitch = 1.0;
                    synth.speak(utter);

                    setTimeout(function() {{
                        if (!synth.speaking && !synth.pending) {{
                            try {{ synth.speak(utter); }} catch (e) {{}}
                        }}
                    }}, 300);
                }}

                if (synth.speaking || synth.pending) {{
                    synth.cancel();
                    setTimeout(doSpeak, 250);
                }} else {{
                    setTimeout(doSpeak, 80);
                }}
            }} catch (e) {{
                console.warn("Browser TTS fallback failed:", e);
            }}
        }})();
        </script>
        """,
        height=0,
    )


def inject_barge_in_listener():
    """
    "Barge-in" support: the instant the student taps ANY mic/record
    widget, immediately stop whatever the tutor is currently saying.
    """
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const win = window.parent;
            if (doc.__voiceInterruptHooked) return;
            doc.__voiceInterruptHooked = true;

            function stopTutorVoice() {
                try {
                    if (win.speechSynthesis) win.speechSynthesis.cancel();
                } catch (e) {}
                try {
                    doc.querySelectorAll('audio').forEach(function(a) {
                        a.pause();
                    });
                } catch (e) {}
            }

            doc.addEventListener('click', function(e) {
                const micWidget = e.target.closest('[data-testid="stAudioInput"]');
                if (micWidget) {
                    stopTutorVoice();
                }
            }, true);

            setInterval(function() {
                try {
                    if (win.speechSynthesis && win.speechSynthesis.speaking) {
                        win.speechSynthesis.pause();
                        win.speechSynthesis.resume();
                    }
                } catch (e) {}
            }, 10000);
        })();
        </script>
        """,
        height=0,
    )


def enforce_mute():
    """If the mute toggle is on, immediately stop any audio/speech currently playing in the browser."""
    components.html(
        """
        <script>
        (function() {
            const win = window.parent;
            try { if (win.speechSynthesis) win.speechSynthesis.cancel(); } catch (e) {}
            try {
                win.document.querySelectorAll('audio').forEach(function(a) { a.pause(); });
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


def play_audio(audio_bytes: bytes, text: str = ""):
    """
    Plays TTS audio if we have it (Groq/Orpheus - primary, better quality).
    Falls back to browser speech synthesis if audio_bytes is empty.
    Does nothing but show a caption if the mute toggle is on.
    """
    if st.session_state.get("voice_muted"):
        st.caption("🔇 Muted — read the text instead")
        return
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav", autoplay=True)
    elif text:
        speak_in_browser(text)
    else:
        st.caption("🔇 Voice is temporarily unavailable — read the text above instead.")


inject_barge_in_listener()


defaults = {
    "stage": "setup",
    "setup_step": "class",   # "class" -> "subject" -> "topic_chat"
    "student": "",
    "voice_muted": False,
    "class_": None,
    "subject": None,
    "topic": None,
    "level": 1,
    "explanation_text": "",
    "explanation_audio": b"",
    "explanation_cache_key": None,
    "question_text": "",
    "question_audio": b"",
    "question_cache_key": None,
    "feedback_text": "",
    "feedback_audio": b"",
    "last_decision": None,
    "round_counter": 0,
    # --- ask-anything chat state ---
    "chat_history": [],       # [{"role": "user"/"assistant", "content": "..."}]
    "chat_topic_key": None,   # (class, subject, topic) the chat_history currently belongs to
    "chat_last_processed_sig": None,  # raw bytes of the last recording we already answered
    "pending_misconception": "",  # carried into explain_topic() after a reteach
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def go_to_setup():
    for k in ["class_", "subject", "topic", "level", "explanation_cache_key",
              "question_cache_key", "last_decision", "chat_history",
              "chat_topic_key", "chat_last_processed_sig", "pending_misconception"]:
        st.session_state[k] = defaults[k]
    st.session_state["setup_step"] = "class"
    st.session_state["stage"] = "setup"


def render_ask_anything(class_, subject, topic):
    """
    Embedded voice chat: lives on the same page as whatever lesson
    stage the student is in (explain / quick check / evaluate).
    Student taps the mic, asks a question, gets a spoken + text
    answer, and can immediately record the next question in the SAME
    widget.

    Every question and answer stays visible, stacked in order (newest
    at the bottom).
    """
    topic_key = (class_, subject, topic)
    if st.session_state.get("chat_topic_key") != topic_key:
        st.session_state.chat_history = []
        st.session_state.chat_topic_key = topic_key
        st.session_state.chat_last_processed_sig = None

    with st.container(border=True):
        st.subheader("💬 Ask anything")
        st.caption(f"About: Class {class_} · {subject} · {topic}")

        history_slot = st.container()

        # IMPORTANT: this key is FIXED for the whole topic - it does NOT
        # change per question. New recordings are detected by comparing
        # raw audio bytes to the last one we already processed, instead
        # of swapping widget keys (which caused a mic-remount bug).
        audio = st.audio_input(
            "🎤 Tap to ask a question",
            key=f"chat_audio_{class_}_{subject}_{topic}",
        )

        new_answer_audio, new_answer_text = None, None

        if audio is not None:
            sig = audio.getvalue()
            if sig != st.session_state.get("chat_last_processed_sig"):
                st.session_state.chat_last_processed_sig = sig

                with st.spinner("Listening..."):
                    question = voice_io.transcribe(audio)

                if not question:
                    st.warning("I couldn't hear anything - please try recording again.")
                else:
                    with st.spinner("Thinking..."):
                        answer = tutor_engine.answer_question(
                            class_, subject, topic, st.session_state.chat_history, question
                        )
                        answer_audio = voice_io.synthesize(answer)

                    st.session_state.chat_history.append({"role": "user", "content": question})
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    new_answer_audio, new_answer_text = answer_audio, answer

        with history_slot:
            for msg in st.session_state.chat_history:
                render_chat_bubble(msg["role"], msg["content"])
            if new_answer_text:
                play_audio(new_answer_audio, new_answer_text)

        if st.session_state.chat_history:
            st.caption("🎙️ Tap the recorder above again to ask another question.")


# ----------------------------------------------------------------------
# Sidebar: identity
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Student")

    if not st.session_state.student:
        # A form keeps what you type fully local until you submit -
        # nothing touches session_state.student mid-keystroke, so there's
        # no risk of the field flashing blank on the rerun after Enter.
        with st.form("name_form", clear_on_submit=False):
            name_input = st.text_input("Your name")
            submitted = st.form_submit_button("Start")
            if submitted and name_input.strip():
                st.session_state.student = name_input.strip()
                st.rerun()
    else:
        # Once a name is set, there's no editable text field left at
        # all - just a static display - so there's nothing that could
        # ever appear to clear itself.
        st.write(f"👋 **{st.session_state.student}**")
        if st.button("Change name"):
            st.session_state.student = ""
            st.rerun()

    st.divider()
    if st.button("🔄 Start a new topic"):
        go_to_setup()
        st.rerun()

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing. Add it to your .env file and restart the app.")
    st.stop()

title_col, mute_col = st.columns([5, 1])
with title_col:
    st.title("🎙️ Voice AI Learning Tutor")
    st.caption("Classes 8–12 · Speak to learn, get quizzed out loud, and the tutor adapts to you.")
with mute_col:
    st.toggle("🔇 Mute", key="voice_muted")
    if st.session_state.voice_muted:
        enforce_mute()


# ----------------------------------------------------------------------
# STAGE: setup - student describes what they want to learn, by voice
# ----------------------------------------------------------------------
if st.session_state.stage == "setup":
    if not st.session_state.student:
        st.info("Enter your name in the sidebar first, then tell the tutor what you want to learn.")
        st.stop()

    with st.container(border=True):

        if st.session_state.setup_step == "class":
            render_chat_bubble("assistant", "Hi! Which class are you in?")
            classes = syllabus.list_classes()
            cols = st.columns(len(classes))
            for col, c in zip(cols, classes):
                with col:
                    if st.button(f"Class {c}", key=f"pick_class_{c}"):
                        st.session_state.class_ = c
                        st.session_state.setup_step = "subject"
                        st.rerun()

        elif st.session_state.setup_step == "subject":
            render_chat_bubble("user", f"Class {st.session_state.class_}")
            render_chat_bubble("assistant", "Great - and which subject would you like to study?")
            subs = syllabus.list_subjects(st.session_state.class_)
            cols = st.columns(len(subs))
            for col, s in zip(cols, subs):
                with col:
                    if st.button(s, key=f"pick_subject_{s}"):
                        st.session_state.subject = s
                        st.session_state.setup_step = "topic_chat"
                        st.rerun()
            if st.button("⬅ Change class"):
                st.session_state.setup_step = "class"
                st.rerun()

        elif st.session_state.setup_step == "topic_chat":
            render_chat_bubble("user", f"Class {st.session_state.class_}")
            render_chat_bubble("user", st.session_state.subject)
            render_chat_bubble("assistant", "Perfect. What topic would you like to learn about? You can just tell me.")

            audio = st.audio_input("🎤 Tap to record, then tap again to stop")
            if audio is not None:
                with st.spinner("Listening..."):
                    spoken = voice_io.transcribe(audio)

                if not spoken:
                    st.warning("I couldn't hear anything - please try recording again.")
                else:
                    render_chat_bubble("user", spoken)
                    with st.spinner("Finding that topic..."):
                        topic = tutor_engine.match_topic_from_speech(
                            st.session_state.class_, st.session_state.subject, spoken
                        )

                    existing = get_topic_record(
                        st.session_state.student, st.session_state.class_,
                        st.session_state.subject, topic,
                    )
                    st.session_state.topic = topic
                    st.session_state.level = existing.get("level", 1)
                    st.session_state.stage = "explain"
                    st.rerun()

            with st.expander("Prefer to pick from a list?"):
                topics = syllabus.list_topics(st.session_state.class_, st.session_state.subject)
                t = st.selectbox("Topic", topics, key="manual_topic")
                if st.button("Start this topic"):
                    existing = get_topic_record(
                        st.session_state.student, st.session_state.class_,
                        st.session_state.subject, t,
                    )
                    st.session_state.topic = t
                    st.session_state.level = existing.get("level", 1)
                    st.session_state.stage = "explain"
                    st.rerun()

            if st.button("⬅ Change subject"):
                st.session_state.setup_step = "subject"
                st.rerun()


# ----------------------------------------------------------------------
# STAGE: explain - tutor teaches the topic out loud
# ----------------------------------------------------------------------
elif st.session_state.stage == "explain":
    class_, subject, topic, level = (
        st.session_state.class_, st.session_state.subject,
        st.session_state.topic, st.session_state.level,
    )
    with st.container(border=True):
        st.subheader(f"📘 Class {class_} · {subject}")
        st.write(f"**Topic:** {topic}  ·  **Level:** {level}/3")

        misconception = st.session_state.pending_misconception
        cache_key = (topic, level, "explain", misconception)
        if st.session_state.explanation_cache_key != cache_key:
            with st.spinner("Preparing your explanation..."):
                text = tutor_engine.explain_topic(class_, subject, topic, level, misconception=misconception)
                audio_bytes = voice_io.synthesize(text)
            st.session_state.explanation_text = text
            st.session_state.explanation_audio = audio_bytes
            st.session_state.explanation_cache_key = cache_key
            st.session_state.pending_misconception = ""

        play_audio(st.session_state.explanation_audio, st.session_state.explanation_text)
        st.write(st.session_state.explanation_text)

        if st.button("✅ I'm ready - ask me a question"):
            st.session_state.stage = "ask_question"
            st.session_state.question_cache_key = None
            st.rerun()

    render_ask_anything(class_, subject, topic)


# ----------------------------------------------------------------------
# STAGE: ask_question - tutor asks, student answers by voice
# ----------------------------------------------------------------------
elif st.session_state.stage == "ask_question":
    class_, subject, topic, level = (
        st.session_state.class_, st.session_state.subject,
        st.session_state.topic, st.session_state.level,
    )
    with st.container(border=True):
        st.subheader("❓ Quick check")

        cache_key = (topic, level, st.session_state.round_counter)
        if st.session_state.question_cache_key != cache_key:
            with st.spinner("Thinking of a question..."):
                q_text = tutor_engine.generate_check_question(class_, subject, topic, level)
                q_audio = voice_io.synthesize(q_text)
            st.session_state.question_text = q_text
            st.session_state.question_audio = q_audio
            st.session_state.question_cache_key = cache_key

        play_audio(st.session_state.question_audio, st.session_state.question_text)
        st.write(f"**Question:** {st.session_state.question_text}")

        answer_audio = st.audio_input(
            "🎤 Record your answer",
            key=f"answer_{topic}_{level}_{st.session_state.round_counter}",
        )
        if answer_audio is not None:
            st.session_state["_pending_answer"] = answer_audio
            st.session_state.stage = "evaluate"
            st.rerun()

    render_ask_anything(class_, subject, topic)


# ----------------------------------------------------------------------
# STAGE: evaluate - transcribe, score, and ADAPT (reteach/reinforce/advance)
# ----------------------------------------------------------------------
elif st.session_state.stage == "evaluate":
    class_, subject, topic, level = (
        st.session_state.class_, st.session_state.subject,
        st.session_state.topic, st.session_state.level,
    )
    with st.container(border=True):
        with st.spinner("Listening to your answer..."):
            student_answer = voice_io.transcribe(st.session_state.get("_pending_answer"))

        st.write(f"**You answered:** {student_answer if student_answer else '_(nothing heard - treated as no answer)_'}")

        with st.spinner("Evaluating your understanding..."):
            result = tutor_engine.evaluate_answer(
                class_, subject, topic, st.session_state.question_text, student_answer, level
            )
            decision = tutor_engine.decide_next_action(result["understanding_score"], level)

        correct_answer_text = ""
        if decision["action"] == "reteach":
            with st.spinner("Getting you the answer..."):
                correct_answer_text = tutor_engine.reveal_answer(
                    class_, subject, topic, st.session_state.question_text, level
                )

        record_attempt(
            st.session_state.student, class_, subject, topic,
            result["understanding_score"], decision["action"], decision["new_level"],
        )

        st.write(f"💬 {result['feedback']}")
        if result.get("misconception"):
            st.caption(f"Gap to work on: {result['misconception']}")
        if correct_answer_text:
            st.write(f"✅ **Here's the answer:** {correct_answer_text}")

        spoken_text = f"{result['feedback']} {correct_answer_text}".strip()
        feedback_audio = voice_io.synthesize(spoken_text)
        play_audio(feedback_audio, spoken_text)

        if st.button("Continue"):
            st.session_state.round_counter += 1
            action = decision["action"]

            if action == "reteach":
                st.session_state.level = decision["new_level"]
                st.session_state.pending_misconception = result.get("misconception", "")
                st.session_state.stage = "explain"

            elif action == "reinforce":
                st.session_state.level = decision["new_level"]
                st.session_state.stage = "ask_question"

            else:  # advance
                st.session_state.level = decision["new_level"]
                if decision.get("move_to_next_topic"):
                    nxt = syllabus.next_topic(class_, subject, topic)
                    if nxt is None:
                        st.session_state.stage = "finished"
                    else:
                        st.session_state.topic = nxt
                        st.session_state.level = 1
                        st.session_state.explanation_cache_key = None
                        st.session_state.stage = "explain"
                else:
                    st.session_state.explanation_cache_key = None
                    st.session_state.stage = "explain"

            st.session_state.pop("_pending_answer", None)
            st.rerun()

    render_ask_anything(class_, subject, topic)


# ----------------------------------------------------------------------
# STAGE: finished - reached the end of this subject's syllabus
# ----------------------------------------------------------------------
elif st.session_state.stage == "finished":
    st.success(
        f"🎉 You've completed every topic covered here for "
        f"Class {st.session_state.class_} {st.session_state.subject}!"
    )
    st.write("Check the sidebar to see your mastery across all topics.")
    if st.button("Learn something else"):
        go_to_setup()
        st.rerun()