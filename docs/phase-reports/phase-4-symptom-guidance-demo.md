# Phase 4 Report: Symptom Guidance, Demo Hardening and v0.1-required-scope

**Date:** 28 October 2026
**Plan reference:** [`docs/first report.md`](../first%20report.md), Phase 4 (Tasks 9 and 10)
**Status:** Complete. Every acceptance criterion was checked (section 7). Tagged **`v0.1-required-scope`**.

---

## 1. What this phase was meant to do

1. **Module 4 – Preliminary Symptom Guidance:** a form for symptoms, duration and general information (age group, severity, pregnancy, long-term condition).
   - Warning signs show the emergency card straight away (112 / 108).
   - Otherwise the result is a level of care, a suggested department, a "Request appointment" button that pre-fills the form, and a permanent disclaimer.
   - The **form and the chat must give the same result** for the same input.
2. **Demo hardening:**
   - a browser test of the whole 6-step demonstration, with screenshots;
   - an accessibility check and a mobile layout check;
   - `implementation-status.md`, `demo-script.md` and `setup.md`;
   - the tag `v0.1-required-scope`.

---

## 2. What was actually built

### Backend
- **`GET /api/care-navigation/options`** (public, no personal data). Returns:
  - the 12 warning signs and 19 symptom choices, read from `care_rules.json`;
  - the duration, severity and age-group choices;
  - the emergency numbers, the disclaimer and the rules version.
- **`POST /api/care-navigation/assess`** (signed-in patients):
  - The form's answers go straight into **`care_engine.evaluate()`**, the same engine the Care Navigation Agent uses in the chat. There is no second set of rules.
  - Duration choices map to fixed day counts that fall on the right side of each rule's threshold: under a day = 0.5, 1–3 days = 2, 4–7 days = 5, 1–3 weeks = 14, over 3 weeks = 30.
- **Validation:** symptoms must come from the list, and the patient must either tick something or write at least 3 characters. Durations and severities must be one of the options, and the free text is limited to 500 characters. All errors come back as friendly per-field messages. I also improved the error handler, which now reports list-item errors under the field name and explains "choose one of the options" in plain words.
- **Traced like a chat message:** every submission is saved as an agent run handled by the **Care Navigation Agent** (method `form`), with 4 steps: received the form → Safety Gate → applied care rules → recorded outcome. It appears on the Agent Activity page and in the dashboard's recent activity. The activity line uses fixed wording only; the patient's own description is **not** copied into it.

### Frontend: Symptom Guidance page
- **"Is any of these happening right now?"** is a red-tinted group with the 12 warning signs. Ticking one **immediately** shows *"Get emergency help now. Don't wait for this form."* with tap-to-call **112** and **108**, or **14416** (Tele-MANAS) for self-harm, before anything is submitted. The form can then be sent without answering anything else.
- **Your symptoms:** 19 tick boxes, plus "Describe it in your own words" with a character counter.
- **How long** and **How severe** are radio groups. Severe has a plain hint, e.g. "Very hard to bear or to carry on as usual". Both are required unless a warning sign is ticked.
- **Who is this for?** (baby, child, adult, older adult), **Currently pregnant**, and **Has a long-term condition**.
- **Your guidance** panel (sticky beside the form on desktop):
  - the Care Navigation Agent label and the rules version marked "not clinically reviewed";
  - the guidance card with level, suggested department, next steps, *Why this guidance?*, and **Request an appointment with …**, which opens the form with the department already selected;
  - or the red emergency card.
  - Below that: **Ask the assistant**, **Start again**, and *How the Care Navigation Agent decided*, which opens the full step timeline.
- Keyboard focus moves to "Your guidance" when the result arrives, and the panel announces changes to screen readers.

### Clean-up
- The "Not built yet" preview page was **deleted**: all five modules are now real pages.
- The backend version is now **`0.1.0-required-scope`**.

