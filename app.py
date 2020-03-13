import os

import requests
from flask import Flask, request, Response, render_template, jsonify

app = Flask(__name__)


@app.route("/")
def root_view():
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
def environment_view():
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
def headers_view():
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


@app.route("/log", methods=["POST"])
def log_view():
    """
    Logs the provided payload into stdout.
    Accepts JSON and plain text
    Returns the provided data on response
    """
    if request.is_json:
        app.logger.warn(request.json)
        return jsonify(request.json)

    data = request.get_data().decode("utf-8")
    app.logger.warn(data)
    return Response(data)


@app.route("/http_request", methods=["POST"])
def http_request_view():
    """
    Performs an http request.
    The view is just a passthrough to the requests library:
    - `method` parameter to set the request method
    - Every other parameter will be sent directly to the requests request method
    """
    params = request.json
    method = params.pop("method", "GET")
    response = requests.request(method, **params)

    return jsonify({
        "method": method,
        "params": params,
        "response": {
            "content": response.text,
            "json": response.json(),
            "headers": {key: value for key, value in response.headers.items()}
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0")
