import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@avrig/ui";

interface TracePin {
  id: string;
  label: string;
  version: string;
}

interface TraceChain {
  id: string;
  relationship: string;
  requirement: TracePin;
  artifact: TracePin;
  test: TracePin;
  deployed: TracePin;
}

const COLUMNS: Array<{ key: keyof Pick<TraceChain, "requirement" | "artifact" | "test" | "deployed">; title: string }> = [
  { key: "requirement", title: "Requirement" },
  { key: "artifact", title: "Artifact" },
  { key: "test", title: "Test" },
  { key: "deployed", title: "Deployed" },
];

const COLUMN_X = [110, 400, 660, 850];
const LANE_Y = [110, 200, 290];
const LANE_JITTER = [0, 28, 8, 34];
const VIEW_WIDTH = 960;
const VIEW_HEIGHT = 360;
const BEND_RADIUS = 9;

const traceChains: TraceChain[] = [
  {
    id: "link-auth",
    relationship: "implements",
    requirement: { id: "REQ-AUTH-01", label: "Universal OIDC requirement", version: "1.4.0" },
    artifact: { id: "FE-06", label: "UniversalAuthProvider", version: "2.1.0" },
    test: { id: "TS-AUTH-04", label: "OIDC discovery round trip", version: "1.0.2" },
    deployed: { id: "DEP-WEB", label: "avrig-web-ui", version: "0.5.0" },
  },
  {
    id: "link-distributed",
    relationship: "constrains",
    requirement: { id: "ADR-042", label: "Distributed transaction baseline", version: "1.0.0" },
    artifact: { id: "STG-04", label: "Enterprise data model", version: "3.2.1" },
    test: { id: "TS-EDM-11", label: "Idempotent migration replay", version: "0.9.0" },
    deployed: { id: "DEP-API", label: "avrig-api", version: "0.5.0" },
  },
  {
    id: "link-vector",
    relationship: "verifies",
    requirement: { id: "EDM-DOC-VEC", label: "Document vector entity", version: "2.0.3" },
    artifact: { id: "KM-INGEST", label: "Knowledge ingestion pipeline", version: "1.3.4" },
    test: { id: "TS-KM-07", label: "Chunk recall precision", version: "1.0.1" },
    deployed: { id: "DEP-KM", label: "avrig-km-worker", version: "0.4.2" },
  },
];

interface Point {
  x: number;
  y: number;
}

const round = (value: number) => Math.round(value * 10) / 10;

const stepToward = (from: Point, toward: Point, distance: number): Point => {
  const dx = toward.x - from.x;
  const dy = toward.y - from.y;
  const length = Math.hypot(dx, dy) || 1;
  return {
    x: round(from.x + (dx / length) * distance),
    y: round(from.y + (dy / length) * distance),
  };
};

/** Orthogonal run between pins: straight legs, small radius only at the turns. */
const routeThrough = (ys: number[]): Point[] => {
  const points: Point[] = [{ x: COLUMN_X[0], y: ys[0] }];
  for (let i = 1; i < COLUMN_X.length; i += 1) {
    const midX = Math.round((COLUMN_X[i - 1] + COLUMN_X[i]) / 2);
    points.push({ x: midX, y: ys[i - 1] }, { x: midX, y: ys[i] }, { x: COLUMN_X[i], y: ys[i] });
  }
  return points;
};

const toPathData = (points: Point[]): string => {
  let data = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i += 1) {
    const previous = points[i - 1];
    const corner = points[i];
    const next = points[i + 1];
    const radius = Math.min(
      BEND_RADIUS,
      Math.hypot(corner.x - previous.x, corner.y - previous.y) / 2,
      Math.hypot(next.x - corner.x, next.y - corner.y) / 2
    );
    const entry = stepToward(corner, previous, radius);
    const exit = stepToward(corner, next, radius);
    data += ` L ${entry.x} ${entry.y} Q ${corner.x} ${corner.y} ${exit.x} ${exit.y}`;
  }
  const last = points[points.length - 1];
  return `${data} L ${last.x} ${last.y}`;
};

const toPercent = (value: number, total: number) => `${round((value / total) * 100)}%`;

