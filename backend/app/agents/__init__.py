"""Nova Health multi-agent system (Module 3).

    supervisor.py           Supervisory Agent: safety gate -> intent -> route -> trace
    safety_gate.py          emergency warning signs and prompt-injection checks
    intent/                 IntentClassifier interface + transparent rule classifier
    patient_assistance.py   Patient Assistance Agent (hospital information)
    appointment_agent.py    Appointment Agent (book / status / cancel)
    care_navigation.py      Care Navigation Agent (preliminary guidance)
    care_engine.py          shared care-navigation rules engine (also used by the form)
"""
