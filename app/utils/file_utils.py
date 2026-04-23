import os
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

class FileUtils:
    ALLOWED_DOCUMENT_TYPES = {
        'application/pdf': 'pdf',
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'text/plain': 'txt',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
    }
    
    ALLOWED_AUDIO_TYPES = {
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/m4a': 'm4a',
        'audio/ogg': 'ogg'
    }

    @staticmethod
    def validate_file(file: UploadFile, allowed_types: dict) -> Tuple[str, str]:
        """Validate uploaded file and return extension and mime type."""
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed. Allowed types: {list(allowed_types.keys())}"
            )
        
        extension = allowed_types[file.content_type]
        return extension, file.content_type

    @staticmethod
    def generate_unique_filename(original_filename: str, extension: str) -> str:
        """Generate unique filename with original extension."""
        # Remove original extension if present
        base_name = os.path.splitext(original_filename)[0]
        unique_id = str(uuid.uuid4())
        return f"{base_name}_{unique_id}.{extension}"

    @staticmethod
    def save_uploaded_file(file: UploadFile, upload_dir: str, filename: str) -> str:
        """Save uploaded file to disk."""
        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        
        try:
            with open(file_path, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
            
            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        finally:
            file.file.close()

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete file from disk."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except OSError:
            return False

    @staticmethod
    def validate_file_size(file_size: int, max_size: int = None) -> bool:
        """Validate file size against maximum allowed size."""
        if max_size is None:
            max_size = settings.MAX_FILE_SIZE
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file_size} exceeds maximum allowed size {max_size}"
            )
        
        return True

class DocumentHandler(FileUtils):
    """Handler for document uploads."""
    
    def __init__(self, upload_dir: str = None):
        if upload_dir is None:
            upload_dir = os.path.join(settings.UPLOAD_DIR, "documents")
        self.upload_dir = upload_dir

    async def handle_upload(self, file: UploadFile, referral_id: int, uploaded_by: int) -> dict:
        """Handle document upload and return file metadata."""
        # Validate file type
        extension, mime_type = self.validate_file(file, self.ALLOWED_DOCUMENT_TYPES)
        
        # Generate unique filename
        filename = self.generate_unique_filename(file.filename, extension)
        
        # Save file
        file_path = self.save_uploaded_file(file, self.upload_dir, filename)
        
        # Get file size
        file_size = self.get_file_size(file_path)
        
        # Validate file size
        self.validate_file_size(file_size)
        
        return {
            "file_path": file_path,
            "file_name": filename,
            "file_type": extension,
            "file_size": file_size,
            "mime_type": mime_type
        }

class AudioHandler(FileUtils):
    """Handler for audio file uploads."""
    
    def __init__(self, upload_dir: str = None):
        if upload_dir is None:
            upload_dir = os.path.join(settings.UPLOAD_DIR, "audio")
        self.upload_dir = upload_dir

    async def handle_upload(self, file: UploadFile, referral_id: int, uploaded_by: int) -> dict:
        """Handle audio file upload and return file metadata."""
        # Validate file type
        extension, mime_type = self.validate_file(file, self.ALLOWED_AUDIO_TYPES)
        
        # Generate unique filename
        filename = self.generate_unique_filename(file.filename, extension)
        
        # Save file
        file_path = self.save_uploaded_file(file, self.upload_dir, filename)
        
        # Get file size
        file_size = self.get_file_size(file_path)
        
        # Validate file size (audio files can be larger)
        max_audio_size = settings.MAX_FILE_SIZE * 5  # Allow 5x larger for audio
        self.validate_file_size(file_size, max_audio_size)
        
        return {
            "audio_path": file_path,
            "audio_file_name": filename,
            "audio_file_size": file_size,
            "mime_type": mime_type
        }
