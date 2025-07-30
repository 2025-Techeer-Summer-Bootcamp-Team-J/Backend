from fastapi import UploadFile, File, HTTPException
from google.cloud import storage
import uuid
from models.diagnosis import Diagnosis
from database.database import get_db

BUCKET_NAME = "ppikkappeonjjeog-storage"
# GCS 클라이언트 초기화
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

async def upload_image(file: UploadFile = File(...)):
    try:
        # 고유 파일명 생성
        file_ext = (file.filename or "bin").split(".")[-1]
        blob_name = f"{uuid.uuid4()}.{file_ext}"
        blob = bucket.blob(blob_name)

        # 파일 내용을 읽고 업로드
        contents = await file.read()

        blob.upload_from_string(contents, content_type=file.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_image_url(diagnosis_id: int):
    db = next(get_db())
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return diagnosis.image


def download_model_from_gcs(bucket_name, source_blob_name, destination_file_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(f"Downloaded {source_blob_name} from GCS bucket {bucket_name} to {destination_file_name}")