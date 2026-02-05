/**
 * Utility functions for dialogue bubble calculations
 */

/**
 * Estimates the height of a dialogue bubble based on text content and width
 * @param text - The dialogue text
 * @param widthRatio - The width of the bubble as a ratio (0-1)
 * @returns The estimated height as a ratio (0-1)
 */
export function estimateBubbleHeight(text: string, widthRatio: number): number {
    const normalized = text.trim();
    if (!normalized) return 0.08;

    const charsPerLine = Math.max(12, Math.floor(widthRatio * 70));
    const rawLines = normalized.split("\n");
    const lines = rawLines.reduce((count, line) => {
        const len = Math.max(1, line.length);
        return count + Math.ceil(len / charsPerLine);
    }, 0);

    const base = 0.05;
    const perLine = 0.03;
    return Math.min(0.55, Math.max(base + lines * perLine, 0.08));
}

/**
 * Maps dialogue type string to bubble type
 * @param type - The dialogue type from suggestions (DIALOGUE, SFX, THOUGHT, NARRATION)
 * @returns The bubble type (chat, sfx, thought, narration)
 */
export function mapDialogueTypeToBubbleType(type?: string): string {
    if (!type) return "chat";

    const typeMap: Record<string, string> = {
        "SFX": "sfx",
        "THOUGHT": "thought",
        "NARRATION": "narration",
        "DIALOGUE": "chat"
    };

    return typeMap[type.toUpperCase()] || "chat";
}
