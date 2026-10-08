import type { RecommendationBlock } from '../types/chatbot';
import type { UserProfile } from '../types/user';

export const createId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const formatTime = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(iso));

/** Only allow http(s) links from backend content. */
export const safeUrl = (url?: string) => (url && /^https?:\/\//i.test(url) ? url : undefined);

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const getFirstName = (profile: UserProfile | null) => profile?.name?.trim().split(/\s+/)[0] ?? '';

export function buildGreeting(profile: UserProfile | null) {
  const name = getFirstName(profile);
  return `Hi${name ? ` ${name}` : ' there'}! 👋\n\nI'm the GSFC University Assistant.\n\nI can help you with programs and schools, admissions, exams, hostels, facilities, events, clubs, placements and contact details.\n\nWhat would you like to know?`;
}

/** Same for every user: shown before the conversation starts. */
export const INITIAL_SUGGESTIONS = [
  'Which programs does the School of ICT offer?',
  'How do I apply for admission?',
  'Tell me about the IEEE Student Branch',
  'What hostel facilities are available?',
  'Who is the Dean of ICT?',
];

type Topic = 'admission' | 'programs' | 'exams' | 'facilities' | 'events' | 'contact' | 'general';

const FOLLOW_UPS: Record<Topic, string[]> = {
  admission: ['What documents are needed for admission?', 'What is the fee structure?', 'Are scholarships available?', 'How can I contact the admission office?'],
  programs: ['How do I apply for admission?', 'What is the fee structure?', 'Tell me about placements', 'Are internships available?'],
  exams: ['How are exams evaluated?', 'How can I contact the exam cell?', 'Where can I find the exam time table?', 'Where is the academic calendar?'],
  facilities: ['What hostel facilities are available?', 'What are the library timings?', 'Is transport available?', 'What sports facilities are there?'],
  events: ['Which clubs can I join?', 'Tell me about the IEEE Student Branch', 'What sports facilities are there?', 'What events are coming up?'],
  contact: ['How can I contact the admission office?', 'Who is the Registrar?', 'How can I contact the exam cell?', 'Who is the Dean of ICT?'],
  general: ['Which programs does GSFC University offer?', 'How do I apply for admission?', 'What hostel facilities are available?'],
};

// The university backend sends plain text only; any structured block just gets generic follow-ups.
const BLOCK_TOPIC: Record<RecommendationBlock['type'], Topic> = {
  career_recommendation: 'general', course_recommendation: 'general', skill_gap: 'general', learning_path: 'general', job_role: 'general',
};

function detectTopic(userText: string, blocks?: RecommendationBlock[]): Topic {
  if (blocks?.length) return BLOCK_TOPIC[blocks[0].type];
  const t = userText.toLowerCase();
  if (/who are you|what can you do|what is gsfc/.test(t)) return 'general';
  if (/contact|e-?mail|phone|\bdean\b|\bhod\b|\bhead\b|registrar|director|provost|president|\boffice\b/.test(t)) return 'contact';
  if (/exam|evaluation|result|time ?table|calendar|semester|\bmse\b|\bese\b/.test(t)) return 'exams';
  if (/hostel|library|transport|\bbus\b|canteen|food|medical|sport|\bgym\b|\blabs?\b|wi-?fi|campus|facilit/.test(t)) return 'facilities';
  if (/admission|apply|eligib|document|scholarship|\bfees?\b|refund/.test(t)) return 'admission';
  if (/event|club|chapter|ieee|\bncc\b|fest|activit|startup|expo/.test(t)) return 'events';
  if (/program|course|b\.?tech|\bbca\b|\bmba\b|\bbba\b|m\.?sc|b\.?sc|ph\.?d|school|department|branch|placement|internship/.test(t)) return 'programs';
  return 'general';
}

/**
 * Fallback follow-ups when the backend sends no `suggestions`. Static prompts picked by topic only;
 * the AI-driven version should come from the backend (ChatReply.suggestions).
 */
export function buildFollowUps(lastUserText: string, blocks?: RecommendationBlock[]): string[] {
  const asked = lastUserText.trim().toLowerCase();
  return FOLLOW_UPS[detectTopic(lastUserText, blocks)].filter((s) => s.toLowerCase() !== asked).slice(0, 4);
}

// Teaser dismissal is a harmless UI flag, kept per browser tab session only.
const TEASER_KEY = 'ncct-career-ai-teaser-dismissed';
export const isTeaserDismissed = () => {
  try { return sessionStorage.getItem(TEASER_KEY) === '1'; } catch { return false; }
};
export const rememberTeaserDismissed = () => {
  try { sessionStorage.setItem(TEASER_KEY, '1'); } catch { /* storage unavailable: ignore */ }
};