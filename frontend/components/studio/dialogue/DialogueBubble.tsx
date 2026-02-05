/**
 * DialogueBubble Component
 * Renders a single dialogue bubble on the canvas with drag/resize/tail functionality
 */

import { type DialogueBubble, type ToolType, BUBBLE_STYLES } from './types';

interface DialogueBubbleProps {
    bubble: DialogueBubble;
    activeTool: ToolType;
    onSelect: (bubbleId: string) => void;
    onDelete: (bubbleId: string) => void;
    onDragStart: (bubbleId: string, offsetX: number, offsetY: number) => void;
    onResizeStart: (bubbleId: string) => void;
    onTailDragStart: (bubbleId: string) => void;
    canvasRef: React.RefObject<HTMLDivElement | null>;
}

export function DialogueBubbleComponent({
    bubble,
    activeTool,
    onSelect,
    onDelete,
    onDragStart,
    onResizeStart,
    onTailDragStart,
    canvasRef
}: DialogueBubbleProps) {
    const bubbleType = (bubble.bubbleType || 'chat') as keyof typeof BUBBLE_STYLES;
    const styleConfig = BUBBLE_STYLES[bubbleType] || BUBBLE_STYLES.chat;

    const handleClick = () => {
        if (activeTool === 'delete') {
            onDelete(bubble.id);
            return;
        }
        onSelect(bubble.id);
    };

    const handlePointerDown = (event: React.PointerEvent) => {
        if (activeTool !== 'select') return;
        if (!canvasRef.current) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const bubbleX = bubble.position.x * rect.width;
        const bubbleY = bubble.position.y * rect.height;
        const offsetX = event.clientX - rect.left - bubbleX;
        const offsetY = event.clientY - rect.top - bubbleY;

        onDragStart(bubble.id, offsetX, offsetY);
    };

    return (
        <div key={bubble.id}>
            <button
                type="button"
                className={`absolute text-[11px] shadow-soft px-2 py-0.5 border hover:border-indigo-300 ${styleConfig.className} ${styleConfig.textColorClass}`}
                style={{
                    left: `${bubble.position.x * 100}%`,
                    top: `${bubble.position.y * 100}%`,
                    width: `${bubble.size.w * 100}%`,
                    height: `${bubble.size.h * 100}%`,
                    minWidth: '80px',
                    transform: 'translate(-50%, -50%)'
                }}
                onClick={handleClick}
                onPointerDown={handlePointerDown}
                data-bubble="true"
            >
                <span className="block whitespace-pre-wrap break-words leading-snug">
                    {bubble.text}
                </span>
            </button>

            {/* Resize handle */}
            {activeTool === 'select' && (
                <button
                    type="button"
                    className="absolute h-3 w-3 rounded-full border border-indigo-300 bg-white shadow"
                    style={{
                        left: `${(bubble.position.x + bubble.size.w / 2) * 100}%`,
                        top: `${(bubble.position.y + bubble.size.h / 2) * 100}%`,
                        transform: 'translate(-50%, -50%)'
                    }}
                    onPointerDown={(event) => {
                        event.stopPropagation();
                        onResizeStart(bubble.id);
                    }}
                    data-bubble="true"
                />
            )}

            {/* Tail handle */}
            {activeTool === 'tail' && (
                <button
                    type="button"
                    className="absolute h-3 w-3 rounded-full border border-indigo-300 bg-indigo-100 shadow"
                    style={{
                        left: `${(bubble.tail?.x ?? bubble.position.x) * 100}%`,
                        top: `${(bubble.tail?.y ?? bubble.position.y + bubble.size.h / 2) * 100}%`,
                        transform: 'translate(-50%, -50%)'
                    }}
                    onPointerDown={(event) => {
                        event.stopPropagation();
                        onSelect(bubble.id);
                        onTailDragStart(bubble.id);
                    }}
                    data-bubble="true"
                />
            )}
        </div>
    );
}
