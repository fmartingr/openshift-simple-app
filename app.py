import os

from flask import Flask, request, Response, render_template, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    """List all available routes"""
    routes = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            routes[rule.rule] = app.view_functions[rule.endpoint].__doc__

    if request.accept_mimetypes.accept_json:
        return jsonify(routes)

    if request.accept_mimetypes.accept_html:
        return render_template("index.j2", routes=routes)

    return Response(
        "\n".join(
            [
                "{path:32s}: {doc}".format(path=path, doc=doc)
                for path, doc in routes.items()
            ]
        ),
        content_type="text/plain",
    )


@app.route("/environment")
def environment():
    """Return defined environment"""

    if request.accept_mimetypes.accept_json:
        return jsonify(os.environ.copy())

    return Response(
        "\n".join(
            [
                "{key}={value}".format(key=key, value=value)
                for key, value in os.environ.items()
            ]
        ),
        content_type="text/plain",
    )


@app.route("/headers")
def headers():
    """Return request headers"""

    if request.accept_mimetypes.accept_json:
        return jsonify(dict(request.headers))

    return Response(
        "\n".join(
            [
                "{key}={value}".format(key=key, value=value)
                for key, value in request.headers
            ]
        ),
        content_type="text/plain",
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0")
