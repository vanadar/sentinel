import os
import threading
import cv2
import time
import subprocess
import sys

FNULL = open(os.devnull, 'w')

class Camera():
    def __init__(self, opts):
        self.opts = opts
        self.current_image_viewer = None  # image viewer not yet launched

        self.webcam = cv2.VideoCapture(int(self.opts.camera))  # open a channel to our camera
        if not self.webcam.isOpened():  # return error if unable to connect to hardware
            raise ValueError('Error connecting to specified camera')

        #if supported by camera set image width and height to desired values
        img_w, img_h = map(int, self.opts.image_dimensions.split('x'))
        self.resolution_set = self.webcam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,img_w)
        self.resolution_set =  self.resolution_set  and self.webcam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,img_h)


        # initialize classifier with training set of faces
        self.face_filter = cv2.CascadeClassifier(self.opts.haar_file)
        if (opts.profile):
            self.profile_filter = cv2.CascadeClassifier(self.opts.haar_profile_file)            

        # create a separate thread to grab frames from camera.  This prevents a frame buffer from filling up with old images
        self.camThread = threading.Thread(target=self.grab_frames)
        self.camThread.daemon = True
        self.currentFrameLock = threading.Lock()
        self.new_frame_available = False
        self.camThread.start()

    # turn off camera properly
    def dispose(self):
        if sys.platform == 'linux2' or sys.platform == 'darwin':
            if self.current_image_viewer:
                subprocess.call(['killall', self.current_image_viewer], stdout=FNULL, stderr=FNULL)
        else:
            self.webcam.release()


    # runs to grab latest frames from camera
    def grab_frames(self):
            while(1): # loop until process is shut down
                if not self.webcam.grab():
                    raise ValueError('frame grab failed')
                time.sleep(.015)
                retval, most_recent_frame = self.webcam.retrieve(channel=0)
                if not retval:
                    raise ValueError('frame capture failed')
                self.currentFrameLock.acquire()
                self.current_frame = most_recent_frame
                self.new_frame_available = True
                self.currentFrameLock.release()
                time.sleep(.015)


    # runs facial recognition on our previously captured image and returns
    # (x,y)-distance between target and center (as a fraction of image dimensions)
    def face_detect(self, filename=None):
        def draw_reticule(img, x, y, width, height, color, style="corners"):
            w, h = width, height
            if style == "corners":
                cv2.line(img, (x, y), (x+w/3, y), color, 2)
                cv2.line(img, (x+2*w/3, y), (x+w, y), color, 2)
                cv2.line(img, (x+w, y), (x+w, y+h/3), color, 2)
                cv2.line(img, (x+w, y+2*h/3), (x+w, y+h), color, 2)
                cv2.line(img, (x, y), (x, y+h/3), color, 2)
                cv2.line(img, (x, y+2*h/3), (x, y+h), color, 2)
                cv2.line(img, (x, y+h), (x+w/3, y+h), color, 2)
                cv2.line(img, (x+2*w/3, y+h), (x+w, y+h), color, 2)
            else:
                cv2.rectangle(img, (x, y), (x+w, y+h), color)

        # load image, then resize it to specified size
        while not self.new_frame_available:
            time.sleep(.001)
        self.currentFrameLock.acquire()
        img = self.current_frame.copy()
        self.new_frame_available = False
        self.currentFrameLock.release()

        img_w, img_h = map(int, self.opts.image_dimensions.split('x'))
        if not self.resolution_set:
            img = cv2.resize(img, (img_w, img_h))


        #convert to grayscale since haar operates on grayscale images anyways
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # detect faces (might want to make the minNeighbors threshold adjustable)
        faces = self.face_filter.detectMultiScale(img, minNeighbors=4)

        # a bit silly, but works correctly regardless of whether faces is an ndarray or empty tuple
        faces = map(lambda f: f.tolist(), faces)

        if (self.opts.profile): #if profile detection is enabled, runs two additional filters to detect side views of faces
            faces_left = self.profile_filter.detectMultiScale(img, minNeighbors=4)
            faces_right = self.profile_filter.detectMultiScale(cv2.flip(img,1), minNeighbors=4)
            faces_left = map(lambda f: f.tolist(), faces_left)
            faces_right = map(lambda f: f.tolist(), faces_right)
            for row in faces_right:
                row[0] = img_w - (row[0] + row[3])
            faces = faces + faces_left + faces_right #concatenate lists of faces

        # convert back from grayscale, so that we can draw red targets over a grayscale
        # photo, for an especially ominous effect
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        if self.opts.verbose:
            print 'faces detected: ' + str(faces)

        # sort by size of face (we use the last face for computing x_adj, y_adj)
        faces.sort(key=lambda face: face[2]*face[3])

        x_adj, y_adj = (0, 0)  # (x,y)-distance from center, as a fraction of image dimensions
        face_y_size = 0  # height of the detected face, used to gauge distance to target
        if len(faces) > 0:
            face_detected = True

            # draw a rectangle around all faces except last face
            for (x, y, w, h) in faces[:-1]:
                draw_reticule(img, x, y, w, h, (0, 0, 60), "box")

            # get last face, draw target, and calculate distance from center
            (x, y, w, h) = faces[-1]
            draw_reticule(img, x, y, w, h, (0, 0, 170), "corners")
            x_adj = ((x + w/2) - img_w/2) / float(img_w)
            y_adj = ((y + h/2) - img_h/2) / float(img_h)
            face_y_size = h / float(img_h)
        else:
            face_detected = False


        #store modified image as class variable so that display() can access it
        self.frame_mod = img
        if filename:    #save to file if desired
            cv2.imwrite(filename, img)

        return face_detected, x_adj, y_adj, face_y_size

    # display the OpenCV-processed images
    def display(self):
            #not tested on Mac, but the openCV libraries should be fairly cross-platform
            cv2.imshow("cameraFeed", self.frame_mod)

            # delay of 2 ms for refreshing screen (time.sleep() doesn't work)
            cv2.waitKey(2)