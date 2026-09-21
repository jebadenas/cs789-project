import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tutor Questionnaire",
  description: "Anonymised team-journal review survey.",
};

const TUTOR_ID = process.env.NEXT_PUBLIC_TUTOR_ID || "Tutor A";
const DEFAULT_DARK = process.env.NEXT_PUBLIC_DEFAULT_THEME === "dark";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" data-color-mode={DEFAULT_DARK ? "dark" : undefined} data-tutor={TUTOR_ID}>
      <body>{children}</body>
    </html>
  );
}
