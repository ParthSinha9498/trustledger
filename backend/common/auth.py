import hmac

from fastapi import Header, HTTPException

from backend import config


def require_node_token(x_node_token: str = Header(default="")) -> None:
    expected = config.node_token()
    # An empty configured token must never match an empty header.
    if not expected or not hmac.compare_digest(x_node_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="bad node token")
