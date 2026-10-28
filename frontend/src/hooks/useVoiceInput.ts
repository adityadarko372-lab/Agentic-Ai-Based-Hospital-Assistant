import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Optional voice input (Phase 5) with the browser's Web Speech API.
 *
 * - Shown only where the browser supports it (Chrome / Edge); nothing to install.
 * - Language en-IN (Indian English).
 * - Speech is turned into text in the message box; the patient reviews it and
 *   presses Send. Nothing is sent automatically.
 * - Privacy: in Chrome and Edge the browser's speech service may send the audio
 *   to the browser vendor's servers. The UI says so before the first use.
 */

interface SpeechRecognitionResultLike {
  0: { transcript: string };
  isFinal: boolean;
}
interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

export function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Microphone access was blocked. Allow it in the browser's site settings, or type instead.",
  "service-not-allowed": "The browser's speech service is not available here. Please type instead.",
  "no-speech": "No speech was heard. Try again a little closer to the microphone.",
  "audio-capture": "No microphone was found.",
  network: "Voice input needs the browser's online speech service, which could not be reached.",
};

export function useVoiceInput(onText: (text: string) => void) {
  const Recognition = getSpeechRecognition();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  useEffect(() => () => recognitionRef.current?.abort(), []);

  const start = useCallback(() => {
    if (!Recognition || recognitionRef.current) return;
    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) text += event.results[i][0].transcript;
      }
      if (text.trim()) onTextRef.current(text.trim());
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") setError(ERROR_MESSAGES[event.error] ?? "Voice input stopped. Please type instead.");
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setListening(false);
    };
    recognitionRef.current = recognition;
    setError(null);
    setListening(true);
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setListening(false);
      setError("Voice input could not start. Please type instead.");
    }
  }, [Recognition]);

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  return { supported: Recognition !== null, listening, error, start, stop };
}
