import { X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { chatbotConfig } from '../../config/chatbotConfig';

interface Props { onAsk: (question: string) => void; onDismiss: () => void }

/** Friendly prompt above the launcher. Each button opens the chat and sends that question. */
export function ChatbotTeaser({ onAsk, onDismiss }: Props) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setVisible(true), chatbotConfig.teaser.showAfterMs);
    return () => window.clearTimeout(t);
  }, []);
  if (!visible) return null;

  return (
    <aside className="cb-teaser" aria-label="University assistant tip">
      <button type="button" className="cb-teaser__close" onClick={onDismiss} aria-label="Dismiss" title="Dismiss">
        <X size={14} aria-hidden="true" />
      </button>
      <p>{chatbotConfig.teaser.message}</p>
      <div className="cb-teaser__actions">
        {chatbotConfig.teaser.questions.map((q) => (
          <button key={q} type="button" className="cb-teaser__btn" onClick={() => onAsk(q)}>{q}</button>
        ))}
      </div>
    </aside>
  );
}