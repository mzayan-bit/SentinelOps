import math
from typing import Dict, Tuple
from app.services.pipeline_core.stage import PipelineStage
from app.services.pipeline_core.context import PipelineContext

class CentroidTracker:
    def __init__(self, maxDisappeared=50):
        self.nextObjectID = 0
        self.objects = {}
        self.disappeared = {}
        self.maxDisappeared = maxDisappeared

    def register(self, centroid):
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        del self.objects[objectID]
        del self.disappeared[objectID]

    def update(self, rects):
        if len(rects) == 0:
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)
            return self.objects

        inputCentroids = []
        for (startX, startY, endX, endY) in rects:
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            inputCentroids.append((cX, cY))

        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.register(inputCentroids[i])
        else:
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            # A very naive mapping just to prevent crashes and keep the pipeline modular.
            # Production would use scipy.spatial.distance.cdist
            for i, (cX, cY) in enumerate(inputCentroids):
                min_dist = float('inf')
                best_id = None
                for obj_id, (ox, oy) in self.objects.items():
                    dist = math.hypot(cX - ox, cY - oy)
                    if dist < min_dist:
                        min_dist = dist
                        best_id = obj_id
                        
                if best_id is not None and min_dist < 100:
                    self.objects[best_id] = (cX, cY)
                    self.disappeared[best_id] = 0
                else:
                    self.register((cX, cY))

            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)

        return self.objects

class TrackingStage(PipelineStage):
    """
    Assigns stable IDs to detected objects across frames.
    """
    def __init__(self, max_disappeared: int = 30, max_distance: int = 150):
        self.tracker = CentroidTracker(maxDisappeared=max_disappeared)

    def process(self, context: PipelineContext) -> PipelineContext:
        rects = []
        for det in context.detections:
            bbox = det["bounding_box"]
            rects.append((
                int(bbox["x_min"]), 
                int(bbox["y_min"]), 
                int(bbox["x_max"]), 
                int(bbox["y_max"])
            ))
            
        objects = self.tracker.update(rects)
        context.tracks = [{"object_id": obj_id, "centroid": centroid} for obj_id, centroid in objects.items()]
        
        return context
