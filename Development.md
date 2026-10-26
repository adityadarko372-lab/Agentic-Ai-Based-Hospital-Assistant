# HOSPIVANTA — MASTER DEVELOPMENT PLANNING PROMPT

## 1. Your role and authority

You are the principal software architect, senior full-stack engineer, AI/ML engineer, agentic systems specialist, UI/UX designer, testing engineer, and technical mentor responsible for planning and building Hospivanta.

You are entrusted with making the best technical and product decisions for this project. You have the freedom to correct my assumptions, improve features, choose appropriate AI and machine-learning techniques, simplify unnecessary complexity, and select better alternatives whenever doing so improves reliability, quality, explainability, safety, or the final demonstration.

Do not blindly follow a technically weak idea simply because I suggested it. Explain only important trade-offs and choose the most practical solution when the evidence is sufficient.

Your objective is to produce the strongest possible working partial implementation of Hospivanta within a seven-day deadline, with zero additional monetary cost.

## 2. Project context

Hospivanta is an Agentic AI-Based Hospital Assistant. Its complete product vision is described in the project context supplied separately.

The examiners have supplied a document titled `partial implementation.md`. Treat this document as the authoritative specification for the minimum demonstrable implementation. Read it carefully and preserve its intended scope.

The five required modules are:

1. Patient Dashboard.
2. AI Hospital Assistant.
3. Supervisory Agent coordinating specialized agents.
4. Preliminary Symptom Guidance.
5. Appointment Management.

The application must also demonstrate an activity or status panel that shows which agent handled a request and what happened.

The three specialist agents required by the partial implementation are:

- Patient Assistance Agent: answers hospital service and department questions.
- Appointment Agent: handles appointment requests and related workflows.
- Care Navigation Agent: provides cautious, preliminary symptom-related guidance.

The Supervisory Agent must receive user requests, identify their intent, route them to the appropriate specialist, coordinate the work, and return a coherent result.

All development begins from scratch. There is no existing implementation to rely on unless actual project files are discovered in the repository.

## 3. Hard constraints

Plan around the following requirements:

- Deadline: seven days from the start of development.
- Budget: zero additional monetary cost.
- Development environment: Kiro IDE.
- Preferred coding model: the Claude Opus model available in my Kiro account, identified in my account as Claude Opus 5.6.
- Version control: Git and GitHub, with regular commits and pushes whenever authentication and repository permissions permit.
- Available storage: approximately 100 GB free.
- Laptop CPU, RAM, and GPU specifications have not yet been provided. Do not assume GPU availability or sufficient memory for a large local language model.
- UI quality: premium, elegant, classic, rich, smooth, and visually impressive, using refined neumorphism with subtle depth, carefully controlled shadows, smooth animations, and excellent responsive behavior.
- Code quality: precise, modular, explainable, and appropriately documented.
- Directory structure: clearly separated areas such as Frontend, Backend, Datasets, Model, and Docs, with meaningful file and folder names.
- Reporting: after every major implementation phase, create a detailed Markdown report in the `docs` directory, written in friendly language that a student can understand and explain to examiners.
- Testing: test the actual user journeys and fix critical failures. Do not waste the deadline on repeated audits, redundant inspections, or separate phases that exist primarily to check work.
- Demonstration: the application must run reliably on my laptop and must not require purchasing an API subscription, dataset, hosting plan, or software licence.

Do not interpret the zero-cost requirement as permission to build an unreliable or unsafe application.

## 4. Your current task: planning only

You are currently operating in Plan mode.

Do not create the application, edit implementation files, install dependencies, download datasets, or begin implementation in this planning pass.

Produce an actionable plan that can be approved and handed over to an execution agent. Avoid an extended research exercise or an elaborate specification that consumes the available development time.

Do not ask unnecessary questions. Make sensible decisions independently. If a missing detail materially affects feasibility, identify it and provide a safe default so planning can continue.

## 5. Select the best practical architecture

Recommend a simple, maintainable architecture that can be implemented quickly and explained confidently during the examination.

Evaluate an appropriate combination of:

- A modern, responsive web frontend.
- A lightweight backend providing validated application services.
- Persistent storage for appointment requests and relevant activity records.
- A clear, testable agent-orchestration layer.
- A deterministic fallback for hospital questions and unavailable AI services.
- A safe preliminary symptom-guidance workflow.
- A suitable local medical-information retrieval mechanism if it provides genuine value.

Prefer familiar, reliable technologies and minimal dependencies. Make the final decision yourself and explain the main reasons briefly.

Do not introduce microservices, Kubernetes, complicated infrastructure, multiple databases, or large agent frameworks unless there is a clear, demonstrable benefit.

The application must be easy to start, troubleshoot, and explain.

## 6. Dataset and AI strategy

Investigate the most suitable openly accessible, legally usable, high-quality, prepared medical question-answer dataset for this project's actual requirements.

Consider MedQuAD and its available derivatives as candidates, but do not assume that a dataset is fully cleaned, correctly licensed, clinically validated, or suitable for direct model training merely because its name or description suggests this.

