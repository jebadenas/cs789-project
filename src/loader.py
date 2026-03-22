from pathlib import Path

from src.parser import load_session
from src.schemas import Session


def load_all_sessions(data_dir: str | Path = "./data") -> dict[tuple[str, str, int], Session]:
    """
    Load every CSV in data_dir into memory.

    Returns a dict keyed by (year, semester, session_number).
    e.g. sessions[("2024", "S1", 3)] → Session object

    Usage:
        from src.loader import load_all_sessions
        sessions = load_all_sessions()
    """
    data_dir = Path(data_dir)
    sessions: dict[tuple[str, str, int], Session] = {}

    for csv_file in sorted(data_dir.glob("*.csv")):
        try:
            session = load_session(csv_file)
            key = (session.year, session.semester, session.number)
            if key in sessions:
                print(f"WARNING: duplicate key {key} — "
                      f"'{sessions[key].name}' overwritten by '{session.name}'")
            sessions[key] = session
            print(f"  Loaded {csv_file.name}  →  {key}")
        except Exception as e:
            print(f"  ERROR loading {csv_file.name}: {e}")

    print(f"\n{len(sessions)} sessions loaded.")
    return sessions