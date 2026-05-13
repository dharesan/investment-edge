from __future__ import annotations

import argparse
from pathlib import Path

from adobe_api import fetch_access_token, load_credentials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch an Adobe IMS access token using server-to-server credentials."
    )
    parser.add_argument(
        "--credentials-path",
        default=Path(__file__).resolve().parents[1]
        / "761BlackAardwolf-4199879-OAuth Server-to-Server.json",
        help="Path to the Adobe credentials JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    credentials = load_credentials(args.credentials_path)
    token = fetch_access_token(credentials)
    print(token)


if __name__ == "__main__":
    main()