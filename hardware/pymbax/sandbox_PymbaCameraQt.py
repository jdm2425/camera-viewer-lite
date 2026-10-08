import logging
import hardware
from hardware.pymbax.qt import PymbaCameraWidget

def test_widget():
    w=PymbaCameraWidget()
    w.format_changed.connect(lambda:print('format changed'))
    w.online_changed.connect(lambda:print('online changed'))
    w.show()
    return w

if __name__=="__main__":
    logging.basicConfig()
    logging.getLogger(hardware.pymbax.__name__).setLevel(level=logging.DEBUG)
        
    # Note this leaves the camera open
    figs=[]
    w=test_widget()
    figs.append(w)
