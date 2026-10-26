import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Badge, Button, Modal, TextInput } from "../src/components/ui";

describe("Button", () => {
  it("defaults to type=button so it never submits forms by accident", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("type", "button");
  });

  it("calls onClick when activated with mouse or keyboard", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Continue</Button>);

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.tab();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Continue" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await user.keyboard(" ");

    expect(onClick).toHaveBeenCalledTimes(3);
  });

  it("is disabled and announces busy while loading", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Submitting
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Submitting" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is skipped by keyboard focus when disabled", async () => {
    const user = userEvent.setup();
    render(
      <>
        <Button disabled>Disabled</Button>
        <Button>Enabled</Button>
      </>,
    );

    await user.tab();
    expect(screen.getByRole("button", { name: "Enabled" })).toHaveFocus();
  });
});

describe("TextInput", () => {
  it("links the label and exposes errors to assistive technology", () => {
    render(<TextInput label="Patient name" error="Please enter your name." />);

    const input = screen.getByLabelText("Patient name");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Please enter your name.");
    expect(screen.getByRole("alert")).toHaveTextContent("Please enter your name.");
  });

  it("uses the hint as the description when there is no error", () => {
    render(<TextInput label="Phone" hint="10-digit mobile number" />);

    const input = screen.getByLabelText("Phone");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAccessibleDescription("10-digit mobile number");
  });
});

describe("Badge", () => {
  it("always includes a text label, not only colour", () => {
    render(<Badge tone="pending">Pending</Badge>);
    expect(screen.getByText("Pending")).toHaveClass("nh-badge", "nh-badge--pending");
  });
});

function ModalHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open dialog</Button>
      <Modal
        open={open}
        title="Confirm request"
        onClose={() => setOpen(false)}
        actions={
          <>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => setOpen(false)}>Confirm</Button>
          </>
        }
      >
        <p>Are you sure?</p>
      </Modal>
    </>
  );
}

describe("Modal", () => {
  it("moves focus inside, traps Tab, closes on Escape and restores focus", async () => {
    const user = userEvent.setup();
    render(<ModalHarness />);

    const opener = screen.getByRole("button", { name: "Open dialog" });
    await user.click(opener);

    const dialog = screen.getByRole("dialog", { name: "Confirm request" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Confirm" })).toHaveFocus();
    await user.tab(); // wraps back to the first control
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
