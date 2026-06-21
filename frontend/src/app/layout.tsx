import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/layout";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "SentinelOps — PPE Safety Monitoring",
    template: "%s | SentinelOps",
  },
  description:
    "Production-grade PPE detection and safety monitoring platform powered by YOLO computer vision models.",
  keywords: ["PPE", "safety", "monitoring", "YOLO", "detection", "MLOps"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