### Accessibility fixes (found by the new axe check)
| Problem (axe rule) | Fix |
|---|---|
| Logo, "Ask Nova" button and "Request appointment" links had a hidden name that didn't start with the visible words (`label-content-name-mismatch`, WCAG 2.5.3) | Accessible names now start with the visible text, e.g. "Nova Health Hospital Assistant, go to dashboard", "Ask Nova, open the AI Assistant" |
| Loading placeholders had `aria-label` on a plain `<div>` (`aria-prohibited-attr`) | Added `role="status"`, so screen readers now also announce "Loading…" |
| Source line under chat answers was slightly too pale (`color-contrast`) | Darker text colour |

### Documentation
- `docs/demo-script.md`: what to click and what to say for each of the 6 steps, optional extras, and likely examiner questions.
- `docs/setup.md`: requirements, setup, start, reset, tests, configuration and troubleshooting.
- `docs/implementation-status.md`: implemented, simulated and future work, mapped to `partial implementation.md` sections 5 and 6.
- README: links to all of these, and the new endpoints.

---

## 3. How the form works

```
Form (ticks, free text, duration, severity, age group, pregnancy, long-term condition)
  │  ticking a warning sign → instant emergency box (112 / 108 / 14416) on the page
  ▼  POST /api/care-navigation/assess
care_service.validate → CareInput(symptom_ids, free_text, duration_days, ...)
  ▼
care_engine.evaluate()   ← exactly the same function the chat agent calls
  ▼
AgentRun "symptom_form" + 4 AgentSteps + activity event   (Care Navigation Agent)
  ▼
{ assessment, run } → guidance card or emergency card + "How it decided" timeline
```

---

## 4. Important files

| File | Purpose |
|---|---|
| `backend/app/services/care_service.py` | Form choices, validation, evaluation, trace |
| `backend/app/api/care_navigation.py` | `/options` and `/assess` |
| `backend/app/schemas.py` | `CareAssessRequest`, `CareAssessResponse` |
| `backend/app/core/errors.py` | Clearer validation messages |
| `backend/tests/test_care_form.py` | 36 new tests |
| `frontend/src/pages/SymptomGuidancePage.tsx` | Module 4 page |
| `frontend/tests/symptomGuidance.test.tsx` | 6 new component tests |
| `frontend/e2e/demo.spec.ts` | The 6-step demonstration, with screenshots |
| `frontend/e2e/accessibility.spec.ts` | axe WCAG 2.1 A/AA check on every page |
| `docs/screenshots/demo-step*.png` | 14 screenshots (7 views × desktop and phone) |
| `docs/demo-script.md`, `setup.md`, `implementation-status.md` | Delivery documents |

New dev-only dependency: `@axe-core/playwright` (free, open source, used only by tests).

---

