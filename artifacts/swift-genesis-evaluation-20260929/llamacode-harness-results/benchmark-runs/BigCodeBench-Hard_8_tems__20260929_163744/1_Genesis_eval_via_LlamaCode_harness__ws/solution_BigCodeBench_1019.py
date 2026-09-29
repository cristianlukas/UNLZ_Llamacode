from PIL import Image
import codecs
import pytesseract

IMAGE_PATH = "image.png"

def task_func(filename=IMAGE_PATH, from_encoding="cp1251", to_encoding="utf8"):
    try:
        image = Image.open(filename)
    except Exception:
        return ""
    try:
        text = pytesseract.image_to_string(image)
        return codecs.decode(codecs.encode(text, from_encoding), to_encoding)
    except (UnicodeDecodeError, LookupError):
        raise ValueError("UnicodeDecodeError or LookupError occurred during conversion")
    except Exception:
        try:
            comment = image.info.get("comment", "")
            if isinstance(comment, bytes):
                comment = comment.decode("latin-1")
            return codecs.decode(codecs.encode(comment, from_encoding), to_encoding)
        except (UnicodeDecodeError, LookupError):
            raise ValueError("UnicodeDecodeError or LookupError occurred during conversion")
        except Exception:
            return ""
