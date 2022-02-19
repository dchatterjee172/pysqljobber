DELIM = ":"


class Namespace:
    def __init__(self, namespace: str):
        self.namespace = namespace

    def __call__(self, other: str):
        return f"{self.namespace}{DELIM}{other}"


ROOT = Namespace("job_queue")
INFLIGHT_JOB_NAMESPACE = Namespace(ROOT("inflight_job"))
QUEUE_NAMESPACE = Namespace(ROOT("queue"))
QUEUE_PATTERN = f"{ROOT('queue')}{DELIM}*"
