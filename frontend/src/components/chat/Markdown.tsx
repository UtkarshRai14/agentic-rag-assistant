import { memo, useEffect, useState, type ReactNode, Children } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check } from "lucide-react";

function scrollToCitation(n: number) {
  const el = document.getElementById(`source-idx-${n}`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("ring-2", "ring-accent");
  setTimeout(() => el.classList.remove("ring-2", "ring-accent"), 1400);
}

function CitationChip({ n }: { n: number }) {
  return (
    <button
      onClick={() => scrollToCitation(n)}
      className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-accent/15 px-1 align-text-top text-[11px] font-semibold text-accent hover:bg-accent/30"
      title={`Jump to source ${n}`}
    >
      {n}
    </button>
  );
}

/** Replace [1], [2] ... inside string children with clickable chips. */
function linkifyCitations(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child !== "string") return child;
    const parts: ReactNode[] = [];
    const re = /\[(\d+)\]/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(child)) !== null) {
      if (m.index > last) parts.push(child.slice(last, m.index));
      parts.push(<CitationChip key={`${m.index}-${m[1]}`} n={Number(m[1])} />);
      last = m.index + m[0].length;
    }
    if (last < child.length) parts.push(child.slice(last));
    return parts.length ? parts : child;
  });
}

function CodeBlock({ code, lang, highlight }: { code: string; lang: string; highlight: boolean }) {
  const [html, setHtml] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    if (!highlight) {
      setHtml(null);
      return;
    }
    import("shiki")
      .then(({ codeToHtml }) =>
        codeToHtml(code, {
          lang: lang || "text",
          themes: { light: "github-light", dark: "github-dark" },
          defaultColor: false,
        }),
      )
      .then((out) => active && setHtml(out))
      .catch(() => active && setHtml(null));
    return () => {
      active = false;
    };
  }, [code, lang, highlight]);

  const copy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  };

  return (
    <div className="group relative">
      <button
        onClick={copy}
        className="absolute right-2 top-2 z-10 rounded-md border border-border bg-surface/80 p-1 text-muted opacity-0 transition-opacity group-hover:opacity-100"
        title="Copy code"
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      {html ? (
        <div dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <pre>
          <code>{code}</code>
        </pre>
      )}
    </div>
  );
}

export const Markdown = memo(function Markdown({
  text,
  highlight = true,
}: {
  text: string;
  highlight?: boolean;
}) {
  return (
    <div className="prose-chat text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{linkifyCitations(children)}</p>,
          li: ({ children }) => <li>{linkifyCitations(children)}</li>,
          td: ({ children }) => <td>{linkifyCitations(children)}</td>,
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || "");
            const isBlock = "node" in props && match;
            const raw = String(children).replace(/\n$/, "");
            if (!isBlock) {
              return <code className={className}>{children}</code>;
            }
            return <CodeBlock code={raw} lang={match![1]} highlight={highlight} />;
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
});