## 5. Commands

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"
cd backend;  .\.venv\Scripts\python.exe -m pytest -q
cd frontend; npm.cmd run typecheck; npm.cmd test; npm.cmd run build
cd frontend; npm.cmd run test:e2e                        # app must be running
cd frontend; npx.cmd playwright test demo                # just the 6-step demo
```

---

## 6. Decisions and changes from the plan

| Item | Decision | Why |
|---|---|---|
| "Mild cough for 3 days" | Gives **General self-care information**, not "Routine" as the plan's example said | That is what the Phase 3 rules (already tested) decide for a mild, short cough with no warning signs. The rules weren't changed just to match an example. |
| Warning signs on the form | Shown **on the page as soon as they are ticked** | The spec says serious symptoms must not wait for routine questions. |
| Form requires duration and severity | Yes, unless a warning sign is ticked | Without them the engine can't apply its duration and severity rules. |
| Form runs in the activity history | Saved as Care Navigation Agent runs (method `form`) | Step 6 should show every request, including the form. |
| Restart persistence | Not repeated | Already verified with a real server restart in Phase 2. Phase 4 changed no storage code. |
| Accessibility tool | axe-core via Playwright, reduced motion on | Free, standard and repeatable. Reduced motion means text is checked after its fade-in, not half-way through. |

---

## 7. Tests actually run and their real results

All run on this laptop on 28 October 2026, after the last code change.

| Check | Result |
|---|---|
| Backend tests (`pytest`) | **209 passed** (173 earlier + 36 new) |
| Frontend typecheck | **0 errors** |
| Frontend tests (`vitest run`) | **57 passed** (7 files, 6 new) |
| Production build | **Succeeded** (JS 477 kB / 148 kB gzipped) |
| Browser tests (Playwright, Edge, desktop 1440 px + phone 390 px) | **28 passed** in 1.0 min |
| Accessibility (axe, WCAG 2.0/2.1 A + AA) | **No serious or critical violations** on login, dashboard, services, appointments, agent activity, design system, assistant (with an emergency reply) and symptom guidance (with a result), desktop and phone |

**What the new backend tests cover:**
- The options match the rules file.
- Sign-in is required to submit.
- A mild cough gives self-care guidance, and the run (4 steps, method `form`) appears in the history and the activity feed.
- **Every one of the 12 warning signs**, ticked alone, gives emergency guidance with 112 and no appointment option.
- A warning sign typed in the free text overrides mild answers.
- Self-harm gives 112 + 14416.
- **The form and the chat give the same level and department in 5 cases:** cough, knee pain, severe stomach pain, a child's cough and chest pain.
- Long duration, older age, pregnancy and a baby with fever raise the level.
- An unrecognised description asks for more.
- 6 invalid inputs are rejected with the right message.
- Free text is not copied into the activity feed.
- Form runs are private to each patient.
- 4 results checked contain no condition or medicine names.

**What the new frontend tests cover:**
- Required-field messages, with nothing sent.
- The instant emergency box with tel: links.
- Self-harm shows 14416.
- The exact request body sent to the server.
- The guidance card, the "Request an appointment" link and focus moving to the result.
- The emergency result has no appointment link.
- **Start again** clears everything.

**What the browser demo test covers (real backend):**
- Step 1: dashboard.
- Step 2: "Which department should I visit?" is answered by the Patient Assistance Agent.
- Step 3: "I want to book an appointment" is routed to the Appointment Agent.
- Step 4: Dermatology, in 10 days, a reason, then yes, gives `NH-APT-####` **Pending**, also visible under Appointments.
- Step 5: Cough, 1–3 days, Mild gives self-care guidance and "not a diagnosis"; ticking chest pain shows the instant emergency box, and the result has tap-to-call 112.
- Step 6: Agent Activity lists Patient Assistance, Appointment and Care Navigation runs, and the form run shows "Received the symptom form".
- The test then cancels its request to tidy up.

**Problems found and fixed:**
1. A Vitest query matched two elements; this was a test-only fix.
2. The three accessibility issues in section 2.
3. The contrast warning appeared only while a reply was fading in on the phone layout. It was fixed in CSS anyway, and the check now runs with reduced motion.

---

## 8. Implemented, simulated and future work

See [`docs/implementation-status.md`](../implementation-status.md). In short:
- **Implemented:** all 5 modules, the 3 specialist agents with the Supervisory Agent and Safety Gate, SQLite persistence, the activity panel and history, and the 6-step demo.
- **Simulated:** the hospital and its details, the patients, scheduling (requests stay Pending), and template wording.
- **Future / optional (Phase 5):** front-desk review, MedQuAD health information, trained classifier, Ollama, voice input.

---

## 9. Known limitations

- **The care rules** are fixed, written for the prototype, and **not clinically reviewed**. Automated accessibility checks cover only part of WCAG; there has been no manual screen-reader audit.
- **Grouped durations:** the form's durations are bands, so "1 to 3 weeks" counts as 14 days. Exact wording is still read from the free text.
- **Pregnancy and long-term conditions** only raise the level in the specific rules listed in `care_engine.py`.
- **Browser tests write to the running backend's database** (and tidy up). Run `scripts\reset-demo-data.ps1` before the examination.

---

## 10. Current state and next steps

**The required scope is complete:** `v0.1-required-scope` is tagged and pushed.

**Optional Phase 5 (Days 6–7), in the plan's priority order, each behind its own setting:**
1. Front-desk review page (staff confirm or decline Pending requests).
2. MedQuAD general health information with NIH citations.
3. A trained DistilBERT intent classifier on the RTX 4060, adopted only if it measurably beats the rules.
4. Ollama phrasing and voice input.

Keep Day 7 afternoon for the final regression run and a demo rehearsal using `docs/demo-script.md`.
