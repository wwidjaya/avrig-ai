import React from "react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (index: number) => void;
  className?: string;
}

/**
 * Parses inline formatting:
 * - Code: `code`
 * - Bold: **text**
 * - Italic: *text* or _text_
 * - Citations: [1], [2], etc.
 */
function renderInline(text: string, onCitationClick?: (index: number) => void): React.ReactNode[] {
  // Regex pattern matching:
  // 1. Inline code: `([^`]+)`
  // 2. Bold: \*\*([^*]+)\*\*
  // 3. Italic: \*([^*]+)\* or _([^_]+)_
  // 4. Citation: \[(\d+)\]
  const inlineRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_|\[\d+\])/g;

  const parts = text.split(inlineRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // Inline code
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code
          key={index}
          className="font-mono bg-muted/70 px-1 py-0.5 rounded text-xs border border-border/50 text-foreground"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={index} className="font-semibold text-foreground">
          {renderInline(part.slice(2, -2), onCitationClick)}
        </strong>
      );
    }

    // Italic with *
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      return (
        <em key={index} className="italic text-foreground">
          {renderInline(part.slice(1, -1), onCitationClick)}
        </em>
      );
    }

    // Italic with _
    if (part.startsWith("_") && part.endsWith("_") && part.length >= 2) {
      return (
        <em key={index} className="italic text-foreground">
          {renderInline(part.slice(1, -1), onCitationClick)}
        </em>
      );
    }

    // Citation [n]
    const citationMatch = part.match(/^\[(\d+)\]$/);
    if (citationMatch) {
      const citationNum = parseInt(citationMatch[1], 10);
      return (
        <span
          key={index}
          onClick={() => onCitationClick?.(citationNum)}
          className="font-mono text-primary font-semibold hover:underline cursor-pointer select-none inline-block px-0.5"
          title={`Citation [${citationNum}]`}
        >
          [{citationNum}]
        </span>
      );
    }

    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

/**
 * Lightweight, safe Markdown renderer component:
 * Parses:
 * - Code blocks (```language ... ```)
 * - Bullet lists (* or -)
 * - Numbered lists (1. , 2. )
 * - Paragraphs and line breaks
 * - Inline formatting (bold, italic, inline code, citations)
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  onCitationClick,
  className = "",
}) => {
  if (!content) return null;

  // Split content by code blocks first
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const sections: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  const processTextBlocks = (textChunk: string, keyPrefix: string): React.ReactNode[] => {
    const lines = textChunk.split(/\r?\n/);
    const elements: React.ReactNode[] = [];

    let currentList: { type: "ul" | "ol"; items: string[] } | null = null;
    let paragraphLines: string[] = [];

    const flushParagraph = () => {
      if (paragraphLines.length > 0) {
        const pText = paragraphLines.join("\n").trim();
        if (pText) {
          elements.push(
            <p key={`${keyPrefix}-p-${elements.length}`} className="my-1.5 leading-relaxed">
              {pText.split("\n").map((line, lineIdx) => (
                <React.Fragment key={lineIdx}>
                  {lineIdx > 0 && <br />}
                  {renderInline(line, onCitationClick)}
                </React.Fragment>
              ))}
            </p>
          );
        }
        paragraphLines = [];
      }
    };

    const flushList = () => {
      if (currentList) {
        if (currentList.type === "ul") {
          elements.push(
            <ul
              key={`${keyPrefix}-ul-${elements.length}`}
              className="list-disc pl-5 space-y-1 my-2"
            >
              {currentList.items.map((item, idx) => (
                <li key={idx} className="leading-relaxed">
                  {renderInline(item, onCitationClick)}
                </li>
              ))}
            </ul>
          );
        } else {
          elements.push(
            <ol
              key={`${keyPrefix}-ol-${elements.length}`}
              className="list-decimal pl-5 space-y-1 my-2"
            >
              {currentList.items.map((item, idx) => (
                <li key={idx} className="leading-relaxed">
                  {renderInline(item, onCitationClick)}
                </li>
              ))}
            </ol>
          );
        }
        currentList = null;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Empty line -> flush lists and paragraphs
      if (!trimmed) {
        flushParagraph();
        flushList();
        continue;
      }

      // Check unordered bullet: * item or - item
      const bulletMatch = line.match(/^(\s*)[*-]\s+(.+)$/);
      if (bulletMatch) {
        flushParagraph();
        if (!currentList || currentList.type !== "ul") {
          flushList();
          currentList = { type: "ul", items: [] };
        }
        currentList.items.push(bulletMatch[2]);
        continue;
      }

      // Check ordered list: 1. item
      const numberedMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
      if (numberedMatch) {
        flushParagraph();
        if (!currentList || currentList.type !== "ol") {
          flushList();
          currentList = { type: "ol", items: [] };
        }
        currentList.items.push(numberedMatch[2]);
        continue;
      }

      // Regular text line
      flushList();
      paragraphLines.push(line);
    }

    flushParagraph();
    flushList();

    return elements;
  };

  let sectionCount = 0;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const textBefore = content.substring(lastIndex, match.index);
    if (textBefore) {
      sections.push(...processTextBlocks(textBefore, `sec-${sectionCount++}`));
    }

    const language = match[1] || "";
    const code = match[2];

    sections.push(
      <div
        key={`code-${sectionCount++}`}
        className="my-3 rounded-lg border border-border/80 bg-zinc-950 dark:bg-zinc-900/90 p-3 overflow-x-auto text-xs font-mono text-zinc-100 shadow-xs"
      >
        {language && (
          <div className="text-[10px] uppercase font-semibold text-zinc-400 mb-1 tracking-wider">
            {language}
          </div>
        )}
        <pre className="overflow-x-auto font-mono">
          <code>{code}</code>
        </pre>
      </div>
    );

    lastIndex = match.index + match[0].length;
  }

  const remainingText = content.substring(lastIndex);
  if (remainingText) {
    sections.push(...processTextBlocks(remainingText, `sec-${sectionCount++}`));
  }

  return <div className={`text-sm leading-relaxed ${className}`}>{sections}</div>;
};