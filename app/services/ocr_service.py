# from PIL import Image
# import cv2
# import numpy as np
#
# from paddleocr import PaddleOCR
#
# from app.pipelines.file_handler import FileHandler
#
#
# class OCRService:
#
#     """
#     OCR Layer ONLY.
#
#     Responsibilities:
#     - OCR extraction
#     - preserve coordinates
#     - preserve confidence
#     - preserve reading order
#
#     NOT responsible for:
#     - semantic understanding
#     - field mapping
#     - validation
#     - classification
#     """
#
#     ocr_engine = PaddleOCR(
#         use_angle_cls=True,
#         lang="en",
#         use_gpu=False,
#         show_log=False
#     )
#
#     @staticmethod
#     def pil_to_cv2(image: Image.Image):
#
#         return cv2.cvtColor(
#             np.array(image),
#             cv2.COLOR_RGB2BGR
#         )
#
#     @staticmethod
#     async def extract_document(file):
#
#         items = await FileHandler.process_file(file)
#
#         all_ocr_blocks = []
#
#         page_number = 1
#
#         for item in items:
#
#             # Direct text extraction
#             if isinstance(item, tuple) and item[0] == "text":
#
#                 all_ocr_blocks.append({
#                     "id": len(all_ocr_blocks) + 1,
#                     "page": page_number,
#                     "line": 1,
#                     "text": item[1],
#                     "bbox": None,
#                     "confidence": 1.0
#                 })
#
#             elif isinstance(item, Image.Image):
#
#                 page_blocks = OCRService.process_image(
#                     item,
#                     page_number
#                 )
#
#                 all_ocr_blocks.extend(page_blocks)
#
#             page_number += 1
#
#         raw_text = OCRService.build_raw_text(
#             all_ocr_blocks
#         )
#
#         return {
#             "raw_text": raw_text,
#             "ocr_blocks": all_ocr_blocks
#         }
#
#     @staticmethod
#     def process_image(
#         image: Image.Image,
#         page_number: int
#     ):
#
#         image = FileHandler.prepare_image(
#             image,
#             max_size=(2000, 2000)
#         )
#
#         cv2_image = OCRService.pil_to_cv2(
#             image
#         )
#
#         result = OCRService.ocr_engine.ocr(
#             cv2_image,
#             cls=True
#         )
#
#         blocks = []
#
#         line_number = 1
#
#         if not result or not result[0]:
#             return blocks
#
#         for line in result[0]:
#
#             try:
#
#                 bbox = line[0]
#
#                 text = line[1][0].strip()
#
#                 confidence = float(line[1][1])
#
#                 if not text:
#                     continue
#
#                 blocks.append({
#                     "id": len(blocks) + 1,
#                     "page": page_number,
#                     "line": line_number,
#                     "text": text,
#                     "bbox": bbox,
#                     "confidence": confidence
#                 })
#
#                 line_number += 1
#
#             except Exception:
#                 continue
#
#         return blocks
#
#     @staticmethod
#     def build_raw_text(blocks):
#
#         return "\n".join(
#             block["text"]
#             for block in blocks
#         )

from pathlib import Path
import tempfile

from docling.document_converter import DocumentConverter

from app.pipelines.file_handler import FileHandler


class OCRService:

    """
    Docling-based OCR / document parsing layer.

    Responsibilities:
    - layout-aware parsing
    - structure preservation
    - markdown reconstruction
    - document semantic formatting

    NOT responsible for:
    - final semantic extraction
    - validation
    - business rules
    """

    converter = DocumentConverter()

    @staticmethod
    async def extract_document(file):

        suffix = Path(file.filename).suffix

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await file.read()

            temp_file.write(content)

            temp_path = temp_file.name

        try:

            result = OCRService.converter.convert(
                temp_path
            )

            document = result.document

            markdown_output = document.export_to_markdown()

            text_output = document.export_to_text()

            return {
                "raw_text": text_output,
                "markdown": markdown_output
            }

        finally:

            Path(temp_path).unlink(
                missing_ok=True
            )