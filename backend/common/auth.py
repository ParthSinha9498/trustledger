from fastapi import Header, HTTPException

from backend import config


def require_node_token(x_node_token: str = Header(default="")) -> None:
    if x_node_token != config.node_token():
        raise HTTPException(status_code=401, detail="bad node token")
