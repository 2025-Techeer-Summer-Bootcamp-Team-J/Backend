"""RAG 프롬프트와 출력 스키마를 정의합니다."""

from langchain.prompts import ChatPromptTemplate

__all__ = [
    "OUTPUT_SCHEMA",
    "PROMPT_TEMPLATE",
]

# ---- Prompt 및 출력 스키마 ----
OUTPUT_SCHEMA: str = """{
    "image_analysis": {
        "skin_score": "(100점(완벽하게 깨끗한 피부)에서 시작합니다. 아래 기준에 따라 최종 점수를 계산하세요. 질병명을 입력받았을때 -5점 차감. 질환의 심각도: 단순 발진(-15), 구진/농포(-20), 수포/물집(-25). 병변의 밀도: 드문드문 분포(-10), 일부 밀집(-15), 광범위 밀집(-25). 영향 범위: 작은 국소 부위(-5), 중간 크기(-10), 넓은 부위(-20))",
        "estimated_treatment_period": "(예시: 2-4주등 의 기간, skin_score바탕으로 계산)"
    },
    "disease_name": "질병명(한국어)",
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
    "제일 먼저 입력된 사진으로 질병 명을 판단하고 입력 받은 질병 명은 참고만 하라.\n"
    "skin_score: 1~100사이의 정수.\n"
    "문맥(참고 문서):\n{context}\n\n"
    "사용자 증상: {symptoms}\n\n"
    "질문: {question}\n\n"
    "다음 JSON 형식으로만 대답해. 다른 설명은 금지.\n"
    "출처를 입력할때는 저장된 URL을 사용하거나 아니면 아예 쓰지마라.\n"
    "답변할때 null은 금지.\n"
    "{output_schema}에 있는 모든 내용을 답해라"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", PROMPT_TEMPLATE),
])



