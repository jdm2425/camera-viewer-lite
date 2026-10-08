import maestro_usb
import time

if __name__=="__main__":

        com='COM4'
        ttl='COM5'
        #create servo object, set unlimited speed, move servo to 90 degrees angle
        servo = maestro_usb.Controller(ttl,com)
        
        
        
        
        
        servo.set_speed(0,200)
        servo.set_acceleration(0,5)
        
        servo.set_target(0,1000)
        time.sleep(0.5)
        servo.set_target(0,2000)
        
        
        
        
        
        
        
        d=0
        loop=0
        while (loop<10):
        print("Iteration = ", loop)
        if(d==0):
                servo.set_target(0,1400)
                d=1
        else:
                servo.set_target(0,1600)
                d=0
        time.sleep(0.5)
        loop=loop+1
        
        print(servo.get_config())   
        
        
        
        # testing create and destroy:
        del servo
        servo = maestro_usb.Controller(com,ttl)
