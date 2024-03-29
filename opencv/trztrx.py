
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  8 15:12:19 2018

@author: pland
"""
#다시 받아친 공이 인식되는지도 체크 할 것. - > 일단 y값 기준으로 해놨다.
#만약 highest 안잡히면 탁구대에 일정 환경설정해놓고 센터 잡아서 거기를 기준으로 donrec아닌데 넘어갈때 xyz잡을것.
#내일 할 일 계산된 x,z가 가능범위를 벗어나면 교정하여 값을 보내기
# import the necessary packages
from collections import deque
from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time
import threading
import math
import serial
import socket

#def __init__(self):
    
timing_h = 0
lockgz = threading.Lock()
timing_l = 0
#lock2 = threading.Lock()    
ry = 600 #나중에 진짜값으로 바꾸기. 레일의 y값.
gorob = 0 #로봇에게 전달하고 싶을때만 1
rz = 50 # 대충 무난한 값. 혹시 모르니까 + z는 어차피 비슷 할 것 같다. 
gotz = 0
trz = 0

#로봇과 연결
robot = serial.Serial('COM6', 9600)

#레일과 연결 
client = socket.socket()
HOST = "169.254.7.25"
PORT = 5003
BUFSIZE = 1024
ADDR = (HOST, PORT)

client.connect(ADDR)
print('Connected to', HOST)


#    message = str(input("Enter something for the server: "))
#    client.send(message.encode('utf-8'))
def opencv1():#측면 카메라
    
    global timing_h
    global timing_l
#    global lock1    
#    global lock2
    global rz
    global gotz
    global lockgz
    global trz
    
        
    # if a video path was not supplied, grab the reference
    # to the webcam
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video",
    	help="path to the (optional) video file")
    ap.add_argument("-b", "--buffer", type=int, default=64,
    	help="max buffer size")
    args = vars(ap.parse_args())
    
    # define the lower and upper boundaries of the "green"
    # ball in the HSV color space, then initialize the
    # list of tracked points
    lower_orange = np.array([10,100,50])  
    upper_orange = np.array([70,245,250])
    pts = deque(maxlen=args["buffer"])
    vs = VideoStream(1).start()#수정 src=0을 1로 바꿈
    
    # allow the camera or video file to warm up
    time.sleep(3.0)
    y_recent = [] #경향성 체크
    z_recent = [] #경향성 체크
    z_history = [] #예측 z값 구하기 위함
    y_history = []
    testh = 0 # 테스트용.
    testl = 0
    pastdown = 0
    pastup = 0
    lenrec= 10 #x,z 좌표를 recent에 몇개 저장할 것인가
    suc = 0
    dontrec = 0 # y가 거꾸로가면 기록을 막는다.

    net = 200 #네트값


    mid = 300 #탁구대 정중앙 x(천장캠 프레임 기준),       추후 정확하게 변경
    arm = 18 #로봇팔길이 
    ztrans = 30 #프레임 바닥에 찍히는 z~로봇 어깨cell 회전축까지의 높이,단위는 cm. 추후 바꿈.
    conx = 0.3 # 변환상수 (추후 바꿈)
    conz = 0.4 #변환상수 (추후 바꿈)
    # keep looping
    while True:
    	# grab the current frame
        frame = vs.read()
     
    	# handle the frame from VideoCapture or VideoStream
        frame = frame[1] if False else frame
     
    	# if we are viewing a video and we did not grab a frame,q
    	# then we have reached the end of the video
        if frame is None:
            break
     
    	# resize the frame, blur it, and convert it to the HSV
    	# color space
        frame = imutils.resize(frame, width=600)
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
     
    	# construct a mask for the color "green", then perform
    	# a series of dilations and erosions to remove any small
    	# blobs left in the mask
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
    
    	# find contours in the mask and initialize the current
    	# (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        center = None
        y_coor = 0
        z_coor = 0
    	# only proceed if at least one contour was found
        if len(cnts) > 0:
    		# find the largest contour in the mask, then use
    		# it to compute the minimum enclosing circle and
    		# centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            y_coor = int(M["m10"] / M["m00"])
            z_coor = int(M["m01"] / M["m00"])
            center = (int(M["m10"] / M["m00"]),int(M["m01"] / M["m00"])) 
            #print(center)
    		# only proceed if the radius meets a minimum size
            if radius > 10:
    			# draw the circle and centroid on the frame,
    			# then update the list of tracked points
                cv2.circle(frame, (int(x), int(y)), int(radius),
    				(0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)
        
    	# update the points queue
        pts.appendleft(center)
        y_recent.append(y_coor)
        z_recent.append(z_coor)
        z_history.append(z_coor)
        y_history.append(y_coor)
        
        
        if (len(y_recent) > lenrec):
            del y_recent[0]
        if (len(y_recent) == lenrec):
            front = 0
            back = 0
            equ = 0
            for i in range(1, len(y_recent)): 
                if (y_recent[i]) < (y_recent[i-1]):
                    front += 1
                if (y_recent[i]) > (y_recent[i-1]):
                    back += 1
                if (y_recent[i]) == (y_recent[i-1]):
                    equ += 1            
            if front > (lenrec - equ)/2 * 1.4 :
                #now going front
                dontrec = 1
                #애매하게 공이 위에있을때가(천천히 표류중일때) 문제면 그냥 여기서 sleep 해버리는 것도?    
                print("무시합니다!")
            if back > (lenrec - equ)/2 * 1.4 :
                dontrec = 0
                print("접수합니다!")
#접수, 무시를 하는 코드를 빼고 싶다면 여기에 dontrec = 0 추가하면 됨.  or if(len(y_recent)) > lenrec이후 여기까지 지우기.          
      #  print("x_history")
     #   print (x_history)
        
        if (len(z_recent) > lenrec):
            del z_recent[0]
#        print(z_recent)        
        if len(z_recent) == lenrec:#혹시 처음 시작할때 len을 다 못채워서 안잡히진 않는지 체크하고 고칠것.
            if dontrec == 0: #제대로된 방향일때만 체크한다.
                plus = 0
                minus = 0
                equ = 0
                for i in range(1, len(z_recent)): 
                    if (z_recent[i]) < (z_recent[i-1]):
                        plus += 1
                    if (z_recent[i]) > (z_recent[i-1]):
                        minus += 1
                    if (z_recent[i]) == (z_recent[i-1]):
                        equ += 1            
                #네트를 지나가 버렸을 경우
                if max(y_recent) > net and timing_h == 0:#대체 시작 (net를 지나친 경우)즉, 최저값이 나왔으며 네트뒤에서부터 왔는데 최고값이 없을 때 시작)
                    z_high = max(z_history) 
                    subh_in = z_history.index(z_high)
                    y_high = y_history[subh_in]
                    testh += 1 #그냥 테스트용
                    timing_h = 1
                    timing_l = 0
                    print("sub_highest")
                    sub_h = 1
                    
                if plus > (lenrec - equ)/2 * 1.4 :
                    #nowup
                    if pastdown == 1:
                
                    
                        z_low = min(z_recent)
                        lpoint = z_recent.index(z_low) #최저값의 리스트 위치
                        y_low = (y_recent[lpoint])
                        print("lowest")
                        testl += 1 #그냥 잘 돌아가나 세보려고 해둠
                        
                        #lock1.acquire()
                        timing_l = 1
                        #lock1.release()
                    pastup = 1
                    pastdown = 0
    
                
                if minus > (lenrec - equ)/2 * 1.4 :
                    #nowdown
                    if pastup == 1 and (sub_h == 0):
                        z_high = max(z_recent)
                        hpoint = z_recent.index(z_high) #최고값의 리스트 위치
                        y_high = (y_recent[hpoint])
                        print("highest")
                        testh += 1 #그냥 테스트 용
                        
                        #lock2.acquire()
                        timing_h = 1
                        #lock2.release()      
                        #lock1.acquire()
                        timing_l = 0
                        #lock2.release()
                    pastup = 0
                    pastdown = 1
                    
        if timing_h == 1 and timing_l == 1:
            
            sameyin = y_low + y_low - ry
            ccnt = 0
            check = 1
            while check:
                try:
                    index_ = y_history.index(sameyin) #동등한 y에 해당하는 인덱스를 찾아 저장
                    
                    break
                except:
                    sameyin -= 1
                    ccnt += 1
                    if ccnt == 15:
                        suc = 3
                        check = 0
            if suc != 3:
                rz = z_history[index_] #동등한y의 인덱스가 붙었을 당시의 z를 받음.
# 여기에서 탁구공이 튀면서 손실이 좀 일어나니까 그거 보완하기위해 좀 낮추는 것도 좋을듯.
                lockgz.acquire()
                gotz = 1
                lockgz.release()                    
                
            else: #low점과 비슷한 것의 index를 찾을 수 없을 때
                if y_high - y_low != 0:
                    rz = z_high * (y_low - ry) / (y_high - y_low)
                    lockgz.acquire()
                    gotz = 1                    
                    lockgz.release()
                    
                    suc = 0
                else:
                    rz = 50#적당한값. 대충 때려맞히기 좋은 값, z는 어차피 고만고만할지도..
                    lockgz.acquire()
                    gotz = 1                   
                    lockgz.release() 
                    suc = 0
                    print("도전")#대회당일에는 쪽팔리니까 print 뺄 것.

            print("opencv1, trz 전송시작")
            trz = rz * conz - ztrans

            #여기에 trz를 아두이노로 보내는 코드가 위치하도록 한다.
            robot.write(trz)
            while True:
                if gotz == 0:        #opencv2에서 로봇으로 보내고나면 이걸 0으로 만들것.            
                    timing_h = 0
                    timing_l = 0
                    sub_h = 0
                    y_history = []
                    z_history = []
                    y_recent = []
                    z_recent = []
                    break
                time.sleep(0.01)
            print("한세트 후 gotz(1)바꾸기 성공")
                
                        
                    
               # - (rx - 탁구대 중앙값)
               # rz 
               #탁구대 보는 시야 따라서 일반적인 xz 좌표계로 줄 것.
        #  기존rz, 중력가속도 문제로 뺐다. rz = zh * (yl - ry) / (yh - yl)
      #  print("y_history")
       # print (y_history)		# otherwise, compute the thickness of the line and
    
    	# loop over the set of tracked points
        for i in range(1, len(pts)):
    		# if either of the tracked points are None, ignore
    		# them
            if pts[i - 1] is None or pts[i] is None:
                continue
    
    		# draw the connecting lines
       #     thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
            #cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)
        
    	# show the frame to our screen
        cv2.imshow("Frame", frame)
        
    
        key = cv2.waitKey(1) & 0xFF
     
    	# if the 'q' key is pressed, stop the loop
        if key == ord("q"):
            break
    
    print(testh)
    print(testl)
    # if we are not using a video file, stop the camera video stream
    if not args.get("video", False):
        vs.stop()
     
        
        
    # otherwise, release the camera
    else:
        vs.release()
     
    # close all windows
    cv2.destroyAllWindows()
    
def opencv2():#x체크
    global timing_h
    global timing_l
#    global lock1
#    global lock2
    global gorob
    global rz
    global gotz #z가 저장되었는지 확인.
    global trz
    global client
    
    arduino = serial.Serial('COM6', 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0)

    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video",
    	help="path to the (optional) video file")
    ap.add_argument("-b", "--buffer", type=int, default=64,
    	help="max buffer size")
    args = vars(ap.parse_args())
    lower_orange = np.array([15,0,50])  
    upper_orange = np.array([20,255,255])
    pts = deque(maxlen=args["buffer"])
    vs = VideoStream(0).start()
    time.sleep(3.0)
    goth = 0
    gotl = 0
#    x_history = [] #경향성 체크
 #   y_history = [] #경향성 체
   
    hh = 0
    ll = 0
   # x_tend2 = [] #레일이 미리 이동해두기 위함. 추가 필요
    #testh = 0 # 테스트용.
    #testl = 0
    #pastdown = 0
    #pastup = 0
    mid = 300 #탁구대 정중앙 x(천장캠 프레임 기준),       추후 정확하게 변경
    arm = 18 #로봇팔길이 
    ztrans = 30 #프레임 바닥에 찍히는 z~로봇 어깨cell 회전축까지의 높이,단위는 cm. 추후 바꿈.
    conx = 0.3 # 변환상수 (추후 바꿈)
    conz = 0.4 #변환상수 (추후 바꿈)
    pastx = 0
    # define the lower and upper boundaries of the "green"
    # ball in the HSV color space, then initialize the
    # list of tracked points
    lower_orange = np.array([10,100,50])  
    upper_orange = np.array([70,245,250])
    pts = deque(maxlen=args["buffer"])

    while True:
    	# grab the current frame
        frame = vs.read()
     
    	# handle the frame from VideoCapture or VideoStream
        frame = frame[1] if False else frame
     
    	# if we are viewing a video and we did not grab a frame,q
    	# then we have reached the end of the video
        if frame is None:
            break
     
    	# resize the frame, blur it, and convert it to the HSV
    	# color space
        frame = imutils.resize(frame, width=600)
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
     
    	# construct a mask for the color "green", then perform
    	# a series of dilations and erosions to remove any small
    	# blobs left in the mask
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
    
    	# find contours in the mask and initialize the current
    	# (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        center = None
        y_coor2 = 0
        x_coor2 = 0
    	# only proceed if at least one contour was found
        if len(cnts) > 0:
    		# find the largest contour in the mask, then use
    		# it to compute the minimum enclosing circle and
    		# centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            y_coor2 = int(M["m10"] / M["m00"])
            x_coor2 = int(M["m01"] / M["m00"])
            center = (int(M["m10"] / M["m00"]),int(M["m01"] / M["m00"])) 
            #print(center)
    		# only proceed if the radius meets a minimum size
            if radius > 10:
    			# draw the circle and centroid on the frame,
    			# then update the list of tracked points
                cv2.circle(frame, (int(x), int(y)), int(radius),
    				(0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)
        
    	# update the points queue
        pts.appendleft(center)
        
#        
#        if len(x_recent) == lenrec:
#            right = 0
#            left = 0
#            equ = 0
#            for i in range(1, len(x_recent)): 
#                if (x_recent[i]) < (x_recent[i-1]):
#                    right += 1
#                if (x_recent[i]) > (x_recent[i-1]):
#                    left += 1
#                if (x_recent[i]) == (x_recent[i-1]):
#                    equ += 1            
                    
        #최고, 최저점에 다다랐을때의 x,y를 저장.
        if timing_h == 1 and goth == 0:
            hh = 1
            time.sleep(0.001)
        if timing_l == 1 and gotl == 0:
            ll = 1
            time.sleep(0.001)
        if hh == 1:
            xh = (x_coor2)
            yh = (y_coor2)
            goth = 1
            hh = 0
        if ll == 1:
            xl = x_coor2
            yl = y_coor2
            gotl  = 1
            ll = 0
        if (goth == 1) and (gotl == 1):
         
            if (yh-yl) != 0:
                rx = xl - ((yh-ry)*(xh-xl))/(yh-yl)
        #        rz = zh * (yl - ry) / (yh - yl)
                # - (rx - 탁구대 중앙값)
                # rz 
                #탁구대 보는 시야 따라서 일반적인 xz 좌표계로 줄 것.
                goth = 0
                gotl = 0
                gorob = 1
            else:
                print("error: yh와 yl이 같습니다. (frame2) 제 2안으로 계산하겠습니다.")
                rx = x_coor2
                gorob = 1
                goth = 0
                gotl = 0
                print("차선의 rx값 획득")
            while gorob:
                if gorob == 1 and gotz == 1:
                    #여기에 통신 코드를 집어넣고 로봇에게 전달한다.
                    #통신 잘 되면 로봇팔 xz가 비독립적이므로 그부분을 보완한다.
                    print("opencv2, rx값을 출력")
                    print(rx)
                    xx = arm*arm - trz*trz
                    lxl = math.sqrt(xx)
                    xaxis = rx - mid #중앙선기준 음양으로 구분
                    xcm = xaxis * const #x축을 cm단위로 변환
                    
                    if xcm >= 0:
                        robx = lxl + 7.5
                    else:
                        robx = -lxl - 7.5
                        
                    railx = xcm - robx
                    trx = railx - pastx
                    #
                    client.send(message.encode('utf-8'))
                    #
                    pastx = trx
                    print("로봇으로 전송")
                    lockgz.acquire()
                    gotz = 0
                    lockgz.release()
                    gorob = 0
                    goth = 0
                    gotl = 0

            
        for i in range(1, len(pts)):
    		# if either of the tracked points are None, ignore
    		# them
            if pts[i - 1] is None or pts[i] is None:
                continue
    
    		# draw the connecting lines
       #     thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
            #cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)
        
    	# show the frame to our screen
        cv2.imshow("Frame2", frame)
    
    
        key = cv2.waitKey(1) & 0xFF
     
    	# if the 'q' key is pressed, stop the loop
        if key == ord("q"):
            break            
                
        

    # if we are not using a video file, stop the camera video stream
    if not args.get("video", False):
        vs.stop()
     
    # otherwise, release the camera
    else:
        vs.release()
     
    # close all windows
    cv2.destroyAllWindows()
        
    
fir = threading.Thread(target = opencv1, )
fir.start()
sec = threading.Thread(target = opencv2,)
sec.start()
