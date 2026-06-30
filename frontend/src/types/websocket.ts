export type ConnectionStatus = "CONNECTING" | "OPEN" | "CLOSED" | "ERROR";

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Detection {
  id: string;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
}

export interface StreamMessage {
  frame: string; // Base64 encoded JPEG
  detections: Detection[];
  fps: number;
  violation_count: number;
  timestamp: number;
}
