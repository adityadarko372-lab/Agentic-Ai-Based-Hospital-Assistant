import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { AgentTimeline } from "../components/assistant/AgentTimeline";
import { AssistantCardView } from "../components/assistant/AssistantCards";
import { PageHeader } from "../components/layout/PageHeader";
import { Button, Card, DemoDataBanner, EmptyState, Icon } from "../components/ui";
import { agentPresentation } from "../config/agents";
import { useAssistantChat, type ChatMessage } from "../hooks/useAssistantChat";
import type { Suggestion } from "../services/types";

// The four example questions from partial implementation.md, plus two demo journeys.
const STARTERS: Suggestion[] = [
  { label: "Which department should I visit?", message: "Which department should I visit for a consultation?" },
  { label: "What should I bring?", message: "What should I bring to my appointment?" },
  { label: "How do I book an appointment?", message: "How do I book an appointment?" },
  { label: "Where are hospital services?", message: "Where can I find hospital services?" },
  { label: "I want to book an appointment", message: "I want to book an appointment" },
  { label: "I have a mild cough for 3 days", message: "I have had a mild cough for 3 days" },
];

function SuggestionChips({ suggestions, onSend, disabled }: { suggestions: Suggestion[]; onSend: (text: string) => void; disabled: boolean }) {
  if (suggestions.length === 0) return null;
  return (
    <div className="nh-chips" role="group" aria-label="Suggested replies">
      {suggestions.map((suggestion) =>
        suggestion.href ? (
          <Link key={suggestion.label} to={suggestion.href} className="nh-chip nh-chip--link">
            {suggestion.label}
            <Icon name="chevronRight" size={14} />
          </Link>
        ) : (
          <button
            key={suggestion.label}
            type="button"
            className="nh-chip"
            disabled={disabled}
            onClick={() => suggestion.message && onSend(suggestion.message)}
          >
            {suggestion.label}
          </button>
        ),
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="nh-message nh-message--user">
        <p className="nh-visually-hidden">You said:</p>
        <div className="nh-bubble nh-bubble--user">{message.text}</div>
      </div>
    );
  }
  const reply = message.reply;
  const agent = agentPresentation(reply?.agent ?? "Supervisory Agent");
  return (
    <div className="nh-message nh-message--assistant">
      <span className={`nh-agent-chip nh-agent-chip--${message.failed ? "safety" : agent.tone}`}>
        <Icon name={message.failed ? "alert" : agent.icon} size={14} />
        {message.failed ? "Not delivered" : reply?.agent}
      </span>
      <div className={`nh-bubble nh-bubble--assistant${message.failed ? " nh-bubble--failed" : ""}`}>
        <p>{message.text}</p>
        {reply?.cards.map((card, index) => <AssistantCardView key={index} card={card} />)}
        {reply && reply.sources.length > 0 && (
          <p className="nh-bubble__source">
            <Icon name="info" size={13} /> Source: {reply.sources.join("; ")}
          </p>
        )}
      </div>
    </div>
  );
}

/** Module 2 (AI Hospital Assistant) with the Module 3 agent activity panel. */
export function AssistantPage() {
  const { user } = useAuth();
  const { messages, sending, send, reset, lastReply } = useAssistantChat(user?.id ?? 0);
  const [draft, setDraft] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages.length, sending]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!draft.trim() || sending) return;
    void send(draft);
    setDraft("");
    inputRef.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter adds a new line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  const suggestions = messages.length === 0 ? STARTERS : (lastAssistant?.reply?.suggestions ?? []);

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Module 2 · AI Hospital Assistant"
        title="AI Assistant"
        description="Ask in your own words. The Supervisory Agent checks safety, works out what you need and hands it to the right specialist agent."
        actions={
          messages.length > 0 ? (
            <Button variant="secondary" size="sm" leadingIcon={<Icon name="refresh" size={14} />} onClick={reset} disabled={sending}>
              New conversation
            </Button>
          ) : undefined
        }
      />
      <DemoDataBanner message="Answers use fictional hospital data and fixed rules. The assistant does not diagnose. For an emergency, call 112 or 108." />

      <div className="nh-assistant-layout">
        <Card as="section" className="nh-chat" aria-label="Conversation">
          <div ref={logRef} className="nh-chat__log" role="log" aria-live="polite" aria-relevant="additions" aria-label="Messages">
            {messages.length === 0 ? (
              <EmptyState
                icon="sparkle"
                title="How can Nova Health help today?"
                description="Ask about departments and services, request an appointment, or describe how you are feeling for preliminary guidance."
              />
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}
            {sending && (
              <div className="nh-message nh-message--assistant" role="status">
                <div className="nh-bubble nh-bubble--assistant nh-typing">
                  <span className="nh-visually-hidden">The assistant is working on your message</span>
                  <span aria-hidden="true" />
                  <span aria-hidden="true" />
                  <span aria-hidden="true" />
                </div>
              </div>
            )}
          </div>

          <SuggestionChips suggestions={suggestions} onSend={(text) => void send(text)} disabled={sending} />

          <form className="nh-composer" onSubmit={submit}>
            <label htmlFor="nh-chat-input" className="nh-visually-hidden">
              Message the assistant
            </label>
            <textarea
              id="nh-chat-input"
              ref={inputRef}
              className="nh-composer__input"
              rows={1}
              maxLength={1000}
              placeholder="Type your message… (Enter to send)"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button type="submit" iconOnly aria-label="Send message" disabled={!draft.trim()} loading={sending}>
              {!sending && <Icon name="chevronRight" />}
            </Button>
          </form>
        </Card>

        <Card
          as="section"
          className="nh-activity-panel"
          title="Agent activity"
          subtitle="What happened behind your last message."
          actions={
            <Link to="/activity" className="nh-button nh-button--secondary nh-button--sm">
              Full history
            </Link>
          }
        >
          {lastReply ? (
            <AgentTimeline run={lastReply.run} />
          ) : (
            <EmptyState
              icon="activity"
              title="No activity yet"
              description="After you send a message, each step appears here: the safety check, the detected intent and its confidence, the agent chosen and the result."
            />
          )}
        </Card>
      </div>
    </div>
  );
}
