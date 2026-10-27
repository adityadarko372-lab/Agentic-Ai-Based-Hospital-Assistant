"""Public hospital directory."""


def test_departments_are_seeded_from_the_knowledge_file(client):
    response = client.get("/api/hospital/departments")

    assert response.status_code == 200
    departments = response.json()
    ids = [department["id"] for department in departments]
    assert ids[0] == "general-medicine"
    assert {"cardiology", "paediatrics", "emergency", "laboratory"} <= set(ids)
    assert len(ids) == len(set(ids))


def test_emergency_and_walk_in_services_do_not_take_appointments(client):
    departments = {d["id"]: d for d in client.get("/api/hospital/departments").json()}

    assert departments["emergency"]["accepts_appointments"] is False
    assert departments["laboratory"]["accepts_appointments"] is False
    assert departments["general-medicine"]["accepts_appointments"] is True


def test_hospital_info_is_marked_as_demo_and_lists_indian_emergency_numbers(client):
    body = client.get("/api/hospital/info").json()

    assert body["hospital"]["is_demo"] is True
    assert "FICTIONAL" in body["notice"]
    assert [entry["number"] for entry in body["emergency_numbers"]] == ["112", "108"]
    assert body["appointment_guidance"]["what_to_bring"]


def test_seeding_twice_does_not_duplicate_data(database_path):
    from tests.conftest import build_client

    for _ in range(2):
        with build_client(database_path) as client:
            departments = client.get("/api/hospital/departments").json()
    assert len(departments) == 11
