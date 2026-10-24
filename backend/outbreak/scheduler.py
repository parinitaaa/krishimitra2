"""
outbreak/scheduler.py

Outbreak evaluation is event-driven: schedule_outbreak_evaluation() is called
from whatsapp_service when a disease case is created or severity is reported.
The legacy 100-second polling job on the detections table is removed per DEMO-O.
"""


def register_jobs(sched):
    """No polling jobs — outbreak alerts are event-driven via disease_cases."""
    pass
