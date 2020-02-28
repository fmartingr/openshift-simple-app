import os

from flask import Flask, request, Response

app = Flask(__name__)


@app.route("/")
def index():
    return f"TODO"


@app.route("/headers")
def headers():
    content = "\n".join(
        [
            "{key}={value}".format(key=key, value=value)
            for key, value in request.headers.items()
        ]
    )
    return Response(content, content_type="text/plain")


@app.route("/environment")
def environment():
    content = "\n".join(
        [
            "{key}={value}".format(key=key, value=value)
            for key, value in os.environ.items()
        ]
    )
    return Response(content, content_type="text/plain")


if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0")
