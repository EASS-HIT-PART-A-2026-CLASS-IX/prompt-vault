from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..database import SettingsDep
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])

# Pre-hashed at import time — never store plaintext passwords.
# Rotate by changing the hash here and updating PROMPT_VAULT_JWT_SECRET in .env.
_USERS: dict[str, dict] = {
    "admin": {
        "hashed_password": hash_password("vault-admin"),
        "roles": ["editor", "student"],
    },
    "student": {
        "hashed_password": hash_password("vault-student"),
        "roles": ["student"],
    },
}


@router.post("/token", summary="Obtain a bearer token")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    settings: SettingsDep = ...,  # type: ignore[assignment]
) -> dict[str, str]:
    """Exchange username + password for a signed JWT.

    - **admin / vault-admin** → roles: editor, student
    - **student / vault-student** → roles: student (read-only)
    """
    record = _USERS.get(form.username)
    if not record or not verify_password(form.password, record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        subject=form.username,
        roles=record["roles"],
        settings=settings,
    )
    return {"access_token": token, "token_type": "bearer"}
