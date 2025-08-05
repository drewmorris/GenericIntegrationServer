import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_pw: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_pw.encode()) 