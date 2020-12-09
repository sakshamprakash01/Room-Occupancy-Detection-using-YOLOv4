from cv2 import cv2
import numpy as np
import time
import sys
import os
from centroidtracker import CentroidTracker
import copy

tracker = CentroidTracker(maxDisappeared=20, maxDistance=90)

CONFIDENCE = 0.5
SCORE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.5

config_path = "cfg/yolov4.cfg"
weights_path = "yolov4.weights"
labels = open("data/coco.names").read().strip().split("\n")

net = cv2.dnn.readNetFromDarknet(config_path, weights_path)

path_name = "test_videos/muskan2.mp4"
cap = cv2.VideoCapture(path_name)

video_framerate = cap.get(cv2.CAP_PROP_FPS)

ln = net.getLayerNames()
ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]

object_id_list = []
total_count = 0

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("output2.mp4", fourcc, video_framerate, (1920, 1080), True)
fps = 0
frameNo = 0

rooms=[{"MinX":1118,"MaxX":1600,"MinY":115,"MaxY":971},{"MinX":266,"MaxX":480,"MinY":141,"MaxY":680}]
occupancy = [0,0]
entry_exit = {}

# cv2.namedWindow('controls')
# cv2.createTrackbar('MinX','controls',200,1920,lambda x:x)
# cv2.createTrackbar('MinY','controls',200,1080,lambda x:x)
# cv2.createTrackbar('MaxX','controls',600,1920,lambda x:x)
# cv2.createTrackbar('MaxY','controls',600,1080,lambda x:x)

