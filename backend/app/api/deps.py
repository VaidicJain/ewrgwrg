from app.services.elexon_client import ElexonClient, build_elexon_client


def get_elexon_client() -> ElexonClient:
    """FastAPI dependency; tests override this with a fake client."""
    return build_elexon_client()
