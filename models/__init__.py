# 순환 참조 문제를 피하기 위해 모든 모델 임포트
from .diseases import Disease
from .skintype import SkinType  
from .symptom import Symptom
from .user import User
from .diagnosis import Diagnosis
from .user_skintype import UserSkinType
# 모든 모델이 사용 가능하도록 보장
__all__ = [
    "Disease",
    "SkinType", 
    "Symptom",
    "User",
    "Diagnosis",
    "UserSkinType"
]
