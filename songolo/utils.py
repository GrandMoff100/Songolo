"""A module of utility/miscellaneous methods and classes."""

import base64
import datetime
import hashlib
import random
import string


class Base64:
    """A wrapper class for base64 encoding and decoding file content."""

    altchars = b"+="
    encoding = "utf-8"

    @classmethod
    def encode(cls, content: bytes) -> str:
        """Encodes file content into web-serializable base64 file content."""
        return base64.b64encode(
            content,
            altchars=cls.altchars,
        ).decode(cls.encoding)

    @classmethod
    def decode(cls, content: str) -> bytes:
        """Decodes base64 file content into bytes."""
        return base64.b64decode(
            content.encode(cls.encoding),
            altchars=cls.altchars,
        )


def sha256_snowflake() -> str:
    """Generates a guaranteed unique string that has never been generated before."""
    source = "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=256,
        ),
    )
    source += str(datetime.datetime.now())
    return hashlib.sha256(source.encode()).hexdigest()
