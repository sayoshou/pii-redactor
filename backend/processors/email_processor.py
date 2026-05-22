import email
from email import policy
from email.parser import BytesParser
from typing import Callable


def process_email(content: bytes, redact: Callable[[str], str]) -> str:
    message = BytesParser(policy=policy.default).parsebytes(content)
    
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "text":
                text = part.get_content()
                redacted_text = redact(text)
                part.set_content(redacted_text, subtype=part.get_content_subtype())
    else:
        text = message.get_content()
        redacted_text = redact(text)
        message.set_content(redacted_text, subtype=message.get_content_subtype())
    
    # EMLフォーマットで出力
    eml_str = message.as_string(unixfrom=True, maxheaderlen=0)
    return eml_str
