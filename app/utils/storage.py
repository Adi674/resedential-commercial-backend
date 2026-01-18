# app/utils/storage.py
import os
import uuid
from fastapi import UploadFile, HTTPException, status
from supabase import create_client, Client
from storage3.exceptions import StorageApiError

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def upload_file_to_supabase(file: UploadFile, bucket_name: str) -> str:
    """
    Uploads a file to Supabase Storage and returns the Public URL.
    Handles errors like file size limits or connection issues.
    """
    try:
        # 1. Generate a unique filename
        file_ext = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        
        # 2. Read file content
        file_content = await file.read()
        
        # 3. Upload with Error Handling
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # 4. Get Public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        
        return public_url

    except StorageApiError as e:
        # Check specifically for "Payload too large" (413)
        error_msg = str(e).lower()
        if "payload too large" in error_msg or "413" in error_msg:
             raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' is too large. Please upload a smaller file (Check Supabase Bucket limits)."
            )
        
        # Handle other Supabase errors (Permissions, Bucket not found, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase Storage Error: {e}"
        )

    except Exception as e:
        # Handle unexpected Python errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while uploading: {str(e)}"
        )