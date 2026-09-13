import { notFound } from "next/navigation";
import { CASES } from "../../../data";
import { RationalePage } from "../../../components";

export default async function Page({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  if (!CASES.some((item) => item.id === caseId)) notFound();
  return <RationalePage caseId={caseId} />;
}
