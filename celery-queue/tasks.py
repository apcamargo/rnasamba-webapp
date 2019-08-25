import os

from celery import Celery
from rnasamba import RNAsambaClassificationModel


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')


celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task
def start_rnasamba(input_file_path, output_file_path, model):
    model_path = os.path.join('/', 'queue', 'models', model)
    classification = RNAsambaClassificationModel(input_file_path, [model_path], verbose=2)
    classification.write_classification_output(output_file_path)
