import { AssistantAvatar } from './ChatMessage';

export function TypingIndicator() {
  return (
    <div className="cb-msg cb-msg--ai" role="status">
      <AssistantAvatar />
      <div className="cb-bubble cb-typing">
        <span className="cb-dot" /><span className="cb-dot" /><span className="cb-dot" />
        <span className="cb-sr">GSFC University Assistant is thinking…</span>
      </div>
    </div>
  );
}