import { notFound } from "next/navigation";
import { CASES } from "../../../../data";
import { SnippetPage } from "../../../../components";

export default async function Page({ params }: { params: Promise<{ caseId: string; snippetIndex: string }> }) {
  const { caseId, snippetIndex } = await params;
  const index = Number(snippetIndex);
  const currentCase = CASES.find((item) => item.id === caseId);
  if (!currentCase || !Number.isInteger(index) || index < 0 || index >= currentCase.snippets.length) notFound();
  return <SnippetPage caseId={caseId} snippetIndex={index} />;
}
