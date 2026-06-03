import sys
import os
import re
import json
import time
import random
import textwrap
from collections import deque
from typing import List, Tuple, Optional 

# ---------------------------------------------------------------------------
# Configuration and Constants
# ---------------------------------------------------------------------------

APP_NAME = "LocalGemini"
VERSION = "0.1"

WELCOME_TEXT = f"{APP_NAME} v{VERSION} — Local study companion. Type /help for commands."
SESSION_SAVE = "localgemini_session.json"

# A very small safety word list to avoid generating harmful content.
# This is intentionally conservative; the assistant will refuse if a user asks for
# instructions that appear illegal, unsafe, or clearly malicious.
DISALLOWED_KEYWORDS = [
    "bomb",
    "explosive",
    "kill",
    "assassinat",
    "illegal",
    "weapon",
    "harm",
    "suicide",
    "drugs",
    "attack",
]

# Default examples and heuristics
DEFAULT_TOPIC = "general study"
SAMPLE_PROMPTS = [
    "Explain the core idea behind photosynthesis.",
    "Give me flashcards for the main causes of World War I.",
    "Make a 3-question quiz about linear algebra basics.",
]

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def random_choice(items):
    return random.choice(items) if items else None


def wrap(text, width=78):
    return "\n".join(textwrap.wrap(text, width=width))


def sanitize_input(text: str) -> str:
    return text.strip()


def contains_disallowed(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in DISALLOWED_KEYWORDS)

# Very naive sentence splitter
def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\\s+", text) if s.strip()]

# Extract keywords by simple frequency of words after stopword removal
STOPWORDS = set("""
 a about above after again against all am an and any are aren't as at be because been before being
 but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few for
 from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
 himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my
 myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll
 she's should shouldn't so some such than that that's the their theirs them themselves then there there's these they
 they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're we've were
 weren't what what's when when's where where's which while who who's whom why why's with won't would wouldn't you you'd
 you'll you're you've your yours yourself yourselves
""".split())


def extract_keywords(text: str, max_keywords: int = 8) -> List[str]:
    words = re.findall(r"\\w+", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words[:max_keywords]]


