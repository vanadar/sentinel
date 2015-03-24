#!/usr/bin/python

# SENTINEL
# A USB rocket launcher face-tracking solution
# For Linux and Windows
#
# Installation: see README.md
#
# Usage: sentinel.py [options]
#
# Options:
# -h, --help            show this help message and exit
# -l ID, --launcher=ID  specify VendorID of the missile launcher to use.
#                         Default: '2123' (dreamcheeky thunder)
#   -d, --disarm          track faces but do not fire any missiles
#   -r, --reset           reset the turret position and exit
#   --nd, --no-display    do not display captured images
#   -c NUM, --camera=NUM  specify the camera # to use. Default: 0
#   -s WIDTHxHEIGHT, --size=WIDTHxHEIGHT
#                         image dimensions (recommended: 320x240 or 640x480).
#                         Default: 320x240
#   -v, --verbose         detailed output, including timing information

import os
import sys
import threading
import time
from optparse import OptionParser
from turret import Turret
from camera import Camera

# http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

if __name__ == '__main__':
    if (sys.platform == 'linux2' or sys.platform == 'darwin') and not os.geteuid() == 0:
        sys.exit("Script must be run as root.")

    # command-line options
    parser = OptionParser()
    parser.add_option("-l", "--launcher", dest="launcherID", default="2123",
                      help="specify VendorID of the missile launcher to use. Default: '2123' (dreamcheeky thunder)",
                      metavar="LAUNCHER")
    parser.add_option("-d", "--disarm", action="store_false", dest="armed", default=True,
                      help="track faces but do not fire any missiles")
    parser.add_option("-r", "--reset", action="store_true", dest="reset_only", default=False,
                      help="reset the turret position and exit")
    parser.add_option("--nd", "--no-display", action="store_true", dest="no_display", default=False,
                      help="do not display captured images")
    parser.add_option("-c", "--camera", dest="camera", default='0',
                      help="specify the camera # to use. Default: 0", metavar="NUM")
    parser.add_option("-s", "--size", dest="image_dimensions", default='320x240',
                      help="image dimensions (recommended: 320x240 or 640x480). Default: 320x240",
                      metavar="WIDTHxHEIGHT")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="detailed output, including timing information")
    parser.add_option("-m", "--mode", dest="mode", default="follow",
                      help="choose behaviour of sentry. options (follow, sweep, guard) default:follow", metavar="NUM")
    parser.add_option("-o", "--origin", dest="origin", default="0.5,0.5",
                      help="direction to point initially - an x and y decimal percentage. Default: 0.5,0.5",
                      metavar="X,Y")
    parser.add_option("-p", "--profile", action="store_true", dest="profile", default=False,
                      help="enable detection of facial side views - better detection but slower")

    opts, args = parser.parse_args()
    print opts

    # additional options
    opts = AttributeDict(vars(opts))  # converting opts to an AttributeDict so we can add extra options
    opts.haar_file = 'haarcascade_frontalface_default.xml'
    opts.haar_profile_file = 'haarcascade_profileface.xml'

    turret = Turret(opts)
    camera = Camera(opts)
    turretCentered = True

    manual = False

    char = None

    def getch():  # define non-Windows version
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        termios.tcflow(fd, termios.TCION)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ord(ch) == 27:
                ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
        return ord(ch)

    def keypress():
        global char
        while True and not e.isSet():
            char = getch()

    def leave():
        turret.dispose()
        camera.dispose()
        e.set()
        thread.join()
        print "bye"

    thread = threading.Thread(None, keypress, ())
    e = threading.Event()
    thread.start()

    camera_on_move = True

    while not camera.new_frame_available:
        # wait for first frame to be captured
        time.sleep(.001)

    if not opts.reset_only:
        while True:
            if char and not manual:
                manual = True
                turret.launcher.ledOff()
                print "Manual mode"
            try:
                if manual:
                    face_detected, x_adj, y_adj, face_y_size = camera.face_detect()

                    if not opts.no_display:
                        camera.display()

                    if char:
                        key = char

                        if key == 27:
                            leave()

                        if key == 32:
                            if camera_on_move:
                                camera_on_move = False
                                turret.launcher.turretStop()
                            else:
                                turret.launcher.turretFire()
                                time.sleep(3.5)
                                turret.launcher.turretStop()
                        if key == 67:
                            camera_on_move = True
                            turret.launcher.turretRight()
                        if key == 68:
                            camera_on_move = True
                            turret.launcher.turretLeft()
                        if key == 66:
                            camera_on_move = True
                            turret.launcher.turretDown()
                        if key == 65:
                            camera_on_move = True
                            turret.launcher.turretUp()

                        if key == 97 or key == 102 or key == 103 or key == 115:
                            camera_on_move = True
                            print "Auto mode"
                            turret.launcher.ledOff()
                            manual = False

                        if key == 103:
                            print "Guard"
                            opts.mode = "guard"
                        elif key == 115:
                            print "Sweep"
                            opts.mode = "sweep"
                        elif key == 102:
                            print "Follow"
                            opts.mode = "follow"

                        char = None
                else:
                    start_time = time.time()
                    face_detected, x_adj, y_adj, face_y_size = camera.face_detect()
                    detection_time = time.time()

                    if not opts.no_display:
                        camera.display()

                    trackingDuration = turret.updateTrackingDuration(face_detected)

                    # if target is already centered in sights take the shot
                    turret.ready_aim_fire(x_adj, y_adj, face_y_size, face_detected, camera)

                    if face_detected:
                        # face detected: move turret to track
                        if opts.verbose:
                            print "adjusting turret: x=" + str(x_adj) + ", y=" + str(y_adj)
                        turret.adjust(x_adj, y_adj)
                        turretCentered = False
                    elif (opts.mode == "guard") and (trackingDuration < -10) and (not turretCentered):
                        # If turret is in guard mode and has lost track of its target
                        # it should reset to the position it is guarding
                        turret.center()
                        turretCentered = True
                    elif (opts.mode == "sweep") and (trackingDuration < -3):
                        turret.sweep()

                    movement_time = time.time()
                    # force camera to obtain next image after movement has completed
                    camera.new_frame_available = False

                    if opts.verbose:
                        print "total time: " + str(movement_time - start_time)
                        print "detection time: " + str(detection_time - start_time)
                        print "movement time: " + str(movement_time - detection_time)

            except KeyboardInterrupt:
                leave()
                break
