"""Web demo layer (FastAPI backend for the M4 UI).

`services.py` is pure and offline-testable (no fastapi import). `api.py` is the only
module that imports fastapi. The core engine and the pytest suite never import this
package, so tests stay stdlib + offline.
"""
