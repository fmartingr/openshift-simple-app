import json
import logging
import os
import sys

import requests
from flask import Flask, request, Response, render_template, jsonify
from werkzeug.routing import Rule

app = Flask(__name__)
app.url_map.add(Rule("/request", endpoint="request"))


logging.basicConfig(format="%(message)s", level="INFO")
black_logger = logging.getLogger("blank")


@app.route("/")
def root_view():
    """List all available routes"""
    routes = {}
    for rule in sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule):
        if rule.endpoint != "static":
            # Get only the first line from the docstring as the summary
            routes[rule.rule] = list(
                filter(None, app.view_functions[rule.endpoint].__doc__.split("\n"))
            )[0].strip()

    # HTML response
    if request.accept_mimetypes.accept_html:
        return render_template("index.j2", routes=routes)

    # JSON response
    if request.accept_mimetypes.accept_json:
        return jsonify(routes)

    # Plain text response
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

    # JSON response
    if request.accept_mimetypes.accept_json:
        return jsonify(os.environ.copy())

    # Plain text response
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

    # JSON response
    if request.accept_mimetypes.accept_json:
        return jsonify(dict(request.headers))

    # Plain text response
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
    # JSON response
    if request.is_json:
        sys.stdout.write(json.dumps(request.json) + "\n")
        return jsonify(request.json)

    # Plain text response
    data = request.get_data().decode("utf-8")
    sys.stdout.write(f"{data}\n")
    return Response(data, content_type="plain/text")


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

    # JSON response
    return jsonify(
        {
            "method": method,
            "params": params,
            "response": {
                "content": response.text,
                "json": response.json(),
                "headers": {key: value for key, value in response.headers.items()},
            },
        }
    )


@app.endpoint("request")  # /request
def request_view():
    """
    Return request information.
    Useful to use along /request from other pods.
    """

    request_data = {
        "method": request.method,
        "url": request.url,
        "path": request.path,
        "data": request.get_data(as_text=True),
        "json": request.get_json(),
        "cookies": {key: value for key, value in request.cookies.items()},
        "params": {key: value for key, value in request.args.items()},
        "headers": {key: value for key, value in request.headers.items()},
    }

    # JSON response
    if request.accept_mimetypes.accept_json:
        return jsonify(request_data)

    # Plain text response
    return Response(
        render_template("request.j2", request_data=request_data),
        content_type="text/plain",
    )


@app.route("/samesite")
def samesite_view():
    hostname = os.environ.get("HOSTNAME")
    return f"""
    <html>
        <head>
            <title>SameSite on {hostname}</title>
        </head>
        <body>
            SameSite on {hostname} <br />
            <iframe src=\"/samesite/iframe\" title=\"samesite test\">
        </body>
    </html>"""


@app.route("/samesite/iframe")
def samesite_iframe_view():
    hostname = os.environ.get("HOSTNAME")
    return f"iframe on {hostname}"


if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0")
