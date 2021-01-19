import copy
import json
import logging
import os
import ssl
import subprocess
import sys
import time

import requests
from flask import Flask, request, Response, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.routing import Rule
from werkzeug.security import generate_password_hash, check_password_hash


# SSL configuration
SERVE_SSL = os.environ.get("SERVE_SSL", "off")
SERVE_SSL_ALLOWED = {"off", "adhoc", "secret"}

assert SERVE_SSL in SERVE_SSL_ALLOWED, f"SSL_MODE is not set to a valid value: {SERVE_SSL_ALLOWED}"

options = {}
if SERVE_SSL == "adhoc":
    options = {
        "ssl_context": SERVE_SSL,
    }

if SERVE_SSL == "secret":
    options = {
        "ssl_context": ("/tmp/app/tls.crt", "/tmp/app/tls.key"), 
    }

app = Flask(__name__)
app.url_map.add(Rule("/request", endpoint="request"))
logging.basicConfig(format="%(message)s", level="INFO")
black_logger = logging.getLogger("blank")
auth = HTTPBasicAuth()

users = {
    "foo": generate_password_hash("bar"),
}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route("/")
def root_view():
    """List all available routes"""
    routes = {}
    for rule in sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule):
        if rule.endpoint != "static":
            # Get only the first line from the docstring as the summary
            if app.view_functions[rule.endpoint].__doc__:
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


@app.route("/timeout", methods=["GET"])
def timeout_view():
    """
    Forces a slow response from the request

    Usage:
        /timeout?duration=301 (in seconds)
    """
    duration = int(request.args.get("duration", 300))
    time.sleep(duration)
    return jsonify({"duration": duration})


@app.route("/curl", methods=["POST"])
def curl_view():
    """
    Get connection information from curl to the defined URL in POST

    Usage:
        curl -X POST http://this-app/curl -d '{"url": "https://fmartingr.com"}' -h "Content-Type: application/json"
        http http://this-app/curl "url=https://fmartingr.com"

    Returns:
        dns_resolution: x
        tcp_established: x
        ssl_handshake_done: x
        ttfb: x

        total: x
    """
    params = request.json
    url = params.get("url", None)
    if not url:
        return Response(status=400)

    cmd = (
        "curl",
        "-w",
        "dns_resolution: %{time_namelookup}s\ntcp_established: %{time_connect}s\nssl_handshake_done: %{time_appconnect}s\nttfb: %{time_starttransfer}s\n\ntotal: %{time_total}s",
        "-o",
        "/dev/null",
        "-s",
        "-k",
        url,
    )

    result = subprocess.run(cmd, stdout=subprocess.PIPE)
    print(result.stdout)
    return Response(result.stdout)


@app.route("/samesite")
def samesite_view():
    """
    Test the SameSite Haproxy bug (BZ#1879445)
    """
    hostname = os.environ.get("HOSTNAME")
    return f"""
    <html>
        <head>
            <title>SameSite on {hostname}</title>
        </head>
        <body>
            Both hostnames shown here should be the same if session stickiness is working properly with haproxy. <br />
            SameSite on {hostname} <br />
            <iframe src=\"/samesite/iframe\" title=\"samesite test\">
        </body>
    </html>"""


@app.route("/samesite/iframe")
def samesite_iframe_view():
    hostname = os.environ.get("HOSTNAME")
    return f"iframe on {hostname}"


@app.route("/cors", methods=["GET", "POST"])
def cors_view():
    """
    View to check CORS within the cluster
    """

    if request.method == "POST":
        headers = {}
        enable_cors = request.args.get("enabled", "false")
        if enable_cors == "true":
            headers = {"Access-Control-Allow-Origin": "*"}
        return Response(
            json.dumps({"status": "ok", "cors_enabled": enable_cors}), headers=headers
        )

    return render_template("cors.j2")


@app.route("/json_items", methods=["GET", "POST"])
def items_view():
    """
    Returns a JSON list with the items specified by the `items_number` parameter.
    """

    items_number = request.args.get("issl_contexttems_number", 1)
    item = {"this": "is", "a": "json", "big": "body"}
    response_body = [copy.copy(item) for i in range(0, int(items_number))]

    return jsonify(response_body)


@app.route("/httpauth")
@auth.login_required
def http_auth_route():
    """
    Route with HTTP Auth enabled
    """
    return jsonify({"logged_in": True, "logout": "/httpauth/logout"})


@app.route("/httpauth/logout")
def http_auth_logout_view():
    return "Logged out", 401


@app.route(
    "/test_redirect", methods=["GET", "POST", "DELETE", "HEAD", "UPDATE", "PATH"]
)
def test_redirect_view():
    """
    Returns a custom response code and Location as set in the headers: X-Response-Code and X-Location
    """
    response_code = int(request.headers.get("X-Response-Code", 302))
    response_location = request.headers.get("X-Location", "/request")

    return Response(
        status=response_code,
        headers={"Location": response_location}
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0", **options)
