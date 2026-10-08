import numpy as np
import logging
from datetime import datetime
from hardware import Camera
import cv2
import threading
from time import sleep

logger = logging.getLogger(__name__)
#  logger.setLevel(logging.DEBUG)

""" Driver lock
Every method that wants to access the camera has to acquire this lock
(i.e. wait for everything else to be done) before executing.
This ensures that no 2 methods want to access the camera hardware
or opencv USB driver at the same time
Using RLock (re-entrant lock) as opposed to Lock means
that a single thread can acquire the lock several times (e.g. in sub-functions)
"""
driver_lock = threading.RLock()

image_formats = {'Native' : (1,1), '320x240': (320, 240), '640x480': (640, 480),
            '800x600': (800, 600), '960x720': (960, 720), '1280x960': (1280, 960)}
image_format_names = list(image_formats.keys())
# have to create this manually to get the order actually right
#image_format_names = ['Native','320x240', '640x480', '800x600', '960x720', '1280x960']


class WebcamController(Camera):
    """
    Webcam controller without GUI, using opencv,
    with a worker thread to continuously acquire images for speed
    """
    # Need to keep a list of opened cameras.
    # This is to avoid re-opening them during rescan()
    # or in other camera controllers.
    opened_cams = []

    def __init__(self):
        self.cams_found = None  # list of found cameras
        self.x = None  # x axis
        self.y = None  # y axis
        self.image = None  # image
        self.datetime = None  # datetime.datetime object with timestamp of latest image
        self.worker_thread = None  # thread which continuously takes images
        self.cap_obj = None  # opencv VideoCapture object connecting to camera
        # saves desired camera settings in case the camera has to be re-connected
        self.nominal_settings = dict(
            exposure_time=None, gain=None, format=None)

    def rescan(self):
        logger.debug('Getting # of available cameras. Waiting for driver lock')
        with driver_lock:
            logger.debug('rescan(): have driver lock')
            cams_found = []
            for ii in range(0, 10):
                if ii in self.opened_cams:
                    cams_found.append(ii)
                    continue
                cap_temp = cv2.VideoCapture(ii, cv2.CAP_DSHOW)
                if cap_temp.isOpened() is True:
                    cams_found.append(ii)
                cap_temp.release()
            logger.debug('Found {0} cameras', len(cams_found))
            self.cams_found = cams_found

    def open(self, index=0):
        """ opens one of the webcams that have been found.
        Args:
            index (int):    0 based and refers to the index
            within the found cameras, not the device ID
            passed to cv2.VideoCapture!
        """
        if index > (len(self.cams_found) - 1):
            logger.warning('Camera index out of bounds')
            return
        if not self.cams_found:
            logger.warning('Cannot open camera: No camera found')
            return
        self.close()
        # if self.cams_found[index] in self.opened_cams:
        #     raise ValueError('Camera with device ID {0} is already open.'.format(self.cams_found[index]))
        logger.debug('Opening camera no {0} which is device ID {1}. \
            Waiting for driver lock'.format(
            index, self.cams_found[index]))
        with driver_lock:
            self.cap_obj = cv2.VideoCapture(self.cams_found[index], cv2.CAP_DSHOW)
            if self.cap_obj.isOpened() is False:
                logger.warning('Could not open camera')
                return
            self.nativeformat = np.flip(np.array(self.cap_obj.read()[1].shape[0:2]))
            self._setup_format()
            self.cam_deviceID = self.cams_found[index]
            self.cam_index = index
            self._update_nominal()
            self.online_changed(self.online)
            self.opened_cams.append(self.cam_deviceID)
            logger.debug('...done opening')

    def close(self):
        """ Closes currently opened camera """
        logger.debug('Closing camera')
        if self.online:
            self.stop()
        if self.cap_obj is not None and self.opened is True:
            logger.debug('close(): Waiting for driver lock')
            with driver_lock:
                logger.debug('close(): Have driver lock')
                self.cap_obj.release()
                self.cap_obj = None
            self.opened_cams.remove(self.cam_deviceID)

    def start(self):
        """Starts worker thread for frame grabbing"""
        if not self.opened:
            logger.debug('Not opened. Cannot start')
            return
        logger.debug(
            'WebcamController.start() camera index {0}...'.format(
                self.cam_index))
        self.worker_thread = threading.Thread(target=self._grab_frame)
        self.worker_thread.setDaemon(True)
        self._run_worker = True
        self.worker_thread.start()
        self.online_changed(self.online)
        logger.debug('WebcamController.start() done')

    def stop(self):
        """Stops worker thread"""
        logger.debug('WebcamController.stop()...')
        self._run_worker = False
        while self.online:  # wait for thread to do its last iteration
            sleep(0.01)
        self.online_changed(False)

    def _grab_frame(self):
        """Target function for worker thread: Continuously grab frames"""
        while self._run_worker:
            with driver_lock:
                ret, self._frame_buffer = self.cap_obj.read()
            if ret is False or self._frame_buffer is None:
                # If another WebcamController has accessed this camera,
                # e.g. through rescan() in a different python instance,
                # this ensures that the camera is made available
                # to this controller again
                logger.warning(
                    'Grabbing frame failed for camera {0}. \
                    Trying to re-open camera...'.format(self.cam_index))
                self.cap_obj.release()
                self.cap_obj.open(self.cam_deviceID)
                if self.opened:
                    logger.warning('Re-opening camera successful')
                    self.set(**self.nominal_settings)
                else:
                    self.cap_obj.release()
                    raise Exception('Re-opening camera failed.')
                continue
            self._datetime_buffer = datetime.now()
            self._new_frame = True
            sleep(0.01)  # need to give other worker threads a chance too!

    def _setup_format(self):
        """
        Setup x and y axes
        """
        if not self.opened:
            return
        logger.debug('Setting up axes: Reading image size')
        with driver_lock:
            ret, tmp = self.cap_obj.read()  # read one frame
            if ret is False or tmp is None:
                raise Exception(
                    'Could not _setup_format(): reading frame failed')
            w = self.cap_obj.get(cv2.CAP_PROP_FRAME_WIDTH)
            h = self.cap_obj.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.x = np.arange(w)
        self.y = np.arange(h)[:, None]  # make column vector
        self._update_nominal()
        self.format_changed()

    def _update_nominal(self):
        """Saves camera settings whenever they are changed,
        for the case that the camera has to be reconnected"""
        with driver_lock:
            (ret, tmp) = self.cap_obj.read()
        if ret is False:
            raise Exception(
                'Tried to update nominal camera settings \
                but camera not responding')
        self.nominal_settings['exposure_time'] = self.exposure_time
        self.nominal_settings['gain'] = self.gain
        self.nominal_settings['format'] = '{0:.0f}x{1:.0f}'.format(
            self.image_size[0], self.image_size[1])

    def set_auto_exposure(self, enabled):
        # DirectShow uses 1 for automatic exposure and 0 for manual.
        with driver_lock:
            if not self.opened:
                return False
            if not self.cap_obj.set(cv2.CAP_PROP_AUTO_EXPOSURE, int(enabled)):
                return False
            self.nominal_settings['auto_exposure'] = bool(enabled)
            return True

    def set(self, exposure_time=None, format=None, gain=None, auto_exposure=None):
        """
        Set exposure time, format, gain
        format can be any of the strings that are keys
        in the image_formats dict.
        All the usual resolutions are available, 320x240 and upwards
        """
        if not self.opened:
            return
        with driver_lock:
            if (exposure_time is not None and
                    exposure_time != self.exposure_time):
                logger.debug(
                    'Setting exposure time to {0}'.format(exposure_time))
                self.cap_obj.set(cv2.CAP_PROP_EXPOSURE, exposure_time)
            if format is not None: 
                if format == "Native": newformat = self.nativeformat
                else : newformat = image_formats[format]
                logger.debug('Setting image size: \
                    Width {0}, Height {1}'.format(
                    newformat[0], newformat[1]))
                self.cap_obj.set(cv2.CAP_PROP_FRAME_WIDTH, newformat[0])
                self.cap_obj.set(cv2.CAP_PROP_FRAME_HEIGHT, newformat[1])
                self._setup_format()
            if gain is not None:
                logger.debug('Setting gain to {0}'.format(gain))
                self.cap_obj.set(cv2.CAP_PROP_GAIN, gain)
        self._update_nominal()
        if auto_exposure is not None:
            self.set_auto_exposure(auto_exposure)

    def trigger(self):
        """Trigger acquisition. Since frames are continuously read anyway,
        this simply makes sure that the frame retrieved by wait()
        was acquired after trigger() was called, not before,
        and that each frame is only acquired once"""
        if not self.online:
            logger.debug('Triggered but not online')
            return
        logger.debug(
            'Setting flag to wait for new frame from camera {0}'.format(
                self.cam_index))
        self._new_frame = False

    def wait(self, timeout=5000):
        """Wait until new frame has been acquired by the frame grabber,
        then do the necessary transformations
        to make image useable by rest of lab app code"""
        if not self.online:
            logger.debug('Tried to wait for frame but not online')
            return
        timed_out = False
        logger.debug(
            'Waiting for new frame from camera {0}'.format(self.cam_index))
        start = datetime.now()
        while (not self._new_frame) and (not timed_out):
            timed_out = (datetime.now() -
                         start).total_seconds() > timeout / 1000
            sleep(0.001)
        if self._new_frame:
            # opencv returns x and y swapped, so swap them here
            self.image = np.fliplr(
                self._frame_buffer.transpose(1, 0, 2)).astype(float)
            self.datetime = self._datetime_buffer
            logger.debug(
                'Got new frame from camera {0}'.format(self.cam_index))
        return not timed_out

    @property
    def online(self):
        if self.worker_thread is None:
            return False
        else:
            return self.worker_thread.is_alive()

    @property
    def opened(self):
        if not self.cap_obj:
            return False
        else:
            with driver_lock:
                ret = self.cap_obj.isOpened()
            return ret

    @property
    def exposure_time(self):
        if self.opened:
            with driver_lock:
                ret = self.cap_obj.get(cv2.CAP_PROP_EXPOSURE)
            return ret
        else:
            return None

    @property
    def gain(self):
        if self.opened:
            with driver_lock:
                ret = self.cap_obj.get(cv2.CAP_PROP_GAIN)
            return ret
        else:
            return None

    @property
    def image_size(self):
        if self.opened:
            with driver_lock:
                ret = (self.cap_obj.get(cv2.CAP_PROP_FRAME_WIDTH),
                       self.cap_obj.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return ret
        else:
            return None


if __name__ == "__main__":
    o = WebcamController()
    o.rescan()
    o.open()
    o.set(format='Native')
    o2 = WebcamController()
    o2.rescan()
    o.start()
    # o2.rescan()
