import { notFound } from "next/navigation";
import { CASES } from "../../../data";
import { SubmittedPage } from "../../../components";

export default async function Page({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  if (!CASES.some((item) => item.id === caseId)) notFound();
  return <SubmittedPage caseId={caseId} />;
}
