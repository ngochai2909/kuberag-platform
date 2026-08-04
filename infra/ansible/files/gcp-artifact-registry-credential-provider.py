#!/usr/bin/env python3
"""Return short-lived GCE metadata credentials to the kubelet for Artifact Registry."""

from __future__ import annotations

import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


REGISTRY_HOST = "asia-southeast1-docker.pkg.dev"
METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/token"
)


def main() -> None:
    request = json.load(sys.stdin)
    image = request.get("image", "")
    registry = image.split("/", maxsplit=1)[0]
    if registry != REGISTRY_HOST:
        raise ValueError("unsupported registry")

    metadata_request = Request(
        METADATA_TOKEN_URL,
        headers={"Metadata-Flavor": "Google"},
    )
    with urlopen(metadata_request, timeout=5) as response:
        access_token = json.load(response)["access_token"]

    response = {
        "apiVersion": request["apiVersion"],
        "kind": "CredentialProviderResponse",
        "cacheKeyType": "Registry",
        "cacheDuration": "30m",
        "auth": {
            REGISTRY_HOST: {
                "username": "oauth2accesstoken",
                "password": access_token,
            }
        },
    }
    print(json.dumps(response))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, URLError, json.JSONDecodeError) as error:
        print(f"Artifact Registry credential provider failed: {error}", file=sys.stderr)
        raise SystemExit(1)
