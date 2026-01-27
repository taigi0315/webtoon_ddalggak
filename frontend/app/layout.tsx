import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/shell/AppShell";
import QueryProvider from "@/lib/query/queryClient";

export const metadata: Metadata = {
  title: "Webtoon Studio",
  description: "Webtoon scene planner and renderer"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