class LocalGemini:
    def __init__(self):
        self.topic = DEFAULT_TOPIC
        self.history = []  # list of (role, text)
        self.short_term_memory = deque(maxlen=200)
        self.session = {"topic": self.topic, "history": [], "created": time.time()}

    def respond(self, text: str) -> str:
        text = sanitize_input(text)
        if not text:
            return "Say something about your study topic or use /help for commands."

        if contains_disallowed(text):
            return "I can't help with that request. Let's keep our study focused and safe."

        intent, payload = self.detect_intent(text)
        if intent == "flashcards":
            return self.handle_flashcards(payload)
        if intent == "quiz":
            return self.handle_quiz(payload)
        if intent == "cheatsheet":
            return self.handle_cheatsheet(payload)
        if intent == "summarize":
            return self.handle_summarize(payload)
        if intent == "example":
            return self.handle_example(payload)
        if intent == "plan":
            return self.handle_plan(payload)
        if intent == "code":
            return self.handle_code(payload)
        if intent == "evaluate":
            return self.handle_evaluate(payload)
        return self.friendly_explain(text)

    # Intent detection is purposely simple: keyword-based rules
    def detect_intent(self, text: str) -> Tuple[str, str]:
        lowercase = text.lower()
        if re.search(r"\\b(code|javascript|python|html|css|snippet|function|program)\\b", lowercase):
            return "code", text
        if re.search(r"\\b(flashcard|flashcards|cards)\\b", lowercase):
            return "flashcards", text
        if re.search(r"\\b(quiz|question|test|practice)\\b", lowercase):
            return "quiz", text
        if re.search(r"\\b(cheat|cheatsheet|cheat-sheet|notes|summary sheet)\\b", lowercase):
            return "cheatsheet", text
        if re.search(r"\\b(summarize|summary)\\b", lowercase):
            return "summarize", text
        if re.search(r"\\b(example|illustrate|apply)\\b", lowercase):
            return "example", text
        if re.search(r"\\b(plan|schedule|strategy|steps)\\b", lowercase):
            return "plan", text
        if re.search(r"\\b(answer|evaluate|grade|correct)\\b", lowercase):
            return "evaluate", text
        return "explain", text

    def friendly_explain(self, text: str) -> str:
        topic = self.guess_topic(text)
        explanation = self.make_explanation(text, topic)
        tools = self.quick_study_tools(topic)
        response = f"{explanation}\n\n{tools}"
        self._save_to_history("assistant", response)
        return response

    def guess_topic(self, text: str) -> str:
        keywords = extract_keywords(text, max_keywords=4)
        if keywords:
            return " ".join(keywords[:2])
        return self.topic

    def make_explanation(self, text: str, topic: str) -> str:
        sentences = split_sentences(text)
        core = sentences[0] if sentences else text
        core_keywords = extract_keywords(core, max_keywords=6)
        if not core_keywords:
            core_keywords = extract_keywords(text, max_keywords=6)

        explanation = (
            f"Here's a clear way to think about {topic}: "
            f"Start with the main idea — {core_keywords[0] if core_keywords else topic} — then connect it to a simple example. "
            "Focus on one concrete case and restate it in one sentence."
        )
        return wrap(explanation)

    def quick_study_tools(self, topic: str) -> str:
        tips = [
            "Write a one-line summary in your own words.",
            "Create one flashcard with question and answer.",
            "Teach the idea aloud for 60 seconds.",
        ]
        return "Study tools: " + " ".join(tips)

    # -----------------------------------------------------------------------
    # Flashcards
    # -----------------------------------------------------------------------
    def handle_flashcards(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        source = self._optional_content_after_keyword(text, ["flashcard", "flashcards", "cards"])
        cards = self.generate_flashcards(topic, source)
        out = f"Flashcards for '{topic}':\n\n"
        for i, (q, a) in enumerate(cards, 1):
            out += f"{i}) Q: {q}\n   A: {a}\n\n"
        self._save_to_history("assistant", out)
        return out

    def generate_flashcards(self, topic: str, source: Optional[str] = None, n: int = 5) -> List[Tuple[str, str]]:
        cards = []
        if source:
            facts = self._split_facts_from_text(source)
            for fact in facts[:n]:
                q = f"What is the main point of: {self._shorten(fact, 60)}?"
                a = self._shorten(fact, 250)
                cards.append((q, a))
        if not cards:
            # Generate generic flashcards for the topic
            prompts = [
                f"Define {topic} in one short sentence.",
                f"Why is {topic} important?",
                f"Give one clear example of {topic} in real life.",
                f"List one common mistake when thinking about {topic}.",
                f"What is a quick memory tip for {topic}?",
            ]
            for p in prompts[:n]:
                cards.append((p, self._short_answer_for_prompt(p, topic)))
        return cards

    # -----------------------------------------------------------------------
    # Quiz generation and evaluation
    # -----------------------------------------------------------------------
    def handle_quiz(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        quiz = self.generate_quiz(topic, n=5)
        out = f"Quiz on '{topic}':\n\n"
        for i, (q, a) in enumerate(quiz, 1):
            out += f"{i}) {q}\n"
        out += "\nType /answer <number> to reveal an answer, or /takequiz to walk through questions interactively."
        self._save_to_history("assistant", out)
        # store last quiz in memory for /answer and /takequiz use
        self.short_term_memory.appendleft({"type": "quiz", "topic": topic, "quiz": quiz})
        return out

    def generate_quiz(self, topic: str, n: int = 5) -> List[Tuple[str, str]]:
        quiz = []
        model_questions = [
            f"Explain the core concept of {topic} in one sentence.",
            f"Name one important application of {topic}.",
            f"Provide one example that demonstrates {topic}.",
            f"State one limitation or counterexample to {topic}.",
            f"How would you test understanding of {topic}?",
        ]
        for p in model_questions[:n]:
            quiz.append((p, self._short_answer_for_prompt(p, topic)))
        return quiz

    def _short_answer_for_prompt(self, prompt: str, topic: str) -> str:
        # Heuristic short answers that are context-aware but generic
        keywords = extract_keywords(topic, max_keywords=3)
        core = keywords[0] if keywords else topic
        if "example" in prompt.lower():
            return f"A simple example is to consider a case where {core} is used to solve a small problem."
        if "importance" in prompt.lower() or "important" in prompt.lower():
            return f"It matters because it helps explain or solve practical issues involving {core}."
        if "define" in prompt.lower() or "explain" in prompt.lower():
            return f"{core.capitalize()} — a concise description focusing on the main idea and its role."
        if "limitation" in prompt.lower() or "counterexample" in prompt.lower():
            return f"A limitation is that {core} may not apply when underlying assumptions are violated."
        return f"A short answer about {topic}."

    def evaluate_answer(self, question: str, user_answer: str) -> Tuple[bool, str]:
        # Very naive evaluation: keyword overlap and length heuristics
        q_keywords = set(extract_keywords(question, max_keywords=6))
        a_keywords = set(extract_keywords(user_answer, max_keywords=8))
        if not q_keywords:
            # cannot evaluate reliably
            return (False, "I can't evaluate that answer automatically.")
        overlap = q_keywords.intersection(a_keywords)
        score = len(overlap) / max(len(q_keywords), 1)
        if score >= 0.5 and len(user_answer.split()) > 6:
            return (True, "Answer seems correct based on key terms.")
        if score >= 0.3:
            return (False, "Some elements are right; expand your answer to include the missing key points.")
        return (False, "The answer doesn't include the main keywords; try focusing on the core idea.")

    # -----------------------------------------------------------------------
    # Cheat sheet
    # -----------------------------------------------------------------------
    def handle_cheatsheet(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        cs = self.generate_cheatsheet(topic)
        out = f"Cheat sheet for '{topic}':\n\n{cs}"
        self._save_to_history("assistant", out)
        return out

    def generate_cheatsheet(self, topic: str) -> str:
        keys = extract_keywords(topic, max_keywords=6)
        core = keys[0] if keys else topic
        bullets = [
            f"Core idea: {core} — short phrase explaining the main point.",
            "Why it matters: Link the idea to a specific application or problem.",
            "Example: One short, concrete example that shows the idea in action.",
            "Quick recall: A one-line mnemonic or phrase to remember it.",
        ]
        return "\n".join("- " + b for b in bullets)

    # -----------------------------------------------------------------------
    # Summarize
    # -----------------------------------------------------------------------
    def handle_summarize(self, text: str) -> str:
        # If user provides content after the keyword, summarize that; otherwise summarize topic
        topic = self._extract_topic_from_text(text)
        content = self._optional_content_after_keyword(text, ["summarize", "summary"]) or topic
        summary = self.summarize_text(content)
        out = f"Summary ({topic}):\n\n{summary}"
        self._save_to_history("assistant", out)
        return out

    def summarize_text(self, text: str, max_sentences: int = 3) -> str:
        # Naive summarization: pick top sentences by keyword density
        sentences = split_sentences(text)
        if not sentences:
            # fallback: shorten the text
            return self._shorten(text, 400)
        keywords = extract_keywords(text, max_keywords=12)
        if not keywords:
            return " ".join(sentences[:max_sentences])
        def score(sentence):
            s_words = set(re.findall(r"\\w+", sentence.lower()))
            return sum(1 for k in keywords if k in s_words)
        ranked = sorted(sentences, key=score, reverse=True)
        chosen = ranked[:max_sentences]
        return " ".join(chosen)

    # -----------------------------------------------------------------------
    # Example/illustration
    # -----------------------------------------------------------------------
    def handle_example(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        example = self.generate_example(topic)
        out = f"Example for '{topic}':\n\n{example}"
        self._save_to_history("assistant", out)
        return out

    def generate_example(self, topic: str) -> str:
        core = extract_keywords(topic, max_keywords=2)
        core_word = core[0] if core else topic
        ex = (
            f"Imagine a simple scenario where {core_word} is used: start with a small, concrete setting, "
            f"walk through one or two steps showing how the idea behaves, and finish with why the outcome matters."
        )
        return wrap(ex)

    # -----------------------------------------------------------------------
    # Study plan
    # -----------------------------------------------------------------------
    def handle_plan(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        plan = self.generate_study_plan(topic)
        out = f"Study plan for '{topic}':\n\n{plan}"
        self._save_to_history("assistant", out)
        return out

    def generate_study_plan(self, topic: str) -> str:
        steps = [
            f"Quick read: read a short section (5-10 min) to identify main ideas about {topic}.",
            "Active recall: write or speak the central idea in one sentence and create one question.",
            "Practice: do a short quiz or application for 10-20 minutes and correct errors.",
        ]
        return "\n".join(f"{i+1}) {s}" for i, s in enumerate(steps))

    # -----------------------------------------------------------------------
    # Code generation helper
    # -----------------------------------------------------------------------
    def handle_code(self, text: str) -> str:
        topic = self._extract_topic_from_text(text)
        lang = self._detect_language(text) or "javascript"
        snippet = self.generate_code_snippet(lang, topic)
        out = f"Code snippet ({lang}) for '{topic}':\n\n{snippet}"
        self._save_to_history("assistant", out)
        return out

    def _detect_language(self, text: str) -> Optional[str]:
        text = text.lower()
        if "python" in text:
            return "python"
        if "html" in text or "css" in text:
            return "html"
        if "javascript" in text or "js" in text:
            return "javascript"
        return None

    def generate_code_snippet(self, lang: str, topic: str) -> str:
        safe_topic = re.sub(r"[^a-zA-Z0-9_ ]", "", topic)
        if lang == "python":
            return textwrap.dedent(f"""
            # Python study helper for {safe_topic}
            def study_prompt(topic: str) -> str:
                # Return a short study prompt for the given topic.
                return f"Write a one-sentence summary of {{topic}} and one question to test understanding."

            if __name__ == '__main__':
                print(study_prompt('{safe_topic}'))
            """)
        if lang == "html":
            return textwrap.dedent(f"""
            <!-- HTML study card for {safe_topic} -->
            <div class="study-card">
              <h3>{safe_topic}</h3>
              <p>Write a one-sentence summary, then create a single flashcard question.</p>
            </div>
            """)
        # default javascript
        return textwrap.dedent(f"""
        // JavaScript study helper for {safe_topic}
        function studyPrompt(topic) {{
          return `Write a one-sentence summary of ${'{'}topic{'}'} and one short question to test understanding.`;
        }}

        console.log(studyPrompt('{safe_topic}'))
        """)

    # -----------------------------------------------------------------------
    # Answer evaluation handler
    # -----------------------------------------------------------------------
    def handle_evaluate(self, text: str) -> str:
        # expects pattern like: evaluate <question> ||| <answer> or similar
        parts = re.split(r"\s*\|\|\|\s*", text, maxsplit=1)
        if len(parts) == 2:
            question = parts[0]
            answer = parts[1]
        else:
            # fallback: use last quiz question if present
            mem = self._get_last_quiz()
            if not mem:
                return "No recent quiz to evaluate. Use /quiz to generate questions or provide question and answer separated by |||"
            question = mem["quiz"][0][0]
            answer = text
        correct, explanation = self.evaluate_answer(question, answer)
        out = f"Evaluation:\nCorrect: {correct}\nNotes: {explanation}"
        self._save_to_history("assistant", out)
        return out

    # -----------------------------------------------------------------------
    # Helpers and small utilities
    # -----------------------------------------------------------------------
    def _shorten(self, text: str, maxlen: int = 160) -> str:
        txt = text.strip()
        if len(txt) <= maxlen:
            return txt
        return txt[:maxlen-3].rstrip() + "..."

    def _split_facts_from_text(self, text: str) -> List[str]:
        # heuristic: break on semicolons, newlines, or sentences
        parts = re.split(r"[;\\n]+|(?<=[.!?])\\s+", text)
        parts = [p.strip() for p in parts if p.strip()]
        return parts

    def _extract_topic_from_text(self, text: str) -> str:
        # look for 'about X' or 'on X' phrases
        m = re.search(r"(?:about|on|for)\\s+([A-Za-z0-9 ,_-]+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # try to take keywords
        kws = extract_keywords(text, max_keywords=3)
        return " ".join(kws) if kws else self.topic

    def _optional_content_after_keyword(self, text: str, keywords: List[str]) -> Optional[str]:
        # find the first keyword occurrence and return trailing content
        lowered = text.lower()
        for kw in keywords:
            idx = lowered.find(kw)
            if idx != -1:
                # return content after keyword
                return text[idx+len(kw):].strip(" -:.") or None
        return None

    def _get_last_quiz(self) -> Optional[dict]:
        for itm in self.short_term_memory:
            if itm.get("type") == "quiz":
                return itm
        return None

    def _save_to_history(self, role: str, text: str):
        self.history.append((role, text))
        self.session["history"].append({"role": role, "text": text, "ts": time.time()})

    # -----------------------------------------------------------------------
    # Session persistence
    # -----------------------------------------------------------------------
    def save_session(self, path: str = SESSION_SAVE):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.session, f, indent=2)
            return True
        except Exception as exc:
            print(f"Failed to save session: {exc}")
            return False

    def load_session(self, path: str = SESSION_SAVE):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.session = data
                    self.topic = data.get("topic", self.topic)
                    self.history = [(h.get("role"), h.get("text")) for h in data.get("history", [])]
                    return True
        except Exception:
            pass
        return False

# ---------------------------------------------------------------------------
# CLI interface and command handling
# ---------------------------------------------------------------------------

HELP_TEXT = """
Commands:
  /help               Show this help text
  /exit               Exit the chat and save session
  /topic <name>       Set the study topic
  /flashcards [topic] Generate flashcards for topic or current topic
  /quiz [topic]       Generate a quiz
  /takequiz           Walk through the last generated quiz interactively
  /answer <n>         Reveal answer n from the last quiz
  /cheatsheet [topic] Generate a cheat sheet
  /summarize [text]   Summarize provided text or topic
  /example [topic]    Show a concrete example
  /plan [topic]       Create a short study plan
  /code [lang] [topic]Create a code snippet
  /eval <q> ||| <a>   Evaluate an answer to a question
  /save               Save session to disk
  /load               Load session from disk
"""


def repl():
    bot = LocalGemini()
    bot.load_session()
    print(WELCOME_TEXT)
    print("\nType a study prompt or a command.\n")

    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting and saving session...")
            bot.save_session()
            break

        if not user:
            continue

        if user.startswith("/"):
            cmd_parts = user.split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            arg = cmd_parts[1] if len(cmd_parts) > 1 else ""
            if cmd == "/help":
                print(HELP_TEXT)
                continue
            if cmd == "/exit":
                print("Saving session and exiting...")
                bot.save_session()
                break
            if cmd == "/topic":
                bot.topic = arg or bot.topic
                bot.session["topic"] = bot.topic
                print(f"Topic set to: {bot.topic}")
                continue
            if cmd == "/flashcards":
                out = bot.handle_flashcards(arg or bot.topic)
                print(out)
                continue
            if cmd == "/quiz":
                out = bot.handle_quiz(arg or bot.topic)
                print(out)
                continue
            if cmd == "/takequiz":
                mem = bot._get_last_quiz()
                if not mem:
                    print("No recent quiz found. Generate one with /quiz.")
                    continue
                run_interactive_quiz(bot, mem)
                continue
            if cmd == "/answer":
                try:
                    n = int(arg)
                except Exception:
                    print("Usage: /answer <number>")
                    continue
                mem = bot._get_last_quiz()
                if not mem:
                    print("No quiz available.")
                    continue
                quiz = mem.get("quiz", [])
                if n < 1 or n > len(quiz):
                    print("Answer number out of range.")
                    continue
                print(f"Answer {n}: {quiz[n-1][1]}")
                continue
            if cmd == "/cheatsheet":
                out = bot.handle_cheatsheet(arg or bot.topic)
                print(out)
                continue
            if cmd == "/summarize":
                out = bot.handle_summarize(arg or bot.topic)
                print(out)
                continue
            if cmd == "/example":
                out = bot.handle_example(arg or bot.topic)
                print(out)
                continue
            if cmd == "/plan":
                out = bot.handle_plan(arg or bot.topic)
                print(out)
                continue
            if cmd == "/code":
                # support: /code python topic
                pieces = arg.split(maxsplit=1)
                if not pieces:
                    print("Usage: /code <lang> [topic]")
                    continue
                lang = pieces[0]
                tp = pieces[1] if len(pieces) > 1 else bot.topic
                out = bot.generate_code_snippet(lang, tp)
                print(out)
                continue
            if cmd == "/eval":
                out = bot.handle_evaluate(arg)
                print(out)
                continue
            if cmd == "/save":
                ok = bot.save_session()
                print("Saved." if ok else "Save failed.")
                continue
            if cmd == "/load":
                ok = bot.load_session()
                print("Loaded." if ok else "No session found.")
                continue
            print("Unknown command. Type /help for a list of commands.")
            continue

        # normal conversational input
        resp = bot.respond(user)
        print("\nGemini> ")
        print(resp)

# ---------------------------------------------------------------------------
# Interactive quiz runner
# ---------------------------------------------------------------------------

def run_interactive_quiz(bot: LocalGemini, mem: dict):
    quiz = mem.get("quiz", [])
    if not quiz:
        print("Empty quiz.")
        return
    print(f"Starting interactive quiz on '{mem.get('topic')}' — {len(quiz)} questions.")
    for i, (q, a) in enumerate(quiz, 1):
        print(f"\nQ{i}: {q}")
        try:
            ans = input("Your answer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nQuiz aborted.")
            return
        if not ans:
            print("Answer empty — counted as incorrect.")
            print(f"Correct: {a}")
            continue
        correct, note = bot.evaluate_answer(q, ans)
        print(f"Result: {'Correct' if correct else 'Incorrect'} — {note}")
        if not correct:
            # provide a quick resource
            resource = bot.generate_cheatsheet(mem.get('topic'))
            print("\nQuick resource:\n")
            print(resource)
            # short delay to mimic reflection
            time.sleep(1)
    print("\nQuiz complete — good work!")

# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        repl()
    except Exception as exc:
        print(f"{APP_NAME} encountered an error: {exc}")
        sys.exit(1)