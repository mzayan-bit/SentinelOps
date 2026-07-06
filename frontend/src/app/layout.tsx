import type { Metadata } from "next";
import { AppShell } from "@/components/layout";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryProvider } from "@/providers/query-provider";
import { Toaster } from "sonner";
import "./globals.css";

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
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="h-full">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <QueryProvider>
            <AppShell>{children}</AppShell>
            <Toaster position="top-right" richColors closeButton />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
