from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue  # kombu에서 Queue와 Exchange 임포트
import logging 

# 환경변수를 통한 동적 설정 (Docker 환경과 로컬 환경 모두 지원)
# Docker 환경에서는 서비스 이름 'redis'를 사용, 로컬 환경에서는 localhost 사용
redis_host = os.getenv('REDIS_HOST', 'redis')  # Docker 환경에서는 'redis', 로컬에서는 'localhost'로 오버라이드
redis_port = os.getenv('REDIS_PORT', '6379')

broker_url = f"redis://{redis_host}:{redis_port}/0"
result_backend = f"redis://{redis_host}:{redis_port}/1"

app = Celery('config',
              include=['tasks.diagnosis', 'tasks.skintype'],
              broker=broker_url,
              backend=result_backend,
              broker_transport_options={'visibility_timeout': 3600})

# 태스크 자동 발견 및 명시적 임포트
app.autodiscover_tasks()

logger = logging.getLogger(__name__)
logger.info(f"Celery app configured with broker: {broker_url}")
logger.info(f"Celery app configured with result backend: {result_backend}")

# 명시적으로 태스크 모듈 임포트
try:
    from tasks import diagnosis, skintype
    logger.info("태스크 모듈 임포트 성공")
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


# logger.info("Current Celery Beat schedule: %s", app.conf.beat_schedule)
