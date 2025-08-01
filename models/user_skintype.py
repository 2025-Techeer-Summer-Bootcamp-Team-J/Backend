from sqlalchemy import Column, ForeignKey, Integer, VARCHAR, DateTime, Boolean, func
from database.database import Base
from sqlalchemy.orm import relationship

class UserSkinType(Base):
    __tablename__ = "USER_SKINTYPE"
    user_id = Column(VARCHAR(255), ForeignKey('USER.user_id'), primary_key=True)
    skin_type_id = Column(Integer, ForeignKey('SKINTYPE.skin_type_id'), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    user = relationship("User", back_populates="skintypes")
    skintypes = relationship("SkinType", back_populates="users")
