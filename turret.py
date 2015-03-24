import os
import time
import cv2
import sys
import math
import usb
import camera

class Launcher(): # a parent class for our low level missile launchers.
#Contains general movement commands which may be overwritten in case of hardware specific tweaks.
            
    # roughly centers the turret at the origin
    def center(self, x_origin=0.5, y_origin=0.5):
        print 'Centering camera ...'
        self.moveToPosition(x_origin,y_origin)

    def moveToPosition(self, right_percentage, down_percentage): 
        self.turretLeft()
        time.sleep( self.x_range)
        self.turretRight()
        time.sleep( right_percentage * self.x_range)
        self.turretStop()

        self.turretUp()
        time.sleep( self.y_range)
        self.turretDown()
        time.sleep( down_percentage * self.y_range) 
        self.turretStop()

    def moveRelative(self, right_percentage, down_percentage):
        if (right_percentage>0):
            self.turretRight()
        elif(right_percentage<0):
            self.turretLeft()
        time.sleep( abs(right_percentage) * self.x_range)
        self.turretStop()
        if (down_percentage>0):
            self.turretDown()
        elif(down_percentage<0):
            self.turretUp()
        time.sleep( abs(down_percentage) * self.y_range)
        self.turretStop()

# Launcher commands for USB Missile Launcher (VendorID:0x1130 ProductID:0x0202 Tenx Technology, Inc.)
class Launcher1130(Launcher):
    # Commands and control messages are derived from
    # http://sourceforge.net/projects/usbmissile/ and http://code.google.com/p/pymissile/

    # 7 Bytes of Zeros to fill 64 Bit packet (8 Bit for direction/action + 56 Bit of Zeros to fill packet)
    cmdFill = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # Low level launcher driver commands
    # this code mostly taken from https://github.com/nmilford/stormLauncher
    # with bits from https://github.com/codedance/Retaliation
    def __init__(self):
        # HID detach for Linux systems...not tested with 0x1130 product
        self.dev = usb.core.find(idVendor=0x1130, idProduct=0x0202)
        if self.dev is None:
                raise ValueError('Missile launcher not found.')
        if sys.platform == "linux2":
            try:
                if self.dev.is_kernel_driver_active(1) is True:
                    self.dev.detach_kernel_driver(1)
                else:
                    self.dev.detach_kernel_driver(0)
            except Exception, e:
                pass

        self.dev.set_configuration()

        self.missile_capacity = 3
#experimentally estimated speed scaling factors 
        self.y_speed = 0.48
        self.x_speed = 0.64    
        #approximate number of seconds of movement to reach end of range  
        self.x_range = 7
        self.y_range = 3

        #directional constants
        self.LEFT   =   1
        self.RIGHT  =   2
        self.UP     =   4
        self.DOWN   =   8
        
        self.BLANK_data   =   [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x08]
        self.LEFT_data   =   [0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x08, 0x08]
        self.RIGHT_data  =   [0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x08, 0x08]
        self.UP_data     =   [0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x08, 0x08]
        self.DOWN_data   =   [0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x08, 0x08]
        self.FIRE   =   [0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x08, 0x08]
        self.STOP   =   [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x08]

    def turretLeft(self):
        cmd = self.LEFT_data + self.cmdFill
        self.turretMove(cmd)

    def turretRight(self):
        cmd = self.RIGHT_data + self.cmdFill
        self.turretMove(cmd)

    def turretUp(self):
        cmd = self.UP_data + self.cmdFill
        self.turretMove(cmd)

    def turretDown(self):
        cmd = self.DOWN_data + self.cmdFill
        self.turretMove(cmd)

    def turretDirection(self, directionCommand):
        cmd = self.BLANK_data + self.cmdFill
        if (directionCommand & self.LEFT == self.LEFT ):
                cmd[1] = 0x1
        elif (directionCommand & self.RIGHT == self.RIGHT ):
                cmd[2] = 0x1

        if (directionCommand & self.UP == self.UP ):
                cmd[3] = 0x1
        elif (directionCommand & self.DOWN == self.DOWN ):
                cmd[4] = 0x1

        self.turretMove(cmd)

    def turretFire(self):
        cmd = self.FIRE + self.cmdFill
        self.turretMove(cmd)

    def turretStop(self):
        cmd = self.STOP + self.cmdFill
        self.turretMove(cmd)

    def ledOn(self):
        # cannot turn on LED. Device has no LED.
        pass

    def ledOff(self):
        # cannot turn off LED. Device has no LED.
        pass

    # Missile launcher requires two init-packets before the actual command can be sent.
    # The init-packets consist of 8 Bit payload, the actual command is 64 Bit payload
    def turretMove(self, cmd):
        # Two init-packets plus actual command
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x01, [ord('U'), ord('S'), ord('B'), ord('C'), 0, 0, 4, 0])
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x01, [ord('U'), ord('S'), ord('B'), ord('C'), 0, 64, 2, 0])
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x00, cmd)



