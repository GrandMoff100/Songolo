import base64


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
        return base64.decode(
            content.encode(cls.encoding), altchars=cls.altchars
        )
