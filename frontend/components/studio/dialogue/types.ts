/**
 * Type definitions for the Dialogue Editor
 */

export type DialogueBubble = {
    id: string;
    panelId: number;
    bubbleType?: string;  // chat, thought, narration, sfx
    text: string;
    speaker?: string;
    position: { x: number; y: number };
    size: { w: number; h: number };
    tail?: { x: number; y: number } | null;
};

export type BubbleStyle = 'chat' | 'thought' | 'narration' | 'sfx';

export type ToolType = 'select' | 'speech' | 'tail' | 'delete';

export interface BubbleStyleConfig {
    className: string;
    textColorClass: string;
    description: string;
}

export const BUBBLE_STYLES: Record<BubbleStyle, BubbleStyleConfig> = {
    chat: {
        className: 'bg-white/40 border-slate-200 rounded-xl',
        textColorClass: 'text-slate-900',
        description: 'Regular speech bubble'
    },
    thought: {
        className: 'bg-blue-50/40 border-gray-500 rounded-full',
        textColorClass: 'text-gray-500',
        description: 'Thought bubble (circular)'
    },
    narration: {
        className: 'bg-slate-900/60 border-slate-700 rounded-md',
        textColorClass: 'text-white',
        description: 'Narration box (rectangular)'
    },
    sfx: {
        className: 'bg-transparent border-transparent',
        textColorClass: 'text-black font-bold drop-shadow-[0_1px_1px_rgba(255,255,255,0.8)]',
        description: 'Sound effect (text only)'
    }
};
