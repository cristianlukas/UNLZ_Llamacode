from PIL import Image
import codecs
import pytesseract

IMAGE_PATH = "image.png"

def task_func(filename=IMAGE_PATH, from_encoding="cp1251", to_encoding="utf8"):
    def convert(value):
        try:
            text = value.decode(from_encoding) if isinstance(value, bytes) else str(value)
            return text.encode(from_encoding).decode(to_encoding)
        except (UnicodeDecodeError, UnicodeEncodeError, LookupError) as exc:
            raise ValueError(str(exc)) from exc

    try:
        codecs.lookup(from_encoding)
        codecs.lookup(to_encoding)
    except LookupError as exc:
        raise ValueError(str(exc)) from exc

    try:
        with Image.open(filename) as image:
            try:
                text = pytesseract.image_to_string(image)
            except Exception:
                text = ""
            if text:
                return convert(text)

            comment = image.info.get("comment", "")
            if comment:
                return convert(comment)
    except ValueError:
        raise
    except Exception:
        pass

    return ""
