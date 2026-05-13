# Adobe API Auth Scaffold

This workspace contains a small Python project for Adobe server-to-server OAuth and PDF-to-XLSX conversion.

## Layout

- `src/adobe_api/` contains the reusable auth helper.
- `scripts/get_access_token.py` is the runnable entry point.
- `adobe-credentials.example.json` is the credentials template.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp adobe-credentials.example.json "YOUR-OAuth Server-to-Server.json"
python scripts/get_access_token.py --credentials-path "YOUR-OAuth Server-to-Server.json"
```

The script prints the raw Adobe access token to standard output.