while True:
    start_time = time.time()

    ret, image = cap.read()
    if not ret:
        break
    # image = cv2.resize(image, (0,0), fx=0.5, fy=0.5)

    # MinX = cv2.getTrackbarPos('MinX','controls')
    # MinY = cv2.getTrackbarPos('MinY','controls')
    # MaxX = cv2.getTrackbarPos('MaxX','controls')
    # MaxY = cv2.getTrackbarPos('MaxY','controls')

    # image = image[MinY:MaxY, MinX:MaxX]
    for i,room in enumerate(rooms): 
        cv2.rectangle(image, (room["MinX"], room["MinY"]), (room["MaxX"], room["MaxY"]), (255, 0, 0), 1)
        cv2.putText(image, "Room-{n}".format(n=i+1), (room["MinX"], room["MinY"]), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 1,)

    image_cpy = copy.deepcopy(image)

    unique_count = 0
    current_count = 0

    h, w = image.shape[:2]

    # DwellYLevel = 500
    # cv2.line(image, (0, DwellYLevel), (1920, DwellYLevel), (255, 128, 0), 2)
    # cv2.putText(
    #     image,
    #     "Dwell Area",
    #     (w - 250, DwellYLevel + 50),
    #     cv2.FONT_HERSHEY_SIMPLEX,
    #     1.5,
    #     (255, 128, 0),
    #     1,
    # )

    blob = cv2.dnn.blobFromImage(image_cpy, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)

    layer_outputs = net.forward(ln)

    outputs = np.vstack(layer_outputs)

    boxes, confidences, class_ids, rects = [], [], [], []

    for output in outputs:

        scores = output[5:]
        class_id = np.argmax(scores)
        confidence = scores[class_id]

        if class_id != 0:
            continue
        if confidence > CONFIDENCE:

            box = output[:4] * np.array([w, h, w, h])
            (centerX, centerY, width, height) = box.astype("int")

            x = int(centerX - (width / 2))
            y = int(centerY - (height / 2))

            boxes.append([x, y, int(width), int(height)])
            confidences.append(float(confidence))
            class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.6, 0.3)

    if len(indices) > 0:
        for i in indices.flatten():
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 1)
            person_box = [x, y, x + w, y + h]
            rects.append(person_box)

    boundingboxes = np.array(rects)
    boundingboxes = boundingboxes.astype(int)

    objects, dereg = tracker.update(rects)

    print(dereg)
    print()
    for (objectId, bbox) in objects.items():
        x1, y1, x2, y2 = bbox
        x1 = abs(int(x1))
        y1 = abs(int(y1))
        x2 = abs(int(x2))
        y2 = abs(int(y2))

        centroidX = int((x1 + x2) / 2)
        centroidY = int((y1 + y2) / 2)

        cv2.circle(image, (centroidX, centroidY), 5, (255, 255, 255), thickness=-1)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if objectId not in object_id_list:  # NEW PERSON
            object_id_list.append(objectId)  # Append in ObjectID list - list of ID of people who have come before
            unique_count += 1

            if (centroidX >= rooms[0]["MinX"] and centroidX <= rooms[0]["MaxX"] and centroidY >= rooms[0]["MinY"] and centroidY <= rooms[0]["MaxY"]):
                key=objectId
                value = [1,0,0] # [R1,R2,O]
                entry_exit[key]=value
            
            elif (centroidX >= rooms[1]["MinX"] and centroidX <= rooms[1]["MaxX"] and centroidY >= rooms[1]["MinY"] and centroidY <= rooms[1]["MaxY"]):
                key=objectId
                value = [0,1,0] # [R1,R2,O]
                entry_exit[key]=value
            else:
                key=objectId
                value = [0,0,1] # [R1,R2,O]
                entry_exit[key]=value
            
        else:

            if (centroidX >= rooms[0]["MinX"] and centroidX <= rooms[0]["MaxX"] and centroidY >= rooms[0]["MinY"] and centroidY <= rooms[0]["MaxY"]):
                pass
            
            elif (centroidX >= rooms[1]["MinX"] and centroidX <= rooms[1]["MaxX"] and centroidY >= rooms[1]["MinY"] and centroidY <= rooms[1]["MaxY"]):
                pass
            else:
                if (entry_exit[objectId][0]==1):
                    occupancy[0]-=1
                    entry_exit[objectId][0]=0
                elif (entry_exit[objectId][1]==1):
                    occupancy[1]-=1
                    entry_exit[objectId][1]=0

        

        ID_text = "Person:" + str(objectId)

        cv2.putText(image, ID_text, (x1, y1 - 7), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1.5, (0, 0, 255), 2)
        current_count += 1

    for (objectID, bbox) in dereg.items():
        x1, y1, x2, y2 = bbox
        x1 = abs(int(x1))
        y1 = abs(int(y1))
        x2 = abs(int(x2))
        y2 = abs(int(y2))

        centroidX = int((x1 + x2) / 2)
        centroidY = int((y1 + y2) / 2)

        if (centroidX >= rooms[0]["MinX"] and centroidX <= rooms[0]["MaxX"] and centroidY >= rooms[0]["MinY"] and centroidY <= rooms[0]["MaxY"] and entry_exit[objectID][0]!=1):
            occupancy[0]+=1
            del entry_exit[objectID]
            tracker.deleteDereg(objectID)
        elif (centroidX >= rooms[1]["MinX"] and centroidX <= rooms[1]["MaxX"] and centroidY >= rooms[1]["MinY"] and centroidY <= rooms[1]["MaxY"] and entry_exit[objectID][1]!=1):
            occupancy[1]+=1
            del entry_exit[objectID]
            tracker.deleteDereg(objectID)
        else:
            del entry_exit[objectID]
            tracker.deleteDereg(objectID)


    total_count += unique_count
    total_count_text = "Total Count:" + str(total_count)
    cv2.putText(
        image,
        total_count_text,
        (5, 400),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 255),
        2,
    )

    current_count_text = "Current Count:" + str(current_count)
    cv2.putText(
        image,
        current_count_text,
        (5, 450),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 255),
        2,
    )

    occupancy1_text = "Room1: " + str(occupancy[0]) + " People"
    cv2.putText(
        image,
        occupancy1_text,
        (5, 500),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 255),
        2,
    )

    occupancy2_text = "Room2: " + str(occupancy[1]) + " People"
    cv2.putText(
        image,
        occupancy2_text,
        (5, 550),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 255),
        2,
    )

    end_time = time.time()
    fps = 1 / (end_time - start_time)
    fps_text = "FPS: {:.2f}".format(fps)
    cv2.putText(image, fps_text, (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    frameNo += 1

    out.write(image)
    cv2.imshow("Application", image)

    key = cv2.waitKey(1)
    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()