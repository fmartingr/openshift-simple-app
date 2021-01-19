# Simple OpenShift application

This is a simple OpenShift application for debugging purposes. You can
deploy it with the python:3.6 builder and it should work out of the box.

It provides several routes for testing on the index page.

Feel free to send patches.

## Configuration

| Variable name | Default | Description |
| --- | --- | --- |
| `SERVE_SSL` | `off` | Use to tell the app to serve SSL instead of plain text. [Check below](#serving-using-ssl)

## Serving using SSL

There are two ways of enabling SSL on this test application, either with an on-the-fly self-signed certificate provided by werkzeug or by providing the certificates using a secret on a fixed path.

### Serving using an on-the-fly certificate

Just set the `SERVE_SSL` variable to `adhoc`.

### Serving using certificates provided by a secret

Set the `SERVE_SSL` variable to `secret` and mount a secret with a `tls.key` and `tls.crt` under `/tmp/app`.