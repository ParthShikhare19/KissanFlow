"""QR code generation utility using qrcode[pil]."""
import io
import base64
import json
import qrcode
from qrcode.image.pil import PilImage


def generate_qr_base64(data: dict) -> str:
    """Generate a QR code PNG from a dict and return as base64 string."""
    json_str = json.dumps(data, default=str)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(json_str)
    qr.make(fit=True)
    img: PilImage = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
