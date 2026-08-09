from io import BytesIO
import unittest

from fastapi import HTTPException
from PIL import Image

from app.api.v1.endpoints.upload import MAX_IMAGE_BYTES, validated_image_extension


def create_image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(20, 40, 60)).save(buffer, format=image_format)
    return buffer.getvalue()


class UploadValidationTests(unittest.TestCase):
    def test_detects_image_from_content_instead_of_client_filename(self):
        self.assertEqual(validated_image_extension(create_image_bytes("PNG")), ".png")
        self.assertEqual(validated_image_extension(create_image_bytes("JPEG")), ".jpg")

    def test_rejects_non_image_content(self):
        with self.assertRaises(HTTPException) as context:
            validated_image_extension(b"<svg onload=alert(1)></svg>")

        self.assertEqual(context.exception.status_code, 400)

    def test_rejects_oversized_upload_before_decoding(self):
        with self.assertRaises(HTTPException) as context:
            validated_image_extension(b"x" * (MAX_IMAGE_BYTES + 1))

        self.assertEqual(context.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
