import boto3
from botocore.config import Config
from app.core.config import settings
from fastapi import UploadFile
import uuid
import os

class S3Storage:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
        self.bucket = settings.S3_BUCKET_NAME

    async def upload_file(self, file: UploadFile, folder: str) -> dict:
        """Uploads a file to S3 and returns metadata."""
        # Calculate file size before uploading
        content = await file.read()
        file_size = len(content)
        await file.seek(0) # Reset file pointer for the actual upload

        file_extension = os.path.splitext(file.filename)[1]
        # Generate a unique key for medical privacy and to avoid collisions
        file_key = f"{folder}/{uuid.uuid4()}{file_extension}"
        
        # Upload the file
        self.s3.upload_fileobj(
            file.file,
            self.bucket,
            file_key,
            ExtraArgs={
                "ContentType": file.content_type
            }
        )
        
        return {
            "path": file_key,
            "name": file.filename,
            "mime": file.content_type,
            "size": file_size
        }

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600):
        """Generates a temporary URL to view a private file."""
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': file_key},
            ExpiresIn=expires_in
        )

    def delete_file(self, file_key: str):
        """Deletes a file from the bucket."""
        self.s3.delete_object(Bucket=self.bucket, Key=file_key)

s3_storage = S3Storage()
