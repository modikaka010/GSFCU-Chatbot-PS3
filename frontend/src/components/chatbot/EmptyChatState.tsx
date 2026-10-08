import { GraduationCap } from 'lucide-react';
import type { UserProfile } from '../../types/user';
import { buildGreeting, INITIAL_SUGGESTIONS } from '../../utils/chatbotUtils';
import { AssistantAvatar } from './ChatMessage';
import { QuickSuggestions } from './QuickSuggestions';
import { RichText } from './RichText';

/** Greeting uses the profile already stored by NCCT; it never asks for skills. */
export function EmptyChatState({ profile, onSelect }: { profile: UserProfile | null; onSelect: (text: string) => void }) {
  return (
    <div className="cb-empty">
      <span className="cb-empty__icon" aria-hidden="true"><GraduationCap size={26} /></span>
      <h3>Welcome to GSFC University</h3>
      <p>Ask about programs, admissions, exams, hostels, events and more.</p>
      <div className="cb-msg cb-msg--ai cb-empty__greeting">
        <AssistantAvatar />
        <div className="cb-bubble"><RichText text={buildGreeting(profile)} /></div>
      </div>
      <QuickSuggestions suggestions={INITIAL_SUGGESTIONS} onSelect={onSelect} />
    </div>
  );
}