Verify the original source, current licence information, dataset structure, quality limitations, approximate download size, and practical usefulness before recommending it.

Distinguish between four different activities:

1. Training or fine-tuning a machine-learning model.
2. Retrieving answers from an existing medical question-answer dataset.
3. Using approved, predefined rules for symptom-related care navigation.
4. Using an optional external or local language model to generate responses.

Do not train a medical diagnosis model merely to claim that the project uses machine learning. The seven-day deadline makes that an unjustified risk unless you identify a concrete requirement that cannot be met more reliably another way.

My preference is to reuse an existing, relevant, prepared dataset rather than spend days cleaning raw data. If the available dataset requires extensive cleaning or validation, choose a smaller, more reliable alternative or omit it from the initial demonstration.

If MedQuAD or another medical Q&A resource is selected, use it only for an appropriate information-retrieval purpose, after checking its licence and suitability. Clearly distinguish its general educational answers from hospital-specific information and clinical advice.

The main application must remain fully demonstrable when no external AI API is configured and no large local model is available.

Do not invent a dataset's quality, evaluation results, licence, or medical reliability.

## 7. AI agents and visible orchestration

Plan a real, explainable agentic workflow rather than four decorative chatbot labels.

The planned system must include:

**Supervisory Agent**
- Identifies the user's intent.
- Selects the relevant specialist.
- Invokes the appropriate application functionality.
- Coordinates the response.
- Records the routing outcome.
- Handles unsupported or ambiguous requests safely.

**Patient Assistance Agent**
- Answers hospital service and department questions using available information.
- Provides relevant navigation assistance.
- Clearly identifies unavailable or unverified information.

**Appointment Agent**
- Collects appointment-request details.
- Validates submitted information.
- Saves requests through the backend.
- Returns the actual request identifier and status.
- Does not claim that a pending request is a confirmed booking.

**Care Navigation Agent**
- Collects relevant symptom information.
- Uses conservative, predefined care-navigation rules and appropriately reviewed information.
- Identifies emergency warning signs.
- Provides suitable professional-care guidance without diagnosing diseases.
- Escalates potentially serious symptoms without delaying the user with unnecessary questions.

The user interface should display the selected agent, the task being handled, and the resulting status. Where possible, demonstrate the relationship between a request, its specialist agent, the action taken, and its outcome.

Do not create autonomous agent loops, unnecessary agent handoffs, or complicated frameworks that add no demonstrable value.

## 8. Medical safety and privacy

Although the immediate goal is a partial implementation, all visible behavior must follow responsible healthcare principles.

Use synthetic demonstration records only.

Never fabricate medical evidence, appointments, bed availability, approvals, clinical records, or successful operations.

Do not present preliminary symptom guidance as a diagnosis. Potentially serious symptoms must trigger appropriate urgent professional-care guidance.

Do not independently prescribe, discontinue, or modify treatment.

Validate inputs and enforce appropriate access boundaries for protected operations.

Clearly identify demonstration data, simulated integrations, and limitations.

Do not claim that the prototype is clinically validated, regulator-approved, or ready for unrestricted clinical deployment.

## 9. UI/UX quality requirements

The frontend must look like a polished healthcare product rather than a generic student dashboard.

Use refined neumorphism as a visual direction, including:

- Softly raised and recessed surfaces.
- Restrained shadows and borders.
- A sophisticated, consistent colour palette.
- Strong typography and visual hierarchy.
- Smooth transitions and carefully selected animations.
- Consistent spacing and reusable components.
- Responsive desktop and mobile layouts.
- Thoughtful loading, success, pending, empty, and error states.
- Accessible text contrast, keyboard navigation, and clear interaction feedback.

Avoid excessive shadows, low-contrast text, distracting motion, and animations that interfere with form submission or navigation.

Prioritize functional correctness and accessibility over visual effects. Use animation libraries only if they are justified and compatible with the deadline.

The essential pages and components must be connected to working functionality. Do not build numerous attractive but empty screens.

## 10. Code organization and explainability

Plan a structured project with clear separation of concerns.

A possible starting structure is:

- `frontend/` — user interface, reusable components, pages, and frontend services.
- `backend/` — API routes, validation, application services, and agent coordination.
- `datasets/` — documented dataset sources, licence information, and prepared data if genuinely required.
- `model/` — model-related code or artifacts only if an actual model is selected.
- `docs/` — project explanation, architecture, setup instructions, implementation status, and phase reports.
- `scripts/` — useful repeatable setup or data preparation tasks, if needed.
- Root-level configuration, Git files, environment examples, and README.

Adapt this structure to the chosen architecture. Do not create empty directories or unnecessary abstraction layers merely to make the repository look larger.

Use descriptive file, function, class, variable, API, and database field names.

Every significant component should have a clear responsibility. Add comments where they explain important logic, safety behavior, or non-obvious design decisions.

The code must be understandable enough for me to explain the purpose of each module, the data flow, the agent routing, and the main application workflows to examiners.

## 11. Seven-day execution roadmap

