"""A slow assistant reply must not block other patients' writes.

Regression test for a 500 seen in the Phase 5 browser run: the Supervisor
held SQLite's write lock for the whole message, so an appointment submitted
while an optional model was loading failed with "database is locked".
"""

import threading
import time

from app.agents import patient_assistance
from tests.conftest import PATIENT_B, auth_headers, valid_appointment


def test_appointment_is_saved_while_the_assistant_is_busy(client, monkeypatch):
    original = patient_assistance.handle

    def slow_handle(ctx):
        time.sleep(3)  # e.g. a model loading on first use
        return original(ctx)

    monkeypatch.setattr(patient_assistance, "handle", slow_handle)
    patient_a = auth_headers(client)
    patient_b = {**auth_headers(client, PATIENT_B), "Idempotency-Key": "concurrency-key-0001"}

    chat_status: list[int] = []
    chat = threading.Thread(
        target=lambda: chat_status.append(
            client.post("/api/assistant/message", json={"message": "What should I bring to my appointment?"}, headers=patient_a).status_code
        )
    )
    chat.start()
    time.sleep(0.5)  # the assistant request is now inside the slow agent

    started = time.perf_counter()
    response = client.post("/api/appointments", json=valid_appointment(patient_name="Rohan Mehta"), headers=patient_b)
    waited = time.perf_counter() - started
    chat.join()

    assert response.status_code == 201, response.text
    assert waited < 2, f"the appointment waited {waited:.1f}s for the assistant"
    assert chat_status == [200]
