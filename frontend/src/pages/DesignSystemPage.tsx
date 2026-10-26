import { useState } from "react";

import { PageHeader } from "../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Icon,
  Modal,
  SelectInput,
  Skeleton,
  TextArea,
  TextInput,
  useToast,
} from "../components/ui";

/**
 * Living reference of the Nova Health UI components and their states.
 * Useful for reviewing visual quality and accessibility in one place.
 */
export function DesignSystemPage() {
  const { showToast } = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  function simulateLoading() {
    setLoading(true);
    window.setTimeout(() => setLoading(false), 1500);
  }

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Design system"
        title="Components and states"
        description="The reusable building blocks of the Nova Health interface."
      />

      <Card as="section" title="Buttons" subtitle="Primary, secondary, ghost, danger, loading and disabled.">
        <div className="nh-row">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button loading={loading} onClick={simulateLoading}>
            {loading ? "Saving…" : "Click to load"}
          </Button>
          <Button disabled>Disabled</Button>
          <Button variant="secondary" iconOnly aria-label="Refresh">
            <Icon name="refresh" />
          </Button>
        </div>
      </Card>

      <Card as="section" title="Status badges" subtitle="Text labels always accompany colour.">
        <div className="nh-row">
          <Badge tone="pending">Pending</Badge>
          <Badge tone="confirmed">Confirmed</Badge>
          <Badge tone="emergency">Emergency</Badge>
          <Badge tone="info">Info</Badge>
          <Badge tone="neutral">Neutral</Badge>
        </div>
      </Card>

      <Card as="section" title="Form fields" subtitle="Labels, hints and accessible error messages.">
        <form className="nh-form-grid" onSubmit={(event) => event.preventDefault()} noValidate>
          <TextInput label="Patient name" placeholder="e.g. Asha Verma" hint="As on your hospital card." required />
          <SelectInput label="Department" defaultValue="">
            <option value="" disabled>
              Select a department
            </option>
            <option>General Medicine</option>
            <option>Cardiology</option>
          </SelectInput>
          <TextInput label="Preferred date" type="date" error="Please choose a date in the future." />
          <TextArea label="Reason for appointment" placeholder="Briefly describe the reason." />
        </form>
      </Card>

      <div className="nh-dashboard-columns">
        <Card as="section" title="Loading skeleton">
          <div className="nh-stack" aria-busy="true" aria-label="Loading example">
            <Skeleton height={20} width="50%" />
            <Skeleton />
            <Skeleton width="85%" />
          </div>
        </Card>
        <Card as="section" title="Empty state">
          <EmptyState icon="calendar" title="No requests yet" description="Submitted requests will appear here." />
        </Card>
      </div>

      <Card as="section" title="Feedback" subtitle="Toasts and a confirmation dialog.">
        <div className="nh-row">
          <Button
            variant="secondary"
            onClick={() =>
              showToast({ tone: "success", title: "Saved", message: "This is a success notification." })
            }
          >
            Success toast
          </Button>
          <Button
            variant="secondary"
            onClick={() => showToast({ tone: "error", title: "Something went wrong", message: "Please try again." })}
          >
            Error toast
          </Button>
          <Button onClick={() => setModalOpen(true)}>Open dialog</Button>
        </div>
      </Card>

      <Modal
        open={modalOpen}
        title="Confirm this action?"
        onClose={() => setModalOpen(false)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setModalOpen(false)}>Confirm</Button>
          </>
        }
      >
        <p>Dialogs trap keyboard focus, close with Escape and return focus to the button that opened them.</p>
      </Modal>
    </div>
  );
}
