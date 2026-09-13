import { notFound } from "next/navigation";
import { CASES } from "../../../data";
import { TriagePage } from "../../../components";

export default async function Page({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  if (!CASES.some((item) => item.id === caseId)) notFound();
  return <TriagePage caseId={caseId} />;
}
