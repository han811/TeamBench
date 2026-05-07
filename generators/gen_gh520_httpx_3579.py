"""
Parameterized generator for GH520_httpx_3579.

Source PR:    https://github.com/encode/httpx/pull/3579
Source Issue: N/A

Seed varies: renames 'automatically' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH520_httpx_3579'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH520_httpx_3579'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('automatically', 'automatically' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH520_httpx_3579',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'encode/httpx',
                "pr_number": 3579,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/encode/httpx/pull/3579",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/advanced/ssl.md': 'When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).\n\n### Enabling and disabling verification\n\nBy default httpx will verify HTTPS connections, and raise an error for invalid SSL cases...\n\n```pycon\n>>> httpx.get("https://expired.badssl.com/")\nhttpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)\n```\n\nYou can disable SSL verification completely and allow insecure requests...\n\n```pycon\n>>> httpx.get("https://expired.badssl.com/", verify=False)\n<Response [200 OK]>\n```\n\n### Configuring client instances\n\nIf you\'re using a `Client()` instance you should pass any `verify=<...>` configuration when instantiating the client.\n\nBy default the [certifi CA bundle](https://certifiio.readthedocs.io/en/latest/) is used for SSL verification.\n\nFor more complex configurations you can pass an [SSL Context](https://docs.python.org/3/library/ssl.html) instance...\n\n```python\nimport certifi\nimport httpx\nimport ssl\n\n# This SSL context is equivelent to the default `verify=True`.\nctx = ssl.create_default_context(cafile=certifi.where())\nclient = httpx.Client(verify=ctx)\n```\n\nUsing [the `truststore` package](https://truststore.readthedocs.io/) to support system certificate stores...\n\n```python\nimport ssl\nimport truststore\nimport httpx\n\n# Use system certificate stores.\nctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)\nclient = httpx.Client(verify=ctx)\n```\n\nLoding an alternative certificate verification store using [the standard SSL context API](https://docs.python.org/3/library/ssl.html)...\n\n```python\nimport httpx\nimport ssl\n\n# Use an explicitly configured certificate store.\nctx = ssl.create_default_context(cafile="path/to/certs.pem")  # Either cafile or capath.\nclient = httpx.Client(verify=ctx)\n```\n\n### Client side certificates\n\nClient side certificates allow a remote server to verify the client. They tend to be used within private organizations to authenticate requests to remote servers.\n\nYou can specify client-side certificates, using the [`.load_cert_chain()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain) API...\n\n```python\nctx = ssl.create_default_context()\nctx.load_cert_chain(certfile="path/to/client.pem")  # Optionally also keyfile or password.\nclient = httpx.Client(verify=ctx)\n```\n\n### Working with `SSL_CERT_FILE` and `SSL_CERT_DIR`\n\nUnlike `requests`, the `httpx` package does not automatically pull in [the environment variables `SSL_CERT_FILE` or `SSL_CERT_DIR`](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_default_verify_paths.html). If you want to use these they need to be enabled explicitly.\n\nFor example...\n\n```python\n# Use `SSL_CERT_FILE` or `SSL_CERT_DIR` if configured.\n# Otherwise default to certifi.\nctx = ssl.create_default_context(\n    cafile=os.environ.get("SSL_CERT_FILE", certifi.where()),\n    capath=os.environ.get("SSL_CERT_DIR"),\n)\nclient = httpx.Client(verify=ctx)\n```\n\n### Making HTTPS requests to a local server\n\nWhen making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.\n\nIf you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here\'s one way to do it...\n\n1. Use [trustme](https://github.com/python-trio/trustme) to generate a pair of server key/cert files, and a client cert file.\n2. Pass the server key/cert files when starting your local server. (This depends on the particular web server you\'re using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)\n3. Configure `httpx` to use the certificates stored in `client.pem`.\n\n```python\nctx = ssl.create_default_context(cafile="client.pem")\nclient = httpx.Client(verify=ctx)\n```\n',
            'docs/environment_variables.md': '# Environment Variables\n\nThe HTTPX library can be configured via environment variables.\nEnvironment variables are used by default. To ignore environment variables, `trust_env` has to be set `False`. There are two ways to set `trust_env` to disable environment variables:\n\n* On the client via `httpx.Client(trust_env=False)`.\n* Using the top-level API, such as `httpx.get("<url>", trust_env=False)`.\n\nHere is a list of environment variables that HTTPX recognizes and what function they serve:\n\n## Proxies\n\nThe environment variables documented below are used as a convention by various HTTP tooling, including:\n\n* [cURL](https://github.com/curl/curl/blob/master/docs/MANUAL.md#environment-variables)\n* [requests](https://github.com/psf/requests/blob/master/docs/user/advanced.rst#proxies)\n\nFor more information on using proxies in HTTPX, see [HTTP Proxying](advanced/proxies.md#http-proxying).\n\n### `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`\n\nValid values: A URL to a proxy\n\n`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` set the proxy to be used for `http`, `https`, or all requests respectively.\n\n```bash\nexport HTTP_PROXY=http://my-external-proxy.com:1234\n\n# This request will be sent through the proxy\npython -c "import httpx; httpx.get(\'http://example.com\')"\n\n# This request will be sent directly, as we set `trust_env=False`\npython -c "import httpx; httpx.get(\'http://example.com\', trust_env=False)"\n\n```\n\n### `NO_PROXY`\n\nValid values: a comma-separated list of hostnames/urls\n\n`NO_PROXY` disables the proxy for specific urls\n\n```bash\nexport HTTP_PROXY=http://my-external-proxy.com:1234\nexport NO_PROXY=http://127.0.0.1,python-httpx.org\n\n# As in the previous example, this request will be sent through the proxy\npython -c "import httpx; httpx.get(\'http://example.com\')"\n\n# These requests will be sent directly, bypassing the proxy\npython -c "import httpx; httpx.get(\'http://127.0.0.1:5000/my-api\')"\npython -c "import httpx; httpx.get(\'https://www.python-httpx.org\')"\n```\n',
        }