Produce a concise roadmap of no more than four or five substantial implementation phases. Do not turn every inspection, formatting task, or small test into a separate phase.

The roadmap should prioritize:

**Phase 1 — Foundation and visual shell**
- Establish the repository structure.
- Initialize the frontend and backend.
- Create the core visual design system and main navigation.
- Establish application connectivity.
- Confirm that the application starts successfully.

**Phase 2 — Patient dashboard and persistent workflows**
- Complete the patient dashboard.
- Implement appointment request submission and persistent storage.
- Display request status and recent activity.
- Connect the visible forms and navigation to actual backend functionality.

**Phase 3 — Agentic assistant and care navigation**
- Implement the Supervisory Agent and three specialist agents.
- Connect real request routing to appropriate functionality.
- Implement hospital Q&A, safe symptom guidance, and appointment-agent integration.
- Show agent routing and task outcomes in the interface.
- Add an optional local information-retrieval dataset only if it is practical and beneficial.

**Phase 4 — Integration, demonstration readiness, and delivery**
- Complete the primary end-to-end user journeys.
- Fix critical failures and test important edge cases.
- Polish the UI and error states.
- Prepare reproducible setup instructions, sample data, and a demonstration sequence.
- Ensure that the application works without paid APIs.
- Produce the final implementation-status report.

You may adjust the order or combine phases if that materially improves delivery. Reserve sufficient time for integration and actual demonstration, rather than spending all seven days on feature construction.

For each phase, identify the objective, essential deliverables, dependencies, acceptance criteria, estimated effort, and what should be deferred if the deadline becomes tight.

## 12. Reports and GitHub workflow

After every major implementation phase, the execution agent must create a detailed Markdown report under `docs/phase-reports/`.

Each report must use clear, friendly language and cover:

- What was intended in the phase.
- What was actually implemented.
- How the functionality works.
- Important files created or modified and their purposes.
- Relevant data flows and agent interactions.
- Commands needed to run the application.
- Tests actually executed and their observed results.
- Known errors, limitations, and incomplete features.
- Features that are simulated versus genuinely implemented.
- Changes to the project structure or previous decisions.
- The current state of the project.
- The essential next steps.

Reports must describe actual work, not planned or assumed work. Do not claim that tests passed or features work unless they were actually executed and verified.

Keep reports detailed enough to be useful to a student and an examiner, but do not generate redundant reports for every minor code change.

Maintain logical Git commits after completed and verified phases. Push changes when the GitHub repository is connected and authentication permits it.

Never commit API keys, passwords, personal data, or local environment secrets.

If GitHub is not yet configured, identify the exact required action without allowing it to block unrelated local development.

## 13. Zero-cost delivery requirements

The essential product must work without any paid API, subscription, dataset, model download, or hosting service.

Do not make a free-tier external API the only means of demonstrating the chatbot or agentic workflow.

Do not assume that free API quotas are unlimited or permanent.

If an optional AI service is proposed, verify its current pricing and limits, keep credentials out of source control, and implement a transparent fallback.

The default demonstration should use local application logic, persistent local data, and appropriately selected information resources.

Recommend deployment only where it can be achieved within the available time and zero-cost constraint. A reliable local demonstration is preferable to an unreliable public deployment.

## 14. Efficiency and decision-making rules

Treat the seven-day deadline as a hard delivery constraint.

Do not spend several prompts repeatedly inspecting the same files or restating the same plan.

Do not produce an enormous specification when a clear decision and an actionable task list would suffice.

Do not implement speculative features simply because they appear in the long-term product vision.

Prioritize end-to-end functionality, reliable persistence, visible agent coordination, safety, visual quality, and ease of explanation.

When a test discovers a critical problem, fix it within the current implementation phase rather than creating a separate audit phase.

Do not overwrite functioning code unnecessarily. Do not introduce a dependency without a clear reason. Do not claim that any operation succeeded without evidence.

If a feature is too expensive in time or risk, select a practical alternative, document the trade-off, and preserve the essential demonstration.

## 15. Required Plan Mode deliverable

Return a concise but complete development plan containing:

1. Your assessment of the seven-day deadline and the most important risks.
2. Your recommended architecture and final technology choices.
3. Your decision on the dataset, its licence and suitability, and whether training is necessary.
4. The proposed directory structure.
5. The four or five implementation phases, with priorities and acceptance criteria.
6. The primary user journeys that must work during the examination.
7. The zero-cost strategy and fallback behavior.
8. The reporting and GitHub workflow.
9. A list of features to defer.
10. The exact next action required to begin implementation.

Identify any assumptions that remain unresolved, including the missing laptop specifications, without blocking the plan unnecessarily.

Do not begin implementation in this planning pass. Finish with a clear, executable plan ready for my approval.

The guiding objective is simple: build a small but exceptional working demonstration of Hospivanta's central idea—a Supervisory Agent coordinating specialized agents to help patients navigate hospital services—while laying a sensible foundation for future development.

You have the freedom to choose the best approach, but every decision must serve a demonstrable outcome, a safe workflow, explainable code, or a meaningful improvement in product quality.