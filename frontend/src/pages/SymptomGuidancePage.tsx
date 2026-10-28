import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { AgentTimeline } from "../components/assistant/AgentTimeline";
import { CareGuidance, EmergencyCard } from "../components/assistant/AssistantCards";
import { EmergencyNotice } from "../components/EmergencyNotice";
import { PageHeader } from "../components/layout/PageHeader";
import { Button, Card, DemoDataBanner, EmptyState, Icon, SelectInput, Skeleton, TextArea } from "../components/ui";
import { useApiResource } from "../hooks/useApiResource";
import { ApiError } from "../services/apiClient";
import { careApi } from "../services/novaApi";
import type { CareAssessRequest, CareAssessResponse, CareOption } from "../services/types";

interface FormErrors {
  symptom_ids?: string;
  duration?: string;
  severity?: string;
  free_text?: string;
}

function CheckboxGroup({
  legend,
  hint,
  options,
  selected,
  onToggle,
  tone,
  error,
  id,
}: {
  legend: string;
  hint?: string;
  options: CareOption[];
  selected: string[];
  onToggle: (id: string) => void;
  tone: "warning" | "normal";
  error?: string;
  id: string;
}) {
  return (
    <fieldset className={`nh-fieldset nh-fieldset--${tone}`} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}>
      <legend className="nh-field__label">{legend}</legend>
      {hint && (
        <p className="nh-field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      <div className="nh-option-grid">
        {options.map((option) => {
          const checked = selected.includes(option.id);
          return (
            <label key={option.id} className={`nh-option nh-option--${tone}${checked ? " is-checked" : ""}`}>
              <input type="checkbox" checked={checked} onChange={() => onToggle(option.id)} />
              <span>{option.label}</span>
            </label>
          );
        })}
      </div>
      {error && (
        <p className="nh-field__error" id={`${id}-error`} role="alert">
          <Icon name="alert" size={14} />
          {error}
        </p>
      )}
    </fieldset>
  );
}

function RadioGroup({
  legend,
  name,
  options,
  value,
  onChange,
  error,
  optional,
}: {
  legend: string;
  name: string;
  options: CareOption[];
  value: string;
  onChange: (value: string) => void;
  error?: string;
  optional?: boolean;
}) {
  return (
    <fieldset className="nh-fieldset" aria-describedby={error ? `${name}-error` : undefined}>
      <legend className="nh-field__label">
        {legend}
        {!optional && (
          <span className="nh-field__required" aria-hidden="true">
            *
          </span>
        )}
      </legend>
      <div className="nh-option-row">
        {options.map((option) => (
          <label key={option.id} className={`nh-option${value === option.id ? " is-checked" : ""}`}>
            <input type="radio" name={name} value={option.id} checked={value === option.id} onChange={() => onChange(option.id)} />
            <span>
              {option.label}
              {option.hint && <span className="nh-option__hint">{option.hint}</span>}
            </span>
          </label>
        ))}
      </div>
      {error && (
        <p className="nh-field__error" id={`${name}-error`} role="alert">
          <Icon name="alert" size={14} />
          {error}
        </p>
      )}
    </fieldset>
  );
}

/** Module 4: Preliminary Symptom Guidance. Never a diagnosis. */
export function SymptomGuidancePage() {
  const options = useApiResource(careApi.options);
  const [selected, setSelected] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [duration, setDuration] = useState("");
  const [severity, setSeverity] = useState("");
  const [ageGroup, setAgeGroup] = useState("adult");
  const [pregnant, setPregnant] = useState(false);
  const [longTerm, setLongTerm] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CareAssessResponse | null>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);

  const warningIds = new Set((options.data?.warning_signs ?? []).map((item) => item.id));
  const warningSelected = selected.filter((id) => warningIds.has(id));

  useEffect(() => {
    if (result) resultHeading.current?.focus();
  }, [result]);

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
    if (errors.symptom_ids) setErrors((current) => ({ ...current, symptom_ids: undefined }));
  }

  function reset() {
    setSelected([]);
    setFreeText("");
    setDuration("");
    setSeverity("");
    setAgeGroup("adult");
    setPregnant(false);
    setLongTerm(false);
    setErrors({});
    setFormError(null);
    setResult(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found: FormErrors = {};
    if (selected.length === 0 && freeText.trim().length < 3) {
      found.symptom_ids = "Please select at least one symptom or describe how you feel.";
    }
    // With a warning sign ticked, guidance is given straight away; no other answers are needed.
    if (warningSelected.length === 0) {
      if (!duration) found.duration = "Please choose how long you have had the symptoms.";
      if (!severity) found.severity = "Please choose how severe the symptoms are.";
    }
    setErrors(found);
    setFormError(null);
    if (Object.keys(found).length > 0) return;

    const body: CareAssessRequest = {
      symptom_ids: selected,
      free_text: freeText.trim(),
      duration: duration || null,
      severity: (severity || null) as CareAssessRequest["severity"],
      age_group: ageGroup as CareAssessRequest["age_group"],
      pregnant,
      long_term_condition: longTerm,
    };
    setSubmitting(true);
    try {
      setResult(await careApi.assess(body));
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors as FormErrors);
      }
      setFormError(
        `${error instanceof Error ? error.message : "Guidance could not be loaded."} If you feel very unwell, call 112 or 108 now.`,
      );
    } finally {
      setSubmitting(false);
    }
  }

  const assessment = result?.assessment;
  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Module 4 · Preliminary Symptom Guidance"
        title="Symptom Guidance"
        description="Answer a few questions to get cautious guidance on how soon, and where, to seek care. This does not diagnose any condition."
      />
      <EmergencyNotice />
      <DemoDataBanner message="Guidance comes from fixed rules written for this prototype. They have not been reviewed by clinicians and do not replace a doctor." />

      <div className="nh-symptom-layout">
        <Card as="section" title="Tell us how you feel" subtitle="Fields marked * are needed unless you tick a warning sign.">
          {options.loading && !options.data ? (
            <div className="nh-stack" role="status" aria-busy="true" aria-label="Loading the questionnaire">
              <Skeleton height={120} />
              <Skeleton height={160} />
              <Skeleton height={60} />
            </div>
          ) : options.error || !options.data ? (
            <div className="nh-status-panel">
              <p>The questionnaire could not be loaded: {options.error}</p>
              <Button variant="secondary" size="sm" onClick={() => void options.reload()}>
                Try again
              </Button>
            </div>
          ) : (
            <form className="nh-stack nh-symptom-form" onSubmit={handleSubmit} noValidate aria-label="Symptom questionnaire">
              <CheckboxGroup
                id="warning-signs"
                legend="Is any of these happening right now?"
                hint="These can be signs of an emergency."
                options={options.data.warning_signs}
                selected={selected}
                onToggle={toggle}
                tone="warning"
              />

              {warningSelected.length > 0 && (
                <div className="nh-inline-emergency" role="alert">
                  <p className="nh-inline-emergency__title">
                    <Icon name="alert" size={18} /> Get emergency help now. Don't wait for this form.
                  </p>
                  <div className="nh-emergency-card__numbers">
                    <a href="tel:112" className="nh-emergency-card__call">
                      <span className="nh-emergency-card__number">112</span>
                      <span>National emergency</span>
                    </a>
                    {warningSelected.includes("self_harm") ? (
                      <a href="tel:14416" className="nh-emergency-card__call">
                        <span className="nh-emergency-card__number">14416</span>
                        <span>Tele-MANAS (24×7)</span>
                      </a>
                    ) : (
                      <a href="tel:108" className="nh-emergency-card__call">
                        <span className="nh-emergency-card__number">108</span>
                        <span>Ambulance</span>
                      </a>
                    )}
                  </div>
                </div>
              )}

              <CheckboxGroup
                id="symptoms"
                legend="Your symptoms"
                hint="Tick everything that applies."
                options={options.data.symptoms}
                selected={selected}
                onToggle={toggle}
                tone="normal"
                error={errors.symptom_ids}
              />

              <TextArea
                id="symptom-free-text"
                label="Describe it in your own words (optional)"
                value={freeText}
                maxLength={500}
                onChange={(event) => setFreeText(event.target.value)}
                error={errors.free_text}
                hint={`For example: “pain in my left knee when walking” (${freeText.trim().length}/500).`}
              />

              <RadioGroup legend="How long have you had it?" name="duration" options={options.data.durations} value={duration} onChange={setDuration} error={errors.duration} optional={warningSelected.length > 0} />
              <RadioGroup legend="How severe is it?" name="severity" options={options.data.severities} value={severity} onChange={setSeverity} error={errors.severity} optional={warningSelected.length > 0} />

              <SelectInput label="Who is this for?" value={ageGroup} onChange={(event) => setAgeGroup(event.target.value)}>
                {options.data.age_groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.label}
                  </option>
                ))}
              </SelectInput>

              <fieldset className="nh-fieldset">
                <legend className="nh-field__label">General information (optional)</legend>
                <div className="nh-option-row">
                  <label className={`nh-option${pregnant ? " is-checked" : ""}`}>
                    <input type="checkbox" checked={pregnant} onChange={(event) => setPregnant(event.target.checked)} />
                    <span>Currently pregnant</span>
                  </label>
                  <label className={`nh-option${longTerm ? " is-checked" : ""}`}>
                    <input type="checkbox" checked={longTerm} onChange={(event) => setLongTerm(event.target.checked)} />
                    <span>Has a long-term condition (e.g. diabetes, heart or kidney disease)</span>
                  </label>
                </div>
              </fieldset>

              {formError && (
                <p className="nh-inline-alert nh-inline-alert--error" role="alert">
                  <Icon name="alert" size={16} />
                  {formError}
                </p>
              )}

              <div className="nh-form-actions">
                <Button variant="ghost" onClick={reset} disabled={submitting}>
                  Clear
                </Button>
                <Button type="submit" loading={submitting}>
                  {submitting ? "Checking…" : "Get guidance"}
                </Button>
              </div>
            </form>
          )}
        </Card>

        <Card as="section" className="nh-symptom-result" aria-live="polite" aria-labelledby="guidance-heading">
          <h2 id="guidance-heading" ref={resultHeading} tabIndex={-1} className="nh-card__title">
            Your guidance
          </h2>
          {!result || !assessment ? (
            <EmptyState
              icon="stethoscope"
              title="No guidance yet"
              description="Fill in the questionnaire and press “Get guidance”. You will see how soon to seek care, a suggested department and next steps."
            />
          ) : (
            <div className="nh-stack">
              <p className="nh-symptom-result__agent">
                <span className="nh-agent-chip nh-agent-chip--care">
                  <Icon name="stethoscope" size={14} />
                  Care Navigation Agent
                </span>
                <span className="nh-chat-card__muted">Rules v{assessment.rules_version} · not clinically reviewed</span>
              </p>
              {assessment.level === "emergency" ? (
                <>
                  <EmergencyCard
                    card={{
                      type: "emergency",
                      red_flags: assessment.red_flags.map((flag) => flag.label),
                      numbers: assessment.emergency_numbers,
                      next_steps: assessment.next_steps,
                      self_harm: assessment.red_flags.some((flag) => flag.id === "self_harm"),
                    }}
                  />
                  <p className="nh-care-card__disclaimer">
                    <Icon name="info" size={14} />
                    {assessment.disclaimer}
                  </p>
                </>
              ) : (
                <CareGuidance assessment={assessment} />
              )}
              <div className="nh-row">
                <Link to="/assistant" className="nh-button nh-button--secondary nh-button--sm">
                  Ask the assistant
                </Link>
                <Button variant="ghost" size="sm" onClick={reset}>
                  Start again
                </Button>
              </div>
              <details className="nh-symptom-result__trace">
                <summary>How the Care Navigation Agent decided</summary>
                <AgentTimeline run={result.run} />
              </details>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
