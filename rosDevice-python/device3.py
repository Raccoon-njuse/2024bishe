import random
import time
import json

from paho.mqtt import client as mqtt_client

# broker = '172.31.12.246'   # broker地址，为曹信的Linux
# broker = '192.168.123.12'  # broker地址，为wsl
# broker = '10.195.154.231' 
broker = '172.24.37.153'
port = 1883  # mqtt默认端口
subTopic = "command/device3/#"  # 订阅mqtt指令话题，可使用/分隔
pubTopic = "command/response/"  # 发布mqtt回复话题
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'

message = 'test-message'
myjson = {'name': 'MY JSON'}
isForward = False
isLeft = False
isRight = False
isBackWard = False
# isStop = True
velocity = 0.0
cameraUrl = "http://192.168.1.2:8080/shot.jpg"
dotCloud = "[0, 0, 0, 0, 0, 0, 0]"


def forward():
    # TODO: 发布话题启动小车
    print("ROS Car3 start running...")


def stop():
    # TODO: 发布话题停止小车
    print("ROS Car3 stop running...")


def backward():
    # TODO 后退
    print("ROS Car3 backward")


def left():
    # TODO 左转
    print("ROS Car3 right")


def right():
    # TODO 右转
    print("ROS Car3 right")


def setVelocity(velocity):
    # TODO: 设置小车速度为 velocity (m/s)
    print(f'Setting Velocity to Car3: {velocity} m/s...')


def getVelocity():
    # TODO: 读出小车速度并返回
    print(f'Car3 Current Velocity is: {velocity} m/s...')
    return velocity


def getCameraUrl():
    # TODO: 获取小车摄像头图像流的url并返回
    print(f'Car3 Camera Url is: {cameraUrl}')
    return cameraUrl


def getDotCloud():
    # TODO: 获取小车激光雷达点云矩阵，字符串化并返回
    print(f'Car3 DotCloud is: {dotCloud}')
    return dotCloud


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        global message, myjson, isForward, velocity, cameraUrl, dotCloud, isLeft, isRight, isBackWard
        # print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        words = msg.topic.split('/')
        cmd = words[2]
        method = words[3]
        uuid = words[4]
        response = {}
        if method == 'set':
            data = json.loads(msg.payload.decode())
            if cmd == 'forward' and data['forward']:
                isForward = True
                isBackWard = False
                client.publish(pubTopic + uuid, json.dumps(response))
                forward()
            elif cmd == 'backward' and data['backward']:
                isBackWard = True
                isForward = False
                client.publish(pubTopic + uuid, json.dumps(response))
                forward()
            elif cmd == 'stop' and data['stop']:
                isForward = isBackWard = isLeft = isRight = False
                client.publish(pubTopic + uuid, json.dumps(response))
                stop()
            elif cmd == 'left' and data['left']:
                isLeft = True
                isRight = False
                client.publish(pubTopic + uuid, json.dumps(response))
            elif cmd == 'right' and data['right']:
                isRight = True
                isLeft = False
                client.publish(pubTopic + uuid, json.dumps(response))
            elif cmd == 'velocity':
                velocity = data['velocity']
                client.publish(pubTopic + uuid, json.dumps(response))
                setVelocity(velocity)

        elif method == 'get':
            if cmd == 'velocity':
                response['velocity'] = getVelocity()
                client.publish(pubTopic + uuid, json.dumps(response))
            elif cmd == 'cameraUrl':
                response['cameraUrl'] = getCameraUrl()
                client.publish(pubTopic + uuid, json.dumps(response))
            elif cmd == 'dotCloud':
                response['dotCloud'] = getDotCloud()
                client.publish(pubTopic + uuid, json.dumps(response))

    client.subscribe(subTopic)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
