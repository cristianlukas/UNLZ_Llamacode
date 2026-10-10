from PIL import Image
import codecs
import pytesseract
IMAGE_PATH = "image.png"


def _convert(text, from_encoding, to_encoding):
    if isinstance(text, bytes):
        text = codecs.decode(text, from_encoding)
    return codecs.decode(codecs.encode(text, from_encoding), to_encoding)


def task_func(filename=IMAGE_PATH, from_encoding="cp1251", to_encoding="utf8"):
    # First attempt: extract text from the image using OCR.
    try:
        with Image.open(filename) as image:
            image.load()
            common = pytesseract.image_to_string(image)
    except Exception:
        common = ""

    if common:
        try:
            common = _convert(common, from_encoding, to_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError, LookupError) as exc:
            raise ValueError(f"Incorrect encodings provided: {exc}") from exc
        return common

    # Fallback: process the image comment.
    try:
        with Image.open(filename) as image:
            image.load()
            common = image.info.get("comment", "")
    except Exception:
        common = ""

    if common:
        try:
            common = _convert(common, from_encoding, to_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError, LookupError) as exc:
            raise ValueError(f"Incorrect encodings provided: {exc}") from exc
        return common

    return ""
