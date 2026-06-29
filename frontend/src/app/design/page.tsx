"use client";

import * as React from "react";
import { PageHeader } from "@/components/ui";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { ShieldAlert, Info } from "lucide-react";

export default function DesignSystemPage() {
  return (
    <div className="space-y-12 pb-12">
      <PageHeader
        title="Design System"
        description="Core components, typography, and color tokens."
        icon={Info}
      />

      {/* Typography */}
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Typography</h2>
          <p className="text-sm text-[var(--color-muted)]">Font weights, sizes, and styles.</p>
        </div>
        <div className="glass space-y-8 rounded-xl p-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">Heading 1</h1>
            <p className="mt-1 text-sm text-[var(--color-muted)]">4xl/5xl, Extrabold</p>
          </div>
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">Heading 2</h2>
            <p className="mt-1 text-sm text-[var(--color-muted)]">3xl, Semibold</p>
          </div>
          <div>
            <h3 className="text-2xl font-semibold tracking-tight">Heading 3</h3>
            <p className="mt-1 text-sm text-[var(--color-muted)]">2xl, Semibold</p>
          </div>
          <div>
            <h4 className="text-xl font-semibold tracking-tight">Heading 4</h4>
            <p className="mt-1 text-sm text-[var(--color-muted)]">xl, Semibold</p>
          </div>
          <div>
            <p className="leading-7 [&:not(:first-child)]:mt-6">
              Paragraph. The quick brown fox jumps over the lazy dog. A cohesive design system
              brings harmony to complex interfaces.
            </p>
            <p className="mt-1 text-sm text-[var(--color-muted)]">Base, Regular</p>
          </div>
        </div>
      </section>

      {/* Buttons */}
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Buttons</h2>
          <p className="text-sm text-[var(--color-muted)]">
            Interactive primary and secondary actions.
          </p>
        </div>
        <div className="glass flex flex-wrap items-center gap-4 rounded-xl p-6">
          <Button>Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
        </div>
        <div className="glass flex flex-wrap items-center gap-4 rounded-xl p-6">
          <Button size="lg">Large Size</Button>
          <Button size="default">Default Size</Button>
          <Button size="sm">Small Size</Button>
          <Button size="icon">
            <ShieldAlert />
          </Button>
        </div>
      </section>

      {/* Badges */}
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Badges</h2>
          <p className="text-sm text-[var(--color-muted)]">Status indicators and small tags.</p>
        </div>
        <div className="glass flex flex-wrap gap-4 rounded-xl p-6">
          <Badge>Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="destructive">Destructive</Badge>
        </div>
      </section>

      {/* Cards & Dialogs */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <section className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Cards</h2>
            <p className="text-sm text-[var(--color-muted)]">Containers for bounded content.</p>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>System Health</CardTitle>
              <CardDescription>Live telemetry from all cameras.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm">All ML models are running at peak efficiency.</p>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button variant="outline">View Logs</Button>
              <Button>Acknowledge</Button>
            </CardFooter>
          </Card>
        </section>

        <section className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Dialogs</h2>
            <p className="text-sm text-[var(--color-muted)]">Modal windows for focused actions.</p>
          </div>
          <div className="glass flex h-[200px] items-center justify-center rounded-xl p-6">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="secondary">Open Modal</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Confirm Action</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to proceed? This action cannot be undone.
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  <p className="text-sm">This is the dialog content area.</p>
                </div>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DialogClose>
                  <Button variant="destructive">Confirm</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </section>
      </div>

      {/* Tables */}
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Tables</h2>
          <p className="text-sm text-[var(--color-muted)]">
            Data visualization for rows and columns.
          </p>
        </div>
        <div className="glass overflow-hidden rounded-xl">
          <Table>
            <TableCaption>Recent system incidents.</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">ID</TableHead>
                <TableHead>Camera</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-medium">INC-001</TableCell>
                <TableCell>Entrance Cam</TableCell>
                <TableCell>No Helmet</TableCell>
                <TableCell className="text-right">
                  <Badge variant="destructive">Open</Badge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">INC-002</TableCell>
                <TableCell>Loading Dock</TableCell>
                <TableCell>No Vest</TableCell>
                <TableCell className="text-right">
                  <Badge variant="warning">Pending</Badge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">INC-003</TableCell>
                <TableCell>Crane Area</TableCell>
                <TableCell>Zone Breach</TableCell>
                <TableCell className="text-right">
                  <Badge variant="success">Resolved</Badge>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}
