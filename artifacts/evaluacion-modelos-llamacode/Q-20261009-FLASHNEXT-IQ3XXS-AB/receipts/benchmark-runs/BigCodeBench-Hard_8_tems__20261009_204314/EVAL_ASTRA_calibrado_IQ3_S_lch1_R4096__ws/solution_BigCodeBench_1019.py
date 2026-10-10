from PIL import Image
import codecs
import pytesseract
IMAGE_PATH = "image.png"
def task_func(filename=IMAGE_PATH, from_encoding="cp1251", to_encoding="utf8"):
    def convert(text):
        try:
            return text.encode(from_encoding).decode(to_encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            raise ValueError(str(exc))

    try:
        with Image.open(filename) as image:
            text = pytesseract.image_to_string(image)
        return convert(text)
    except ValueError:
        raise
    except Exception:
        pass

    try:
        with Image.open(filename) as image:
            comment = image.info.get('comment', '')
        if not comment:
            return ''
        if isinstance(comment, bytes):
            comment = codecs.decode(comment, from_encoding, errors='ignore')
        return convert(comment)
    except ValueError:
        raise
    except Exception:
        return ''
