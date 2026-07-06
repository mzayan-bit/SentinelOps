import numpy as np
from scipy.optimize import linear_sum_assignment
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext

def iou(bb_test, bb_gt):
    """
    Computes Intersection Over Union between two bounding boxes in [x1,y1,x2,y2] format.
    """
    xx1 = np.maximum(bb_test[0], bb_gt[0])
    yy1 = np.maximum(bb_test[1], bb_gt[1])
    xx2 = np.minimum(bb_test[2], bb_gt[2])
    yy2 = np.minimum(bb_test[3], bb_gt[3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[2]-bb_test[0])*(bb_test[3]-bb_test[1])
      + (bb_gt[2]-bb_gt[0])*(bb_gt[3]-bb_gt[1]) - wh)
    return o

class Track:
    def __init__(self, obj_id, bbox):
        self.id = obj_id
        self.bbox = bbox # [x1, y1, x2, y2]
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self.history = [bbox]

    def get_centroid(self):
        return (int((self.bbox[0] + self.bbox[2])/2), int((self.bbox[1] + self.bbox[3])/2))
        
    def update(self, bbox):
        self.bbox = bbox
        self.history.append(bbox)
        if len(self.history) > 30: # keep last 30 frames
            self.history.pop(0)
        self.hits += 1
        self.time_since_update = 0

class IoUTracker:
    def __init__(self, max_age=15, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks = []
        self.frame_count = 0
        self.next_id = 1

    def update(self, dets):
        self.frame_count += 1
        
        # Format detections into Nx4 array
        if len(dets) == 0:
            for trk in self.tracks:
                trk.time_since_update += 1
            # Remove dead tracks
            self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]
            return [t for t in self.tracks if t.time_since_update == 0]

        dets = np.array(dets)

        if len(self.tracks) == 0:
            for det in dets:
                self.tracks.append(Track(self.next_id, det))
                self.next_id += 1
            return self.tracks

        # Compute IoU matrix
        iou_matrix = np.zeros((len(dets), len(self.tracks)), dtype=np.float32)
        for d, det in enumerate(dets):
            for t, trk in enumerate(self.tracks):
                iou_matrix[d, t] = iou(det, trk.bbox)

        # Hungarian Matching (minimize cost -> maximize IoU)
        matched_indices = linear_sum_assignment(-iou_matrix)
        matched_indices = np.asarray(matched_indices).T

        unmatched_detections = []
        for d, det in enumerate(dets):
            if d not in matched_indices[:, 0]:
                unmatched_detections.append(d)
                
        unmatched_tracks = []
        for t, trk in enumerate(self.tracks):
            if t not in matched_indices[:, 1]:
                unmatched_tracks.append(t)

        matches = []
        for m in matched_indices:
            if iou_matrix[m[0], m[1]] < self.iou_threshold:
                unmatched_detections.append(m[0])
                unmatched_tracks.append(m[1])
            else:
                matches.append(m.reshape(1, 2))
                
        if len(matches) == 0:
            matches = np.empty((0, 2), dtype=int)
        else:
            matches = np.concatenate(matches, axis=0)

        # Update matched tracks
        for m in matches:
            self.tracks[m[1]].update(dets[m[0]])
            
        # Create tracks for unmatched detections
        for i in unmatched_detections:
            self.tracks.append(Track(self.next_id, dets[i]))
            self.next_id += 1
            
        # Update time for unmatched tracks
        for i in unmatched_tracks:
            self.tracks[i].time_since_update += 1

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # Return only currently active (updated in this frame) or slightly occluded (allows drawing)
        # We'll return all tracks that haven't been dead for too long so the downstream engines can use them
        return [t for t in self.tracks if t.time_since_update <= 2 and t.hits >= self.min_hits]


class TrackingStage(PipelineStage):
    """
    Assigns stable IDs to detected objects across frames using an IoU/Hungarian tracker.
    Handles temporary disappearances (occlusions) robustly.
    """
    def __init__(self, max_age: int = 15, iou_threshold: float = 0.3):
        # We keep min_hits=1 for fast responsiveness in PPE detection, but max_age=15 prevents ID switching
        self.tracker = IoUTracker(max_age=max_age, min_hits=1, iou_threshold=iou_threshold)

    def process(self, context: PipelineContext) -> PipelineContext:
        rects = []
        det_map = {} # Map bounding box tuple to original detection dict to fuse data
        
        for idx, det in enumerate(context.detections):
            bbox = det["bounding_box"]
            rect = (
                bbox["x_min"], 
                bbox["y_min"], 
                bbox["x_max"], 
                bbox["y_max"]
            )
            rects.append(rect)
            det_map[rect] = det
            
        active_tracks = self.tracker.update(rects)
        
        context_tracks = []
        for track in active_tracks:
            # Reconstruct the tracking output
            ctx_track = {
                "object_id": track.id,
                "centroid": track.get_centroid(),
                "bbox": track.bbox,
                "age": track.age,
                "hits": track.hits,
                "time_since_update": track.time_since_update,
                "history": track.history,
                # Try to map back to the original YOLO detection classes if updated this frame
                "class_name": "unknown",
                "confidence": 0.0
            }
            
            # Find the best matching detection to carry over YOLO metadata (like class_name)
            if track.time_since_update == 0:
                best_iou = 0
                best_det = None
                for orig_rect, orig_det in det_map.items():
                    o = iou(track.bbox, orig_rect)
                    if o > best_iou:
                        best_iou = o
                        best_det = orig_det
                if best_det and best_iou > 0.5:
                    ctx_track["class_name"] = best_det["class_name"]
                    ctx_track["confidence"] = best_det["confidence"]
                    # Optionally attach the tracking ID directly to the detection
                    best_det["track_id"] = track.id
                    
            context_tracks.append(ctx_track)
            
        context.tracks = context_tracks
        
        return context
