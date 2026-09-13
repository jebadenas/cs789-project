import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "@primer/primitives/dist/css/functional/themes/light.css";
import "./globals.css";
import { Providers } from "./providers";
import { QuestionnaireProvider } from "./state";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Tutor Questionnaire",
  description: "Anonymised team-journal review survey.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <Providers>
          <QuestionnaireProvider>{children}</QuestionnaireProvider>
        </Providers>
      </body>
    </html>
  );
}