export const KnowledgeView: React.FC = () => {
  const [activeChainId, setActiveChainId] = useState<string>(traceChains[0].id);

  const lanes = traceChains.map((chain, index) => {
    const ys = LANE_JITTER.map((jitter) => LANE_Y[index] + jitter);
    return {
      chain,
      ys,
      path: toPathData(routeThrough(ys)),
      pins: COLUMNS.map((column, columnIndex) => ({
        column: column.title,
        x: COLUMN_X[columnIndex],
        y: ys[columnIndex],
        pin: chain[column.key],
      })),
    };
  });

  const activeChain = traceChains.find((chain) => chain.id === activeChainId) ?? traceChains[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-[28px] leading-tight font-semibold tracking-tight">
          Knowledge and lineage traceability
        </h1>
        <p className="text-sm text-text-secondary">
          The links between requirements, design decisions, data entities, and the artifacts that satisfy them.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-medium text-text-secondary">Lineage and traceability</h2>
          <span className="font-mono text-xs text-muted-foreground">Apache AGE traversal</span>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <Card>
            <CardHeader className="border-b border-border pb-4">
              <CardTitle className="text-sm font-semibold">Active graph lineage</CardTitle>
              <CardDescription className="text-xs">
                Every pin is a recorded version, so a route describes one moment rather than a moving target.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <div
                  className="relative min-w-[720px]"
                  style={{ aspectRatio: `${VIEW_WIDTH} / ${VIEW_HEIGHT}` }}
                >
                  <svg
                    viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
                    className="absolute inset-0 h-full w-full"
                    aria-hidden="true"
                  >
                    {COLUMNS.map((column, index) => (
                      <text
                        key={column.key}
                        x={COLUMN_X[index]}
                        y={40}
                        textAnchor="middle"
                        className="fill-muted-foreground font-mono text-[11px]"
                      >
                        {column.title}
                      </text>
                    ))}

                    {lanes.map((lane) => {
                      const isActive = lane.chain.id === activeChainId;
                      return (
                        <g key={lane.chain.id}>
                          <path
                            d={lane.path}
                            fill="none"
                            strokeWidth={isActive ? 1.5 : 1}
                            strokeLinecap="round"
                            className={isActive ? "stroke-muted-foreground" : "stroke-border"}
                          />
                          <text
                            x={255}
                            y={lane.ys[0] - 14}
                            textAnchor="middle"
                            className="fill-muted-foreground font-mono text-[10px]"
                          >
                            {lane.chain.relationship}
                          </text>
                          {lane.pins.map((pin) => (
                            <g key={`${lane.chain.id}-${pin.column}`}>
                              <circle
                                cx={pin.x}
                                cy={pin.y}
                                r={isActive ? 4.5 : 3.5}
                                className={
                                  isActive
                                    ? "fill-primary"
                                    : "fill-muted-foreground/70"
                                }
                              />
                              <text
                                x={pin.x}
                                y={pin.y + 20}
                                textAnchor="middle"
                                className="fill-muted-foreground font-mono text-[10px] tabular-nums"
                              >
                                {pin.pin.version}
                              </text>
                            </g>
                          ))}
                        </g>
                      );
                    })}
                  </svg>

                  {lanes.map((lane) =>
                    lane.pins.map((pin) => {
                      const isActive = lane.chain.id === activeChainId;
                      return (
                        <button
                          key={`hit-${lane.chain.id}-${pin.column}`}
                          type="button"
                          aria-pressed={isActive}
                          aria-label={`${pin.column}: ${pin.pin.id} ${pin.pin.label}, version ${pin.pin.version}`}
                          onMouseEnter={() => setActiveChainId(lane.chain.id)}
                          onFocus={() => setActiveChainId(lane.chain.id)}
                          onClick={() => setActiveChainId(lane.chain.id)}
                          className="absolute size-6 -translate-x-1/2 -translate-y-1/2 rounded-full focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card focus-visible:outline-none"
                          style={{ left: toPercent(pin.x, VIEW_WIDTH), top: toPercent(pin.y, VIEW_HEIGHT) }}
                        />
                      );
                    })
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="self-start">
            <CardHeader className="border-b border-border pb-4">
              <CardTitle className="text-sm font-semibold">Selected route</CardTitle>
              <CardDescription className="font-mono text-xs">
                {activeChain.relationship}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-xs">
              {[
                { role: "Requirement", pin: activeChain.requirement },
                { role: "Artifact", pin: activeChain.artifact },
                { role: "Test", pin: activeChain.test },
                { role: "Deployed", pin: activeChain.deployed },
              ].map((entry) => (
                <div key={entry.role} className="space-y-0.5">
                  <div className="text-[11px] text-muted-foreground">{entry.role}</div>
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="min-w-0 flex-1">
                      <span className="font-mono text-[11px] text-text-secondary">{entry.pin.id}</span>
                      <span className="block truncate text-foreground">{entry.pin.label}</span>
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                      v{entry.pin.version}
                    </span>
                  </div>
                </div>
              ))}

              <p className="border-t border-border pt-3 text-[11px] leading-relaxed text-muted-foreground">
                Three recorded routes. Hover or focus any pin to raise its route here.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
