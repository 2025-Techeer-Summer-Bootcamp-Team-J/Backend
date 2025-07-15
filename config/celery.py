from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue  # kombu에서 Queue와 Exchange 임포트
import logging

# 로컬 개발환경을 위한 직접 설정
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/1"

app = Celery('config',
              include=['tasks.diagnosis', 'tasks.skintype'],
              broker=broker_url,
              backend=result_backend,
              broker_transport_options={'visibility_timeout': 3600})

# 태스크 자동 발견 및 명시적 임포트
app.autodiscover_tasks()

# 명시적으로 태스크 모듈 임포트
try:
    from tasks import diagnosis, skintype
except ImportError as e:
    logging.getLogger(__name__).error(f"태스크 모듈 임포트 실패: {str(e)}")


# 큐 설정
app.conf.task_queues = (
    Queue('diagnosis_queue', Exchange('diagnosis', type='direct'), routing_key='diagnosis_queue'),
    Queue('skintype_queue', Exchange('skintype', type='direct'), routing_key='skintype_queue'),
    Queue('default', Exchange('default', type='direct'), routing_key='default')
)

# 라우팅 설정
app.conf.task_routes = {
    'tasks.diagnosis.process_diagnosis': {'queue': 'diagnosis_queue'},
    'tasks.skintype': {'queue': 'skintype_queue'},
}

# 기본 큐 설정
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

logger = logging.getLogger(__name__)
logger.info("Celery app configured for FastAPI project.")
# logger.info("Current Celery Beat schedule: %s", app.conf.beat_schedule)
