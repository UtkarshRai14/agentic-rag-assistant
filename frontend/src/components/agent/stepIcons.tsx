import { Globe, FileSearch, Wrench } from "lucide-react";

export function StepIcon({ tool, className }: { tool: string; className?: string }) {
  if (tool === "web_search") return <Globe className={className} />;
  if (tool === "retrieve_documents") return <FileSearch className={className} />;
  return <Wrench className={className} />;
}

export function toolLabel(tool: string): string {
  switch (tool) {
    case "web_search":
      return "Searching the web";
    case "retrieve_documents":
      return "Retrieving documents";
    default:
      return tool;
  }
}
