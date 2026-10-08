import { GraduationCap } from 'lucide-react';
import { useEffect, useRef } from 'react';

export function ChatbotButton({ onClick, restoreFocus }: { onClick: () => void; restoreFocus?: boolean }) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (restoreFocus) ref.current?.focus(); }, [restoreFocus]);
  return (
    <button ref={ref} type="button" className="cb-launcher" onClick={onClick} aria-label="Ask GSFC University Assistant" title="Ask GSFC University Assistant">
      <GraduationCap size={20} aria-hidden="true" />
      <span className="cb-launcher__text">Ask GSFCU AI</span>
    </button>
  );
}