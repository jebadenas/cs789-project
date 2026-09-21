import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Team Health",
  description: "Coordinator dashboard for capstone team health from reflective journals.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
