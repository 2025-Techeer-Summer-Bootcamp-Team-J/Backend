from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue  # kombu에서 Queue와 Exchange 임포트
import logging 
from models import *

# 환경변수를 통한 동적 설정 (Docker 환경과 로컬 환경 모두 지원)
# Docker 환경에서는 서비스 이름 'redis'를 사용, 로컬 환경에서는 localhost 사용
redis_host = os.getenv('REDIS_HOST', 'redis')  # Docker 환경에서는 'redis', 로컬에서는 'localhost'로 오버라이드
redis_port = os.getenv('REDIS_PORT', '6379')


broker_url = f"redis://{redis_host}:{redis_port}/0"
result_backend = f"redis://{redis_host}:{redis_port}/1"

app = Celery(
    'Backend',
    broker=broker_url,
    backend=result_backend,
    include=['tasks.diagnosis', 'tasks.skintype', 'tasks.uv_index']
)

# Celery 설정
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Seoul', # 시간대 설정
    enable_utc=False,
    broker_connection_retry_on_startup=True,
    # 주기적인 태스크 설정 (Celery Beat)
    beat_schedule={
        'update-uv-index-every-hour': {
            'task': 'tasks.uv_index.update_uv_index_task',
            'schedule': crontab(minute='*/1'), # 1분마다 실행
            'args': (),
            'kwargs': {},
            'options': {'queue': 'default'}
        },
        # 다른 주기적인 태스크가 있다면 여기에 추가
    }
)

# Celery worker가 태스크를 찾을 수 있도록 자동 디스커버리 설정
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

