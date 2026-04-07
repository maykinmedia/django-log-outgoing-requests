# Celery compat, in case celery is not installed
try:
    from celery import shared_task
except ImportError:

    def shared_task(func):
        class NoOpTask:
            def apply_async(self, *args, **kwargs):
                pass

        return NoOpTask()
