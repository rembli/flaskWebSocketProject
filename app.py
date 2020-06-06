####################################################################################
# LIBRARIES
####################################################################################

# Flask and Flask web socket library
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from time import sleep

# libraries to manage images
import base64
import threading
import binascii
from io import BytesIO
from PIL import Image
import cv2, numpy, colour


####################################################################################
# UTILITY FUNCTIONS FOR IMAGE PROCESSING OVER THE NETWORK
####################################################################################

def base64_to_pil_image(base64_img):
    return Image.open(BytesIO(base64.b64decode(base64_img)))

def pil_image_to_base64(pil_image):
    buf = BytesIO()
    pil_image.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue())

def pil_image_to_cv2(pil_image):
    return cv2.cvtColor(numpy.array(pil_image), cv2.COLOR_RGB2BGR)

def cv2_to_pil_image(cv2_image):
    img = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img)


####################################################################################
# CAMERA CLASS (with integrated messaging queue)
####################################################################################

class Camera():
    def __init__(self):
        self.to_process = []
        self.to_output = []
       
        thread = threading.Thread(target=self.keep_processing, args=())
        thread.daemon = True
        thread.start()

    def enqueue_input(self, input):
        self.to_process.append(input)

    def keep_processing(self):
        while True:
            self.process_one()
            sleep(0.01)        

    def process_one(self):
        if not self.to_process:
            return

        # input is an ascii string 
        input_str = self.to_process.pop(0)

        # convert it to a cv2 image
        input_img = base64_to_pil_image(input_str)
        cv2_image = pil_image_to_cv2 (input_img)

        ####################################################################################
        # DO SOME NICE IMAGE MANIPULATION WITH CV2 (e.g. gray)
        
        cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
    
        ####################################################################################

        # output_str is a base64 string in ascii
        output_img = cv2_to_pil_image (cv2_image)
        output_str = pil_image_to_base64(output_img)

        # convert eh base64 string in ascii to base64 string in _bytes_
        self.to_output.append(binascii.a2b_base64(output_str))

    def get_frame(self):
        while not self.to_output:
            sleep(0.05)
        return self.to_output.pop(0)


####################################################################################
# FLASK WITH WEB SOCKET SUPPORT
####################################################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['DEBUG'] = True

# Set async_mode to 'threading' because f*** apache webserver at Jelastic cannot handle anything else
sio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
# sio = SocketIO(app)

# Init (server-side) camera

camera = Camera()

# INDEX.HTML

@app.route('/')
def index():
    return render_template('index.html')

# VIDEO HTTP-STREAMING TO SERVE MANIPULATED IMAGES

def gen():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# WEB SOCKET ENDPOINT TO RECEIVE NEW IMAGES

@sio.on('connect', namespace='/imagestream')
def test_connect():
    print ("client connected")

@sio.on('input image', namespace='/imagestream')
def test_message(input):
    input = input.split(",")[1]
    camera.enqueue_input(input)

if __name__ == '__main__':
    sio.run(app)
