import base64
import datetime
import string
import random
import hashlib


class Base64:
    altchars = b"+="
    encoding = "utf-8"

    @classmethod
    def encode(cls, content: bytes) -> str:
        return base64.b64encode(content, altchars=cls.altchars).decode(
            cls.encoding
        )

    @classmethod
    def decode(cls, content: str) -> bytes:
        return base64.b64decode(
            content.encode(cls.encoding), altchars=cls.altchars
        )


def sha256_snowflake() -> str:
    source = ''.join(random.choices(string.ascii_uppercase + string.digits, k=256))
    source += str(datetime.datetime.now())
    return hashlib.sha256(source.encode()).hexdigest()