# Launcher commands for DreamCheeky Thunder (VendorID:0x2123 ProductID:0x1010)
class Launcher2123(Launcher):
    # Low level launcher driver commands
    # this code mostly taken from https://github.com/nmilford/stormLauncher
    # with bits from https://github.com/codedance/Retaliation
    def __init__(self):
        self.dev = usb.core.find(idVendor=0x2123, idProduct=0x1010)

        # HID detach for Linux systems...tested with 0x2123 product

        if self.dev is None:
            raise ValueError('Missile launcher not found.')
        if sys.platform == "linux2":
            try:
                if self.dev.is_kernel_driver_active(1) is True:
                    self.dev.detach_kernel_driver(1)
                else:
                    self.dev.detach_kernel_driver(0)
            except Exception, e:
                pass

        #some physical constraints of our rocket launcher
        self.missile_capacity = 4
        #experimentally estimated speed scaling factors 
        self.y_speed = 0.48
        self.x_speed = 1.2    
        #approximate number of seconds of movement to reach end of range  
        self.x_range = 6.5  # this turret has a 270 degree range of motion and if this value is set
                            # correcly should center to be facing directly away from the usb cable on the back
        self.y_range = 0.75

        #define directional constants        
        self.DOWN = 0x01
        self.UP = 0x02
        self.LEFT = 0x04
        self.RIGHT = 0x08



    def turretUp(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretDown(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretLeft(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretRight(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretDirection(self,direction):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, direction, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretStop(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretFire(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def ledOn(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def ledOff(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

 

class Turret():
    def __init__(self, opts):
        self.opts = opts

        # Choose correct Launcher
        if opts.launcherID == "1130":
            self.launcher = Launcher1130()
        else:
            self.launcher = Launcher2123()

        self.missiles_remaining = self.launcher.missile_capacity
        self.origin_x, self.origin_y = map(float, opts.origin.split(','))

        self.killcam_count = 0
        self.trackingTimer = time.time()
        self.locked_on = 0

        self.bufferPhoto = 0

        # initial setup
        # self.center()
        self.launcher.ledOff()

        if opts.mode == "sweep":
            self.approx_x_position = self.origin_x
            self.approx_y_position = self.origin_y
            self.sweep_x_direction = 1
            self.sweep_y_direction = 1
            self.sweep_x_step = 0.05
            self.sweep_y_step = 0.2

    # turn off turret properly
    def dispose(self):
        self.launcher.turretStop()
        self.launcher.ledOff()

    # roughly centers the turret to the middle of range or origin point if specified
    def center(self):
        self.launcher.center(self.origin_x, self.origin_y)

    # adjusts the turret's position (units are fairly arbitary but work ok)
    def adjust(self, right_dist, down_dist):
        right_seconds = right_dist * self.launcher.x_speed
        down_seconds = down_dist * self.launcher.y_speed

        direction_right = 0
        direction_down = 0

        if right_seconds > 0:
            direction_right = self.launcher.RIGHT
        elif right_seconds < 0:
            direction_right = self.launcher.LEFT

        if down_seconds > 0:
            direction_down = self.launcher.DOWN
        elif down_seconds < 0:
            direction_down = self.launcher.UP

        # move diagonally first
        self.launcher.turretDirection(direction_down | direction_right)

        # move remaining distance in one direction
        if abs(right_seconds) > abs(down_seconds):
            time.sleep(abs(down_seconds))
            self.launcher.turretDirection(direction_right)
            time.sleep(abs(right_seconds-down_seconds))            
        else:
            time.sleep(abs(right_seconds))
            self.launcher.turretDirection(direction_down)
            time.sleep(abs(down_seconds-right_seconds))          
        
        self.launcher.turretStop()

        # OpenCV takes pictures VERY quickly, so if we use it, we must
        # add an artificial delay to reduce camera wobble and improve clarity
        time.sleep(.2)

    # stores images of the targets within the killcam folder
    def killcam(self, camera):
        # create killcam dir if none exists, then find first unused filename
        if not os.path.exists("killcam"):
            os.makedirs("killcam")
        filename_locked_on = os.path.join("killcam", "lockedon" + str(self.killcam_count) + ".jpg")
        while os.path.exists(filename_locked_on):
            self.killcam_count += 1
            filename_locked_on = os.path.join("killcam", "lockedon" + str(self.killcam_count) + ".jpg")

        # save the image with the target being locked on
        cv2.imwrite(filename_locked_on, camera.frame_mod)

        # wait a little bit to attempt to catch the target's reaction.
        time.sleep(1)  # tweak this value for most hilarious action shots

        # force camera to obtain image after this point
        camera.new_frame_available = False

        # take another picture of the target while it is being fired upon
        filename_firing = os.path.join("killcam", "firing" + str(self.killcam_count) + ".jpg")
        camera.face_detect(filename=filename_firing) 
        if not self.opts.no_display:
            camera.display()

        self.killcam_count += 1

    def save_image(self, camera):
        photo_dir = "photoForTraining"
        if not os.path.exists(photo_dir):
            os.makedirs(photo_dir)

        self.bufferPhoto += 1
        filename = os.path.join(photo_dir, "photo" + str(self.bufferPhoto) + ".jpg")
        cv2.imwrite(filename, camera.current_frame)

    # compensate vertically for distance to target
    def projectile_compensation(self, target_y_size):
        if target_y_size > 0:
            # objects further away will need a greater adjustment to hit target
            adjust_amount = 0.1 * math.log(target_y_size)
        else:
            # log 0 will throw an error, so handle this case even though unlikely to occur
            adjust_amount = 0

        # tilt the turret up to try to increase range
        self.adjust(0, adjust_amount)
        if self.opts.verbose:
            print "size of target: %.6f" % target_y_size
            print "compensation amount: %.6f" % adjust_amount

    # turn on LED if face detected in range, and fire missiles if armed
    def ready_aim_fire(self, x_adj, y_adj, target_y_size, face_detected, camera=None):
        fired = False

        if face_detected and camera:
            self.save_image(camera)

        if face_detected and abs(x_adj) < .05 and abs(y_adj) < .05:
            self.launcher.ledOn()  # LED will turn on when target is locked
            if self.opts.armed:
                # aim a little higher if our target is in the distance
                self.projectile_compensation(target_y_size)

                self.launcher.turretFire()
                self.missiles_remaining -= 1
                fired = True

                if camera:
                    self.killcam(camera)  # save a picture of the target

                time.sleep(3)  # disable turret for approximate time required to fire

                print 'Missile fired! Estimated ' + str(self.missiles_remaining) + ' missiles remaining.'

                if self.missiles_remaining < 1:
                    self.launcher.ledOff()
                    raw_input("Ammunition depleted. Awaiting order to continue assault. [ENTER]")
                    self.missiles_remaining = 4
            else:
                print 'Turret trained but not firing because of the --disarm directive.'
        else:
            self.launcher.ledOff()
        return fired

    #keeps track of length of time since a target was found or lost
    def updateTrackingDuration(self, is_locked_on):
        
        if is_locked_on:
            if self.locked_on:
                trackingDuration = time.time() - self.trackingTimer
            else:
                self.locked_on = True
                self.trackingTimer = time.time()
                trackingDuration = 0
        else: #not locked on
            if self.locked_on:
                self.locked_on = False
                self.trackingTimer = time.time()
                trackingDuration = 0
            else:
                trackingDuration = -(time.time() - self.trackingTimer)
        return trackingDuration #negative values indicate time since target seen

    #increments the sweeping behaviour of a turret on patrol
    def sweep(self):
        self.approx_x_position += self.sweep_x_direction * self.sweep_x_step
        if self.approx_x_position<=1 and self.approx_x_position>=0:
            #move in x direction first
            self.launcher.moveRelative(self.sweep_x_step * self.sweep_x_direction, 0)
        else:
            #reached end of x range.  move in y direction and switch x sweep direction
            self.sweep_x_direction = -1 * self.sweep_x_direction
            self.approx_x_position += self.sweep_x_direction * self.sweep_x_step 
            self.approx_y_position += self.sweep_y_direction * self.sweep_y_step
            if(self.approx_y_position<=1 and self.approx_y_position>=0): 
                #take a step in current y direction
                self.launcher.moveRelative(0, 0.2 * self.sweep_y_direction)
            else:
                #swap y direction and take a step in that direction instead
                self.sweep_y_direction = -1 * self.sweep_y_direction
                self.approx_y_position += self.sweep_y_direction * 2 * self.sweep_y_step # reverse previous y step and take a new step 
                self.launcher.moveRelative(0, self.sweep_y_step * self.sweep_y_direction)
        time.sleep(.2) #allow camera to stabilize
