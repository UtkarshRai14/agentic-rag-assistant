import { useRef, useState } from "react";
import { Upload, X, Loader2, FileUp, FileText, Trash2 } from "lucide-react";
import { deleteDocument, uploadDocuments, type DocumentInfo } from "@/lib/api";

export function UploadDialog({
  documents,
  onChanged,
}: {
  documents: DocumentInfo[];
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setResult(null);
    try {
      const r = await uploadDocuments(Array.from(files));
      setResult(
        r.chunks_added === 0
          ? "Nothing new to index: these files are already in your library."
          : `Indexed ${r.chunks_added} chunks from ${r.files.length} file(s).`,
      );
      onChanged();
    } catch (e) {
      setResult(e instanceof Error ? e.message : `Upload failed: ${String(e)}`);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = ""; // allow choosing the same file again
    }
  };

  const handleDelete = async (doc: DocumentInfo) => {
    if (!window.confirm(`Remove "${doc.name}" from your library?`)) return;
    setDeleting(doc.id);
    setResult(null);
    try {
      await deleteDocument(doc.id);
      onChanged();
    } catch (e) {
      setResult(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(null);
    }
  };

  const close = () => !busy && setOpen(false);

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
          onClick={close}
        >
          <div
            className="flex max-h-[90vh] w-full max-w-md flex-col rounded-xl border border-border bg-surface p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-1 flex items-center justify-between">
              <h3 className="font-semibold">Your documents</h3>
              <button onClick={close} className="text-muted hover:text-fg" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mb-3 text-xs text-muted">
              Only you can see these. The assistant searches them when it answers your questions.
            </p>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (!busy) handleFiles(e.dataTransfer.files);
              }}
              onClick={() => !busy && inputRef.current?.click()}
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

            <div className="mt-4 min-h-0 overflow-y-auto">
              {documents.length === 0 ? (
                <p className="text-xs text-muted">You have not uploaded any documents yet.</p>
              ) : (
                <ul className="flex flex-col gap-1.5">
                  {documents.map((doc) => (
                    <li
                      key={doc.id}
                      className="flex items-center gap-2 rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted" />
                      <span className="min-w-0 flex-1 truncate" title={doc.name}>
                        {doc.name}
                      </span>
                      <span className="shrink-0 text-xs text-muted">{doc.chunks} chunks</span>
                      <button
                        onClick={() => handleDelete(doc)}
                        disabled={deleting !== null}
                        className="shrink-0 text-muted hover:text-danger disabled:opacity-40"
                        title="Remove from your library"
                        aria-label={`Remove ${doc.name}`}
                      >
                        {deleting === doc.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
