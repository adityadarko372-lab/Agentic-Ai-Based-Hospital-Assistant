import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HealthInfoCard } from "../src/components/assistant/AssistantCards";
import { describeAddOns, describeRouting } from "../src/config/features";
import type { HealthResponse } from "../src/services/healthService";
import { HEALTHY_RESPONSE } from "./renderWithProviders";

const CARD = {
  type: "health_info" as const,
  title: "Asthma",
  question: "What is Asthma?",
  answer: "Asthma is a chronic disease that affects your airways.",
  source: "MPlusHealthTopics",
  url: "https://medlineplus.gov/asthma.html",
  similarity: 0.82,
  license: "MedQuAD, CC BY 4.0",
  disclaimer: "General educational information. It is not medical advice.",
};

const FEATURES = HEALTHY_RESPONSE.features as HealthResponse["features"];

describe("Health information card (Phase 5, optional)", () => {
  it("shows the passage with its source, licence and disclaimer", () => {
    render(
      <MemoryRouter>
        <HealthInfoCard card={CARD} />
      </MemoryRouter>,
    );
    expect(screen.getByText("General information")).toBeInTheDocument();
    expect(screen.getByText("What is Asthma?")).toBeInTheDocument();
    expect(screen.getByText(/match 82%/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /MPlusHealthTopics page/ });
    expect(link).toHaveAttribute("href", "https://medlineplus.gov/asthma.html");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/CC BY 4.0/)).toBeInTheDocument();
    expect(screen.getByText(/not medical advice/)).toBeInTheDocument();
  });

  it("does not turn a non-https source into a link", () => {
    render(
      <MemoryRouter>
        <HealthInfoCard card={{ ...CARD, url: "javascript:alert(1)" }} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("Feature summaries on the dashboard", () => {
  it("lists only what the server reports as on", () => {
    expect(describeAddOns(FEATURES)).toBe("Off (not required)");
    expect(describeAddOns({ ...FEATURES, health_info_enabled: true, front_desk_enabled: true })).toBe(
      "Health information (index not built) · Front-desk review",
    );
  });

  it("says when the trained classifier was requested but rules are in use", () => {
    expect(describeRouting(FEATURES)).toBe("Transparent rules (default)");
    expect(describeRouting({ ...FEATURES, intent_classifier: "transformer" })).toBe(
      "Transparent rules (trained model not installed)",
    );
    expect(describeRouting({ ...FEATURES, intent_classifier: "transformer", intent_classifier_active: "transformer" })).toMatch(
      /Trained classifier/,
    );
  });
});
