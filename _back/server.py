from flask import Flask, request, jsonify, send_from_directory
import os
import traceback

# Try to import notopenai; if unavailable, fall back to local rule-based generator
try:
    import notopenai
except Exception:
    notopenai = None

from local_gemini import LocalGemini

app = Flask(__name__, static_folder='.', static_url_path='')

bot = LocalGemini()


def ai_generate(prompt: str) -> str:
    """Generate a response using notopenai if available, otherwise fallback to LocalGemini."""
    text = (prompt or '').strip()
    if not text:
        return "Say something to begin studying."
    # exact greeting override
    if text.lower() == 'hello':
        return 'Hello there! How may I help you?'

    if notopenai:
        try:
            # Best-effort: support common API shapes
            if hasattr(notopenai, 'Chat'):
                resp = notopenai.Chat.create(prompt=text)
                # try common attributes
                return getattr(resp, 'text', getattr(resp, 'message', str(resp)))
            if hasattr(notopenai, 'Completion'):
                resp = notopenai.Completion.create(prompt=text)
                return getattr(resp, 'text', str(resp))
            # unknown SDK shape, attempt call
            return str(notopenai)
        except Exception as e:
            # return fallback but include error note
            return f"notopenai error: {e}\n\nFallback:\n" + bot.respond(text)

    # fallback: rule-based LocalGemini
    return bot.respond(text)


@app.route('/api/study', methods=['POST'])
def api_study():
    try:
        data = request.get_json(force=True)
        prompt = data.get('prompt') if isinstance(data, dict) else None
        if not prompt:
            return jsonify({'error': 'No prompt provided.'}), 400
        reply = ai_generate(prompt)
        return jsonify({'reply': reply})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({'error': str(exc)}), 500


@app.route('/', defaults={'path': 'main.html'})
@app.route('/<path:path>')
def static_proxy(path):
    # Serve files from repository root for simplicity
    if os.path.exists(path):
        return send_from_directory('.', path)
    return 'Not Found', 404


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
