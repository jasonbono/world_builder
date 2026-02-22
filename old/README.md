# World Server

Simulated 1D physics world exposed via REST API. An external agent interacts with it through HTTP calls.

## Architecture

Single-file FastAPI server (`server.py`). All state is in-memory — a position `x`, hidden velocity `v`, and time counter `t`. The world is frozen between API calls.

Endpoints: `/act`, `/observe`, `/advance`, `/reset`, `/history`.

## Run

```bash
pip install -r requirements.txt
python server.py
```

Server starts on `http://localhost:8080`. Docs at `http://localhost:8080/docs`.

## Stop

Ctrl+C in the terminal.
