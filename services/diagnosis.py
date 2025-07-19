from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from fastapi import HTTPException
from models.diagnosis import Diagnosis as DiagnosisModel
from schema.diagnosis import DiagnosisData


import json
import base64
import logging
from services.diseases import generate_disease_info_stream_service # Import from diseases service

logger = logging.getLogger(__name__)

def delete_diagnosis(db: Session, user_id: int, diagnosis_id: int):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id, Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="진단 정보가 없습니다")

    diagnosis.diseases.clear()
    diagnosis.symptoms.clear()
    diagnosis.skin_type = None

    db.delete(diagnosis)
    db.commit()

    return diagnosis

def get_diagnosis_table(db: Session):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.is_deleted == False).all()
    return [DiagnosisData.model_validate(diagnosis) for diagnosis in diagnoses]

async def generate_and_save_detailed_disease_info(
    db: Session, image_bytes: bytes, disease_name: str
) -> int:
    """
    Generates detailed disease info via streaming, aggregates it, and saves to DB.
    Returns the ID of the newly created record.
    """
    # Initialize data structures to aggregate streamed content
    image_analysis_data = {}
    text_analysis_data = {
        "ai_opinion": "",
        "detailed_description": "",
        "precautions": [],
        "management": {}
    }

    # Convert image bytes to base64 for storage
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # Iterate through the streaming service to collect all data
    async for event_str in generate_disease_info_stream_service(image_bytes, disease_name):
        # Extract JSON part from SSE format: "data: {json_string}\n\n"
        if event_str.startswith("data: "):
            try:
                event_json = json.loads(event_str[len("data: "):].strip())
                event_type = event_json.get("type")
                event_data = event_json.get("data")

                if event_type == "image_analysis":
                    image_analysis_data = event_data
                elif event_type == "ai_opinion_chunk":
                    text_analysis_data["ai_opinion"] += event_data + " "
                elif event_type == "detailed_description_chunk":
                    text_analysis_data["detailed_description"] += event_data + " "
                elif event_type == "precautions_item_start":
                    # For precautions, we need to handle items as they come
                    # This assumes precautions are streamed item by item
                    text_analysis_data["precautions"].append("") # Add a new empty string for the current precaution
                elif event_type == "precautions_chunk":
                    if text_analysis_data["precautions"]:
                        text_analysis_data["precautions"][-1] += event_data + " "
                current_management_key = None
    async for event_str in generate_disease_info_stream_service(image_bytes, disease_name):
        if event_str.startswith("data: "):
            try:
                event_json = json.loads(event_str[len("data: "):].strip())
                event_type = event_json.get("type")
                event_data = event_json.get("data")
                if event_type == "management_item_start":
                    current_management_key = event_data
                    text_analysis_data["management"][current_management_key] = ""
                elif event_type == "management_chunk":
                    if current_management_key in text_analysis_data["management"]:
                        text_analysis_data["management"][current_management_key] += event_data + " "

            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from SSE event: {e} - {event_str}")
            except Exception as e:
                logger.error(f"Error processing SSE event: {e} - {event_str}")

    # Clean up trailing spaces from collected text data
    text_analysis_data["ai_opinion"] = text_analysis_data["ai_opinion"].strip()
    text_analysis_data["detailed_description"] = text_analysis_data["detailed_description"].strip()
    text_analysis_data["precautions"] = [p.strip() for p in text_analysis_data["precautions"]]
    for key, value in text_analysis_data["management"].items():
        text_analysis_data["management"][key] = value.strip()

    # Create a DetailedDiseaseInfoCreate schema object
    detailed_info_data = DetailedDiseaseInfoCreate(
        disease_name=disease_name,
        image_base64=image_base64,
        skin_score=image_analysis_data.get("skin_score"),
        severity=image_analysis_data.get("severity"),
        estimated_treatment_period=image_analysis_data.get("estimated_treatment_period"),
        ai_opinion=text_analysis_data.get("ai_opinion"),
        detailed_description=text_analysis_data.get("detailed_description"),
        precautions=text_analysis_data.get("precautions"),
        management=text_analysis_data.get("management"),
    )

    from models.detailed_disease_info import DetailedDiseaseInfo
    detailed_info_data_dict = detailed_info_data.model_dump()
    detailed_info_data_dict['precautions'] = json.dumps(detailed_info_data_dict['precautions'], ensure_ascii=False)
    detailed_info_data_dict['management'] = json.dumps(detailed_info_data_dict['management'], ensure_ascii=False)
    db_detailed_info = DetailedDiseaseInfo(**detailed_info_data_dict)
    db.add(db_detailed_info)
    db.commit()
    db.refresh(db_detailed_info)

    return db_detailed_info.id

