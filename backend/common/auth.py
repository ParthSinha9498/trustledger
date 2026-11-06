import hmac

from fastapi import Header, HTTPException

from backend import config


def require_node_token(x_node_token: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_node_token.encode(), config.node_token().encode()):
        raise HTTPException(status_code=401, detail="bad node token")
