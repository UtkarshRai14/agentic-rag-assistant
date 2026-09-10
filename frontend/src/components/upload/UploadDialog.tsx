import { useRef, useState } from "react";
import { Upload, X, Loader2, FileUp } from "lucide-react";
import { uploadDocuments } from "@/lib/api";

export function UploadDialog({ onIngested }: { onIngested?: (chunks: number) => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setResult(null);
    try {
      const r = await uploadDocuments(Array.from(files));
      setResult(`Indexed ${r.chunks_added} chunks from ${r.files.length} file(s).`);
      onIngested?.(r.chunks_added);
    } catch (e) {
      setResult(`Upload failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm hover:bg-surface-2"
      >
        <Upload className="h-4 w-4" />
        Upload docs
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">Add documents to the knowledge base</h3>
              <button onClick={() => !busy && setOpen(false)} className="text-muted hover:text-fg">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                handleFiles(e.dataTransfer.files);
              }}
              onClick={() => inputRef.current?.click()}
              className={
                "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors " +
                (dragging ? "border-accent bg-accent/5" : "border-border")
              }
            >
              {busy ? (
                <Loader2 className="h-7 w-7 animate-spin text-accent" />
              ) : (
                <FileUp className="h-7 w-7 text-muted" />
              )}
              <p className="text-sm text-muted">
                Drag & drop or click to choose files
                <br />
                <span className="text-xs">PDF, TXT, Markdown</span>
              </p>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.md,.markdown"
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
              />
            </div>

            {result && <p className="mt-3 text-sm text-muted">{result}</p>}
          </div>
        </div>
      )}
    </>
  );
}
