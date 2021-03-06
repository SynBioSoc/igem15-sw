from werkzeug.contrib.fixers import ProxyFix
from flask import Flask
from flask import request, Response
import json
import requests
import time

import sys
sys.path.append("/home/pi/igem15-sw/")

from gui.webshell.mjpgstreamer import MjpgStreamer
import gui.webshell.locker
from gui.webshell.timelapser import Timelapser
from gui.webshell import edf
from hw.ledmotorcontrol import driver
from img_processing.identificationTesting.autofocus import test_autofocus

tlThread = None

app = Flask(__name__)

@app.route("/timelapse/set/<delay>/<times>")
def timelapse(delay, times):
    global tlThread

    if gui.webshell.locker.lockobj[0] != request.authorization.username and not gui.webshell.locker.lock(request.authorization.username, "timelapse"):
        return 'Webshell locked by %s for %s' % (gui.webshell.locker.lockobj[0], gui.webshell.locker.lockobj[1])

    # stop thread
    if tlThread is not None:
        tlThread.stop()
        tlThread.join()
    # start thread
    tlThread = Timelapser([request.authorization.username, int(delay), int(times)])
    tlThread.start()
    return 'Timelapse set'

@app.route("/timelapse/get/")
def get_if_timelapse():
    global tlThread
    if tlThread is not None:
        return json.dumps(tlThread.tl)
    else:
        return json.dumps(['', 0, 0])

## todo: move to seperate module
@app.route("/zstack/<amount>/<times>")
def zstack(amount, times):
    imgs = []

    driver.move_motor(2, -int(int(amount)*(int(times)-1)/2))
    time.sleep(2)
    for _ in range(int(times)):
        imgs.append(requests.get("http://127.0.0.1:9002/?action=snapshot").content)
        if _ != (int(times)-1):
            driver.move_motor(2, int(amount))
            time.sleep(2)
    driver.move_motor(2, int(int(amount)*(int(times)-1)/2))

    ret = edf.edf(imgs, request.authorization.username)
    return ret

@app.route("/autofocus/")
def autofocus():
    test_autofocus(timeout=90)
    return "done"

@app.route("/")
def root():
    return '<meta http-equiv="refresh" content="0;URL=/webshell/main.html">'

@app.route("/control/power/<onoff>")
def control_power(onoff):
    if onoff == "on":
        MjpgStreamer.start()
        return 'started'
    elif onoff == "off":
        MjpgStreamer.stop()
        return 'stopped'
    return 'error'

@app.route("/capture/")
def capture():
    return MjpgStreamer.captureImg(request.authorization.username)

@app.route("/capture_stream/")
def capture_stream():
    return Response(MjpgStreamer.captureImgStream(), mimetype='image/png')

@app.route("/capture_scale/<cal>")
def capture_scale(cal):
    return MjpgStreamer.scaleCaptureImg(MjpgStreamer.captureImg(request.authorization.username), cal)

@app.route("/calibrate/<len>/<rad>/<actual>")
def calibrate(len, rad, actual):
    const = float(actual)/float(len)
    jsn = [const * 800, const * 600]

    with open('/home/pi/igem15-sw/gui/portal/webshell/fov.json', 'w') as outfile:
        json.dump(jsn, outfile)
    return 'done'

@app.route("/snap/")
def snap():
    return MjpgStreamer.captureSnap(request.authorization.username)

@app.route("/snap_scale/<cal>")
def snap_scale(cal):
    return MjpgStreamer.scaleCaptureImg(MjpgStreamer.captureSnap(request.authorization.username), cal)

@app.route("/prune/")
def prune():
    return MjpgStreamer.prunedir("/home/pi/igem15-sw/captured/%s" % request.authorization.username)

@app.route("/pruneall/")
def pruneall():
    if request.authorization.username == "admin":
        return MjpgStreamer.prunedir("/home/pi/igem15-sw/captured/", 524288000)
    else:
        return "Error - cannot delete other user's data unless you are admin"

@app.route("/iso/set/<set>")
def iso_set(set):
    MjpgStreamer.iso = str(int(set))
    return 'set iso, restart stream to see'

@app.route("/iso/get/")
def iso_get():
    return MjpgStreamer.iso

@app.route("/control/led/<mode>/<setting>")
def control_led(mode, setting):
    error = "No LED board connected"

    if mode == "get":
        r = driver.get_led_mode()
        return str(r) if r is not None else error
    elif mode == "set":
        driver.set_led_mode(int(setting))
        return 'Set!'
    elif mode == "toggle":
        driver.toggle_led()
        r = driver.get_led_mode()
        return str(r) if r is not None else error
    return 'error'

@app.route("/control/motor/<axis>/<amount>")
def control_mot(axis, amount):
    driver.move_motor(int(axis), int(amount))
    return 'done'

app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == '__main__':
    app.run('0.0.0.0', 9001, debug=True)
