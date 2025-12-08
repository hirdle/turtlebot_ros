from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import numpy as np
import cv2.aruco
#import glob

# Load previously saved data
with np.load('B.npz') as X:
    mtx, dist, _, _ = [X[i] for i in ('arr_0','arr_1','arr_2','arr_3')]
#print 'mtx=',mtx,'dist=',dist
#exit(0)

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)#(800, 600)#
camera.framerate = 24 #32
rawCapture = PiRGBArray(camera, size=(640, 480)) #(800, 608)
 
# allow the camera to warmup
time.sleep(0.1)
font = cv2.FONT_HERSHEY_SIMPLEX
framenumber = 0
markerLength = 13.3 # 133 миллиметра сторона маркера

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_ARUCO_ORIGINAL)
 
# capture frames from the camera
for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image, then initialize the timestamp
    # and occupied/unoccupied text
    img = frame.array
    # увеличим яркость, дабы робот не ослеп
    cv2.convertScaleAbs(img,img,1.8, 0)#img = img * 2 #convertTo(img,-1,1.5,50)
    # обработаем картинку
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = cv2.aruco.detectMarkers(gray, dictionary)
    if len(corners)>0:
        cv2.aruco.drawDetectedMarkers(img, corners, ids)
        rvecs = cv2.aruco.estimatePoseSingleMarkers(corners, markerLength, mtx, dist)
        print 'corners = ',corners
        print 'rvecs =',rvecs
        #exit(0)
        i=0
        while i<len(rvecs[0]):
            cv2.aruco.drawAxis(img, mtx, dist, rvecs[0][i], rvecs[1][i], 5)
            i=i + 1
    #"r: "+str(rvecs[0][0])+
    #cv2.putText(img," v:"+str(rvecs[0][0]),(10,450), font, 1,(0,128,0),1,cv2.LINE_AA)
    cv2.imshow('img', img)
    #cv2.imshow("Frame", gray) #image)
    key = cv2.waitKey(1) & 0xFF
 
    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
    framenumber=framenumber+1
    #print framenumber, ret
    # if the `q` key was pressed, break from the loop
    if key == ord("q"):#or framenumber>20:
        break
    
#cv2.destroyAllWindows()