import { ArrowUp } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { chatbotConfig } from '../../config/chatbotConfig';

interface Props { onSend: (text: string) => void; disabled?: boolean }

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  const max = chatbotConfig.maxMessageLength;

  // Focus on desktop only; on phones this would pop the keyboard open immediately.
  useEffect(() => {
    if (window.matchMedia('(min-width: 641px)').matches) ref.current?.focus();
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    const needed = el.scrollHeight + 2; // + border (box-sizing: border-box)
    el.style.height = `${Math.min(needed, 120)}px`;
    el.style.overflowY = needed > 120 ? 'auto' : 'hidden';
  }, [value]);

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue('');
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); }
  };

  return (
    <div className="cb-input">
      <label htmlFor="ncct-cb-input" className="cb-sr">Message the GSFC University Assistant</label>
      <textarea
        id="ncct-cb-input" ref={ref} rows={1} value={value} maxLength={max}
        onChange={(e) => setValue(e.target.value)} onKeyDown={onKeyDown}
        placeholder="Ask about admissions, programs, exams, hostels or events..."
      />
      <button type="button" className="cb-send" onClick={submit} disabled={disabled || !value.trim()} aria-label="Send message" title="Send (Enter)">
        <ArrowUp size={18} aria-hidden="true" />
      </button>
      {value.length > max * 0.8 && <span className="cb-count" aria-live="polite">{value.length}/{max}</span>}
    </div>
  );
}