import type { ToastTone } from "../types/tracker";

type ToastProps = {
  message: string;
  tone: ToastTone;
};

export function Toast({ message, tone }: ToastProps) {
  if (!message) {
    return null;
  }

  const toneClass =
    tone === "success"
      ? "feedback-success"
      : tone === "error"
        ? "feedback-error"
        : "feedback-info";

  return (
    <section className="toast-stack" aria-live="polite">
      <p className={`toast ${toneClass}`}>{message}</p>
    </section>
  );
}
