from config.celery import app
import logging

logger = logging.getLogger(__name__)

@app.task(name='tasks.skintype.process_skintype')
def process_skintype_task():
    """
    피부타입 처리를 위한 Celery 태스크 (향후 확장용)
    """
    logger.info("Skintype task placeholder")
    return {"status": "success", "message": "Skintype task executed"}