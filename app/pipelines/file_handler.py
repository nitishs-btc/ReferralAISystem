import io
import zipfile
import tarfile
from PIL import Image
from pdf2image import convert_from_bytes

POPPLER_PATH = r"C:\Users\Ramyakrishna\poppler\poppler-24.08.0\Library\bin"

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}
SUPPORTED_DOC_EXTENSIONS = {".pdf", ".doc", ".docx"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".zip", ".tar", ".tar.gz", ".tgz"}
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS | SUPPORTED_ARCHIVE_EXTENSIONS


class FileHandler:

    @staticmethod
    def get_file_extension(filename: str) -> str:
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""

    @staticmethod
    def get_file_type(filename: str) -> str:
        extension = FileHandler.get_file_extension(filename)
        filename_lower = filename.lower()

        if extension == ".pdf":
            return "pdf"
        elif extension in SUPPORTED_IMAGE_EXTENSIONS:
            return "image"
        elif extension in {".doc", ".docx"}:
            return "word"
        elif extension == ".zip":
            return "zip"
        elif extension in {".tar", ".tgz"} or filename_lower.endswith(".tar.gz"):
            return "tar"
        else:
            return "unknown"

    @staticmethod
    def is_supported(filename: str) -> bool:
        extension = FileHandler.get_file_extension(filename)
        filename_lower = filename.lower()
        return extension in ALL_SUPPORTED_EXTENSIONS or filename_lower.endswith(".tar.gz")

    @staticmethod
    def is_archive(filename: str) -> bool:
        file_type = FileHandler.get_file_type(filename)
        return file_type in {"zip", "tar"}

    @staticmethod
    async def process_file(file) -> list:
        """
        Process uploaded file and return list of PIL Images for OCR.
        Handles PDF, images, and Word documents.
        Returns list of images ready for OCR processing.
        """

        content = await file.read()
        filename = file.filename.lower()
        file_type = FileHandler.get_file_type(filename)

        if file_type == "pdf":
            return FileHandler.process_pdf(content)

        elif file_type == "image":
            return FileHandler.process_image(content)

        elif file_type == "word":
            return FileHandler.process_word(content, FileHandler.get_file_extension(filename))

        else:
            return FileHandler.try_as_image(content, filename)

    @staticmethod
    def process_pdf(content: bytes) -> list:
        """Convert PDF pages to list of PIL Images."""

        pages = convert_from_bytes(
            content,
            dpi=100,
            poppler_path=POPPLER_PATH
        )

        return [FileHandler.prepare_image(page) for page in pages]

    @staticmethod
    def process_image(content: bytes) -> list:
        """Process image file and return as list with single PIL Image."""

        image = Image.open(io.BytesIO(content))
        return [FileHandler.prepare_image(image)]

    @staticmethod
    def process_word(content: bytes, extension: str) -> list:
        """
        Process Word document.
        Returns list with None to indicate text extraction (no OCR needed).
        The text is stored in the first element as a tuple ('text', extracted_text).
        """

        try:
            import docx
        except ImportError:
            raise ImportError(
                "python-docx is required for Word document processing. "
                "Install with: pip install python-docx"
            )

        if extension == ".docx":
            doc = docx.Document(io.BytesIO(content))
            text_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)

            extracted_text = "\n".join(text_parts)
            return [("text", extracted_text)]

        else:
            raise ValueError("Legacy .doc format is not supported. Please convert to .docx")

    @staticmethod
    def try_as_image(content: bytes, filename: str) -> list:
        """Try to process unknown file type as image."""

        try:
            image = Image.open(io.BytesIO(content))
            return [FileHandler.prepare_image(image)]
        except Exception:
            extension = FileHandler.get_file_extension(filename)
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: PDF, images ({', '.join(SUPPORTED_IMAGE_EXTENSIONS)}), Word documents (.docx)"
            )

    @staticmethod
    async def extract_archive(file) -> list:
        """
        Extract files from ZIP or TAR archive.
        Returns list of tuples: (filename, content_bytes)
        """

        content = await file.read()
        filename = file.filename.lower()
        file_type = FileHandler.get_file_type(filename)

        extracted_files = []

        if file_type == "zip":
            extracted_files = FileHandler.extract_zip(content)

        elif file_type == "tar":
            extracted_files = FileHandler.extract_tar(content)

        return extracted_files

    @staticmethod
    def extract_zip(content: bytes) -> list:
        """Extract files from ZIP archive."""

        extracted_files = []

        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:

            for file_info in zip_ref.infolist():

                if file_info.is_dir():
                    continue

                inner_filename = file_info.filename
                base_name = inner_filename.split("/")[-1]

                if base_name.startswith(".") or base_name.startswith("__"):
                    continue

                if not FileHandler.is_supported(base_name) or FileHandler.is_archive(base_name):
                    continue

                file_content = zip_ref.read(file_info.filename)
                extracted_files.append((base_name, file_content))

        return extracted_files

    @staticmethod
    def extract_tar(content: bytes) -> list:
        """Extract files from TAR/TAR.GZ archive."""

        extracted_files = []

        with tarfile.open(fileobj=io.BytesIO(content), mode='r:*') as tar_ref:

            for member in tar_ref.getmembers():

                if not member.isfile():
                    continue

                inner_filename = member.name
                base_name = inner_filename.split("/")[-1]

                if base_name.startswith(".") or base_name.startswith("__"):
                    continue

                if not FileHandler.is_supported(base_name) or FileHandler.is_archive(base_name):
                    continue

                file_obj = tar_ref.extractfile(member)
                if file_obj:
                    file_content = file_obj.read()
                    extracted_files.append((base_name, file_content))

        return extracted_files

    @staticmethod
    def process_extracted_content(filename: str, content: bytes) -> list:
        """Process extracted file content (from archive)."""

        file_type = FileHandler.get_file_type(filename)

        if file_type == "pdf":
            return FileHandler.process_pdf(content)

        elif file_type == "image":
            return FileHandler.process_image(content)

        elif file_type == "word":
            return FileHandler.process_word(content, FileHandler.get_file_extension(filename))

        else:
            return FileHandler.try_as_image(content, filename)

    @staticmethod
    def prepare_image(image, max_size=(1000, 1000)) -> Image.Image:
        """
        Prepare image for OCR:
        - Handle transparency (RGBA, P, LA modes)
        - Convert to RGB
        - Resize to max_size
        """

        if image.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(
                image,
                mask=image.split()[-1] if "A" in image.mode else None
            )
            image = background
        else:
            image = image.convert("RGB")

        image.thumbnail(max_size)

        return image

    @staticmethod
    def image_to_bytes(image: Image.Image, quality: int = 85) -> bytes:
        """Convert PIL Image to JPEG bytes."""

        buffer = io.BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=quality
        )

        return buffer.getvalue()
