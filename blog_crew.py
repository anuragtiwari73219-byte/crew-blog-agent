import os
import traceback

from flask import Flask, render_template, request

from repo_blog_agent import generate_blog_post

app = Flask(__name__)

# Gated on purpose — full custom input would let anyone burn through the
# Groq free-tier quota (3-5 calls per request, more if fact-check FLAGs).
# Same lesson learned on the email-triage project.
ALLOWED_REPOS = [
    "anuragtiwari73219-byte/crew-blog-agent",
    "crewAIInc/crewAI",
    "pallets/flask",
    "psf/requests",
    "tiangolo/fastapi",
]


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    selected_repo = None

    if request.method == "POST":
        selected_repo = request.form.get("repo")
        if selected_repo not in ALLOWED_REPOS:
            error = "Invalid repo selection."
        else:
            try:
                result = generate_blog_post(selected_repo, log=lambda *_: None)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()

    return render_template(
        "index.html",
        repos=ALLOWED_REPOS,
        selected_repo=selected_repo,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)