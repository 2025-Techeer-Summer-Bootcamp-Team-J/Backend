from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.diseases import Disease
from schema.diseases import DiseaseCreate, DiseaseUpdate, DiseaseRead
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import asyncio
from PIL import Image
import io
import logging
import re # Import the re module

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")

async def generate_disease_info_stream_service(image_bytes: bytes, disease_name: str):
    """
    Processes image and text to generate disease info and streams it via SSE.
    Uses non-streaming API calls for better error handling and inspection.
    """
    raw_image_response_text = ""
    text_data_str = ""
    try:
        # 1. Analyze image for score, severity, and treatment period
        yield f"data: {json.dumps({"type": "status", "data": "Analyzing image..."}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        image_prompt = [
            "Based on the skin condition in this image, provide ONLY a JSON object with 'skin_score' (integer 0-100), 'severity' (e.g., 경증, 중등도, 중증), and 'estimated_treatment_period' (e.g., 2-4주). Do not include any other text, explanations, or disclaimers. All responses must be in Korean. The JSON object should be the ONLY content in the response.",
            Image.open(io.BytesIO(image_bytes))
        ]
        
        image_response = await model.generate_content_async(image_prompt)
        
        if not image_response.parts:
            logger.error(f"Image analysis returned no content. API response: {image_response}")
            raise ValueError("Image analysis returned no content. This might be due to safety filters or an empty response.")

        raw_image_response_text = image_response.text
        logger.info(f"Raw image analysis response text: {raw_image_response_text}")

        image_data = {"skin_score": 0, "severity": "분석 불가", "estimated_treatment_period": "분석 불가"} # Default values
        try:
            # Use regex to extract JSON block
            json_match = re.search(r"```json\n([\s\S]*?)\n```", raw_image_response_text)
            if json_match:
                image_data_str = json_match.group(1).strip()
            else:
                # If no ```json``` block, try to parse the whole response as JSON
                image_data_str = raw_image_response_text.strip()
                logger.warning("No ```json``` block found in image response. Attempting to parse entire response as JSON.")

            if not image_data_str:
                raise ValueError("Image analysis returned an empty string or no parsable JSON. Cannot parse JSON.")

            logger.info(f"Cleaned image analysis response: {image_data_str}")
            image_data = json.loads(image_data_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error during image analysis: {e}. Response text was: {raw_image_response_text}")
            yield f"data: {json.dumps({"type": "error", "data": f"이미지 분석 JSON 파싱 실패: {e}. 기본값을 사용합니다."}, ensure_ascii=False)}\n\n"
        except ValueError as e:
            logger.error(f"Value Error during image analysis: {e}. Response text was: {raw_image_response_text}")
            yield f"data: {json.dumps({"type": "error", "data": f"이미지 분석 오류: {e}. 기본값을 사용합니다."}, ensure_ascii=False)}\n\n"
        
        yield f"data: {json.dumps({"type": "image_analysis", "data": image_data}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        # 2. Generate text-based info using the disease name
        yield f"data: {json.dumps({"type": "status", "data": "Generating details..."}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        text_prompt = f'''
        Please provide concise information about the following skin disease: {disease_name}.
        The output should be in a JSON object with the following structure. All responses must be in Korean.

        {{
        "ai_opinion": "A very brief summary and core recommendations (in Korean, 1-2 sentences).",
        "detailed_description": "1. 정의: A brief, one-sentence definition of {disease_name}. 2. 특징: List 2-3 main symptoms as keywords. 3. 원인: List 2-3 main causes as keywords. (respond in Korean, clearly separated by number)",
        "precautions": [
        "A complete but brief sentence for precaution 1 (in Korean)",
        "A complete but brief sentence for precaution 2 (in Korean)",
        "A complete but brief sentence for precaution 3 (in Korean)"
        ],
        "management": [
        "Moisturizing: A complete but brief sentence (in Korean)",
        "Cleanliness: A complete but brief sentence (in Korean)",
        "Environment: A complete but brief sentence (in Korean)",
        "Clothing: A complete but brief sentence (in Korean)"
        ]
        }}
        '''
        
        text_response = await model.generate_content_async(text_prompt)

        if not text_response.parts:
            logger.error(f"Text analysis failed. API response: {text_response}")
            raise ValueError("Text analysis returned no content. This might be due to safety filters.")

        # Use regex to extract JSON block for text response as well
        json_match = re.search(r"```json\n([\s\S]*?)\n```", text_response.text)
        if json_match:
            text_data_str = json_match.group(1).strip()
        else:
            text_data_str = text_response.text.strip()
            logger.warning("No ```json``` block found in text response. Attempting to parse entire response as JSON.")

        if not text_data_str:
            raise ValueError("Text analysis returned an empty string or no parsable JSON. Cannot parse JSON.")

        logger.info(f"Raw text analysis response: {text_data_str}")

        text_data = json.loads(text_data_str)
        
        # Yield individual parts of the text analysis as separate events, word by word
        
        # AI Opinion
        yield f"data: {json.dumps({"type": "ai_opinion_start"}, ensure_ascii=False)}\n\n"
        for word in text_data.get("ai_opinion", "").split():
            yield f"data: {json.dumps({"type": "ai_opinion_chunk", "data": word}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05) # Small delay for streaming effect
        yield f"data: {json.dumps({"type": "ai_opinion_end"}, ensure_ascii=False)}\n\n"

        # Detailed Description
        yield f"data: {json.dumps({"type": "detailed_description_start"}, ensure_ascii=False)}\n\n"
        detailed_desc = text_data.get("detailed_description", {})
        for key, value in detailed_desc.items():
            yield f"data: {json.dumps({"type": "detailed_description_section_start", "data": key}, ensure_ascii=False)}\n\n"
            if isinstance(value, list):
                for item in value:
                    for word in item.split():
                        yield f"data: {json.dumps({"type": "detailed_description_chunk", "data": word}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)
            else: # Assuming it's a string
                for word in value.split():
                    yield f"data: {json.dumps({"type": "detailed_description_chunk", "data": word}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
            yield f"data: {json.dumps({"type": "detailed_description_section_end"}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({"type": "detailed_description_end"}, ensure_ascii=False)}\n\n"

        # Precautions
        yield f"data: {json.dumps({"type": "precautions_start"}, ensure_ascii=False)}\n\n"
        for i, precaution in enumerate(text_data.get("precautions", [])):
            yield f"data: {json.dumps({"type": "precautions_item_start", "data": i}, ensure_ascii=False)}\n\n"
            for word in precaution.split():
                yield f"data: {json.dumps({"type": "precautions_chunk", "data": word}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)
            yield f"data: {json.dumps({"type": "precautions_item_end"}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({"type": "precautions_end"}, ensure_ascii=False)}\n\n"

        # Management
        yield f"data: {json.dumps({"type": "management_start"}, ensure_ascii=False)}\n\n"
        # Assuming management is a dict now based on prompt, if it's a list, adjust here
        management_data = text_data.get("management", {})
        if isinstance(management_data, dict):
            for key, value in management_data.items():
                yield f"data: {json.dumps({"type": "management_item_start", "data": key}, ensure_ascii=False)}\n\n"
                for word in value.split():
                    yield f"data: {json.dumps({"type": "management_chunk", "data": word}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
                yield f"data: {json.dumps({"type": "management_item_end"}, ensure_ascii=False)}\n\n"
        elif isinstance(management_data, list):
            for i, item in enumerate(management_data):
                yield f"data: {json.dumps({"type": "management_item_start", "data": i}, ensure_ascii=False)}\n\n"
                for word in item.split():
                    yield f"data: {json.dumps({"type": "management_chunk", "data": word}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
                yield f"data: {json.dumps({"type": "management_item_end"}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({"type": "management_end"}, ensure_ascii=False)}\n\n"


    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}. Response text was: {raw_image_response_text if "raw_image_response_text" in locals() else (text_data_str if "text_data_str" in locals() else "N/A")}")
        error_message = json.dumps({"error": f"Failed to parse JSON response from API: {e}"}, ensure_ascii=False)
        yield f"data: {json.dumps({"type": "error", "data": error_message}, ensure_ascii=False)}\n\n"
    except ValueError as e:
        logger.error(f"Value Error: {e}")
        error_message = json.dumps({"error": str(e)}, ensure_ascii=False)
        yield f"data: {json.dumps({"type": "error", "data": error_message}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        error_message = json.dumps({"error": str(e)}, ensure_ascii=False)
        yield f"data: {json.dumps({"type": "error", "data": error_message}, ensure_ascii=False)}\n\n"
    finally:
        yield f"data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n"


def get_all_diseases_name(db: Session):
    diseases = db.query(Disease.disease_name).filter(Disease.is_deleted == False).all()
    return [result[0] for result in diseases]

def get_disease_table(db: Session):
    diseases = db.query(Disease).filter(Disease.is_deleted == False).all()
    return [DiseaseRead.model_validate(disease) for disease in diseases]

def create_disease(db: Session, disease: DiseaseCreate):
    new_disease = Disease(
        main_symptom=disease.main_symptom,
        disease_name=disease.disease_name,
        description=disease.description,
        precautions=disease.precautions
    )
    db.add(new_disease)
    db.commit()
    db.refresh(new_disease)
    return DiseaseRead.model_validate(new_disease)

def delete_disease(db: Session, disease_id: int):
    disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    
    disease_data = DiseaseRead.model_validate(disease)
    
    disease.diagnoses.clear()
    disease.skintypes.clear()

    db.delete(disease)
    db.commit()
    return disease_data

def update_disease(db: Session, disease_id: int, disease_update: DiseaseUpdate):
    db_disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not db_disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    
    update_data = disease_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_disease, key, value)
        
    db.commit()
    db.refresh(db_disease)
    return DiseaseRead.model_validate(db_disease)

def get_disease_by_id(db: Session, disease_id: int):
    disease = db.query(Disease).filter(Disease.is_deleted == False).first()
    if not disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    return DiseaseRead.model_validate(disease)
