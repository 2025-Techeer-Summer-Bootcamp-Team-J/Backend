"""RAG 프롬프트와 출력 스키마를 정의합니다."""

from langchain.prompts import ChatPromptTemplate

__all__ = [
    "OUTPUT_SCHEMA",
    "PROMPT_TEMPLATE",
]

# ---- Prompt 및 출력 스키마 ----
OUTPUT_SCHEMA: str = """{
    "image_analysis": {
        "skin_score": "(예시: 1~100사이의 정수)",
        "estimated_treatment_period": "(예시: 2-4주등 의 기간)"
    },
    "disease_name": "질병명(한국어)",
    "photo_url": "신뢰할 수 있는 사이트의 사진 URL",
    "detailed_description": "정의|특징(증상)|원인을 포함한 설명",
    "precautions": ["주의점1", "주의점2", "주의점3"],
    "management": {
        "일상 관리법(가정에서의 피부 관리, 샤워법 등)": "",
        "의학적 치료법(연고, 경구약, 물리치료 등)": "",
        "생활습관(재발 방지법, 환경 개선법)": "",
        "기타": ""
    },
    "출처": {
        "기관명": "",
        "출처url": ""
    }
}"""

PROMPT_TEMPLATE: str = (
    "너는 피부과 전문의 AI 어시스턴트다. 제공된 참고 문서를 바탕으로 질문에 답해라.\n"
    "이미지 분석 결과를 참고하여 질문에 답해라.\n"
    "보고서 형식으로 답해라.\n"
    "문맥(참고 문서):\n{context}\n\n"
    "사용자 증상: {symptoms}\n\n"
    "질문: {question}\n\n"
    "다음 JSON 형식으로만 대답해. 다른 설명은 금지.\n"
    "{output_schema}에 있는 모든 내용을 답해라"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", PROMPT_TEMPLATE),
])



