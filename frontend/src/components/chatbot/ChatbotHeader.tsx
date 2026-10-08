import { GraduationCap, Maximize2, Minimize2, Minus, Moon, RotateCcw, Sun, X } from 'lucide-react';
import type { ReactNode } from 'react';
import { chatbotConfig } from '../../config/chatbotConfig';
import type { Theme } from '../../hooks/useTheme';

interface Props {
  theme: Theme;
  expanded: boolean;
  onToggleTheme: () => void;
  onToggleExpand: () => void;
  onNewChat: () => void;
  onMinimize: () => void;
  onClose: () => void;
}

function Btn({ label, onClick, className = '', children }: { label: string; onClick: () => void; className?: string; children: ReactNode }) {
  return <button type="button" className={`cb-icon-btn ${className}`} onClick={onClick} aria-label={label} title={label}>{children}</button>;
}

export function ChatbotHeader({ theme, expanded, onToggleTheme, onToggleExpand, onNewChat, onMinimize, onClose }: Props) {
  return (
    <header className="cb-header">
      <span className="cb-avatar cb-avatar--lg" aria-hidden="true"><GraduationCap size={20} /></span>
      <div className="cb-header__text">
        <h2>{chatbotConfig.assistantName}</h2>
        <p>Student Information Assistant</p>
      </div>
      <div className="cb-header__actions">
        <Btn label="Start new conversation" onClick={onNewChat}><RotateCcw size={16} /></Btn>
        <Btn label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} onClick={onToggleTheme}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </Btn>
        <Btn label={expanded ? 'Restore default size' : 'Expand chat'} onClick={onToggleExpand} className="cb-hide-mobile">
          {expanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </Btn>
        <Btn label="Minimize chat (keeps conversation)" onClick={onMinimize}><Minus size={16} /></Btn>
        <Btn label="Close chat" onClick={onClose}><X size={16} /></Btn>
      </div>
    </header>
  );
}