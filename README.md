### 1. 架构设计

![毕业设架构图](https://picturebed-raccoon.oss-cn-hangzhou.aliyuncs.com/default/%E6%AF%95%E4%B8%9A%E8%AE%BE%E6%9E%B6%E6%9E%84%E5%9B%BE.png)

### 2. demo

实现一个经过Edgex, Mqtt Device Service, Robot Service, ROS Node这几个层次，由北到南通过mqtt连通的demo系统，实现简单控制小车前进刹车的功能。具体包含以下步骤

#### 2.1 edgex平台搭建

采用docker运行, 参考文档https://docs.edgexfoundry.org/2.3/examples/Ch-ExamplesAddingMQTTDevice/

```sh
git clone git@github.com:edgexfoundry/edgex-compose.git
cd edgex-compose
git checkout levski # 本文档使用levski分支，即2.3版本
cd compose-builder
make gen ds-mqtt mqtt-broker no-secty ui # 使用make gen命令生成docker-compose.yml文件，这里添加了ds-mqtt mqtt-broker ui no-secty镜像，ds-mqtt用于注册默认device-service设备服务，mqtt-broker运行在1883端口作为mqtt代理，no-secty表明以非安全模式运行
docker-compose up -d # 拉取镜像，启动服务
```


#### 2.2 注册设备

##### 2.2.1 docker启动时自动注册方式

https://docs.edgexfoundry.org/2.3/examples/Ch-ExamplesAddingMQTTDevice/ 此文档中提到的方式是可以通过在docker compose的yml文件中指定本地配置文件路径的方式，使得部署的镜像自带对应的device和device profile

1.新建三个文件夹和两个文件，保持如下架构

```
  - custom-config
    |- devices
       |- my.custom.device.config.toml
    |- profiles
       |- my.custom.device.profile.yml
```
```toml
# my.custom.device.config.toml 该文件描述设备相关配置信息
# Pre-define Devices
[[DeviceList]]
  Name = "my-custom-device" # 设备名称
  ProfileName = "my-custom-device-profile" # 设备使用的profile名称
  Description = "MQTT device is created for test purpose" # 设备描述
  Labels = [ "MQTT", "test" ] # 设备标签
  [DeviceList.Protocols]
    [DeviceList.Protocols.mqtt]
       # Comment out/remove below to use multi-level topics
       CommandTopic = "CommandTopic" # 单级topic名称，用于mqtt通信
       # Uncomment below to use multi-level topics
       # CommandTopic = "command/my-custom-device"
    [[DeviceList.AutoEvents]] # 自动化事件，这段代码可以不要
       Interval = "30s"
       OnChange = false
       SourceName = "message"
```

```yaml
# 设备元信息my.custom.device.profile.yml文件，核心包含deviceResources和deviceCommands两部分
name: "my-custom-device-profile" # profile文件的名称
manufacturer: "iot"
model: "MQTT-DEVICE"
description: "Test device profile"
labels:
  - "mqtt"
  - "test"
deviceResources: # 设备资源列表，列表中没有hidden的部分也会和command一起出现在前端可执行的命令中
  -
    name: randnum
    isHidden: true
    description: "device random number"
    properties:
      valueType: "Float32"
      readWrite: "R"
  -
    name: ping
    isHidden: true
    description: "device awake"
    properties:
      valueType: "String"
      readWrite: "R"
  -
    name: message
    isHidden: false
    description: "device message"
    properties:
      valueType: "String"
      readWrite: "RW"
  -
    name: json
    isHidden: false
    description: "JSON message"
    properties:
      valueType: "Object"
      readWrite: "RW"
      mediaType: "application/json"

deviceCommands: # 设备可以执行的命令，这里使用的resourceOperations必须在上面已定义过
  -
    name: values
    readWrite: "R" #RW对应该设备该方法是否有GET和SET,R表明在values命令下，只有get方法，而没有set方法
    isHidden: false
    resourceOperations:
        - { deviceResource: "randnum" }
        - { deviceResource: "ping" }
        - { deviceResource: "message" }
```

2.在`docker-compose.yml`文件同级目录下新建`docker-compose.override.yml`，替换/path/to/custom-config部分，并重启docker服务

```yaml
 # docker-compose.override.yml

 version: '3.7'

 services:
     device-mqtt:
        environment:
          DEVICE_DEVICESDIR: /custom-config/devices
          DEVICE_PROFILESDIR: /custom-config/profiles
        volumes:
        - /path/to/custom-config:/custom-config # 这里的/path/to/custom-config替换为上一步自己建立的custom-config文件夹路径，用于指定本地配置文件路径
```

```sh
docker-compose stop && docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d # 用改写过的override文件更新并重启镜像服务
```

3.重启完毕后，打开Localhost:4000端口，在设备管理列表，可以看到默认已经注册了一个my-custom-device-profile和my-custom-device

##### 2.2.2 4000端口UI手动添加方式（推荐）

也可以在edgex运行之后访问localhost：4000端口，在前端ui中新增对应的设备元信息和注册对应的设备

1. 添加设备元信息，将上面的`my.custom.device.profile.yml`中的内容复制到前端新增设备元信息的界面

![image-20240415193945549](https://picturebed-raccoon.oss-cn-hangzhou.aliyuncs.com/default/image-20240415193945549.png)

2. 注册设备，点击添加设备，设备服务选择device-mqtt, 设备元信息选择刚刚创建的my-custom-device-profile，设备信息自拟，自动事件可跳过，创建设备通信协议选择自定义协议模板，创建一个名为mqtt的协议，协议属性添加一个key为CommandTopic, value也为CommandTopic的部分（对应上一种方法的my.custom.device.config.toml中描述的属性）

![image-20240415194407200](https://picturebed-raccoon.oss-cn-hangzhou.aliyuncs.com/default/image-20240415194407200.png)



#### 2.3 MQTT代理的实现

- 在一台机器（大概率是edgex部署的机器）上用docker运行一个eclipse-mosquitto:2.0.15镜像充当mqtt-broker代理，`docker-compose.yml`内容见下文。mqtt-broker服务启动后，默认监听127.0.0.1:1883端口，需要更改为本机ip方可被其他机器访问。

- 比较操蛋的是，代理机器和edgex宿主机好像不能分开，否则宿主机的59882不认识代理机的1883端口，只认识本机的1883端口

  ```yaml
  # docker-compose.yml
  # 如果是在edgex宿主机，这段代码在make gen的时候就已经生成了
      mqtt-broker:
          command:
            - /usr/sbin/mosquitto
            - -c
            - /mosquitto-no-auth.conf
          container_name: edgex-mqtt-broker
          hostname: edgex-mqtt-broker
          image: eclipse-mosquitto:2.0.15
          networks:
            edgex-network: null
          ports:
            - mode: ingress
              host_ip: 127.0.0.1 # 需要更改
              target: 1883
              published: "1883"
              protocol: tcp
          read_only: true
          restart: always
          security_opt:
            - no-new-privileges:true
          user: 2002:2001
  ```

#### 2.4 MQTT Mock Device的实现与测试

##### 2.4.1使用javascript脚本模拟mock-device的实现与测试

参考文档https://github.com/hobbyquaker/mqtt-scripts，有两种实现方式

1. 使用mqtt-script运行js脚本，订阅对应的commandTopic, 执行完毕后，发布ResponseTopic, ResponseTopic可以被59882端口的CoreCommand服务接收并展示在前端

```sh
npm install -g mqtt-scripts # 需要nodejs和npm
cd /path/to/scripts # 存放js脚本的目录
touch mock-device.js
vim mock-device.js # 写入对应javascript代码，见下文
mqtt-scripts -d ./ # mqtt-scripts会自动load该目录下的所有js脚本，并输出以下信息
mqtt-scripts -d ./ --url mqtt://ip # 特别的，当该模拟设备和非本机broker通信时，需要加上对应代理服务机器ip
```

```sh
2022-08-12 09:52:42.086 <info>  mqtt-scripts 1.2.2 starting
2022-08-12 09:52:42.227 <info>  mqtt connected mqtt://127.0.0.1 # 设备已连接到mqtt代理，开始监听topic，在连接非本机的mqtt-broker服务时，会显示对应ip
2022-08-12 09:52:42.733 <info>  /mock-device.js loading # 对应脚本的虚拟设备服务已启动
```

2. 使用docker镜像运行

```sh
cd /path/to/scripts # 存放js脚本的目录
touch mock-device.js
vim mock-device.js # 写入对应代码，见下文
docker run --rm --name=mqtt-scripts \
    -v ./:/scripts  --network host \ #用本文件夹下的文件替换镜像中/scripts文件夹中的文件
    dersimn/mqtt-scripts --dir /scripts
    

docker run --rm --name=mqtt-scripts \
    -v ./:/scripts  --network host \ 
    dersimn/mqtt-scripts --dir /scripts
    --url mqtt://ip # 特别的，当该模拟设备和非本机broker通信时，需要加上对应代理服务机器ip
```

mock-device.js的代码如下

```javascript
//本js语法并不规范，只能依赖于mqtt-scripts或者docker解析运行
function getRandomFloat(min, max) {
    return Math.random() * (max - min) + min;
}

const deviceName = "my-device";
let message = "test-message";
let json = {"name" : "My JSON"};

// DataSender sends async value to MQTT broker every 15 seconds 每15秒发布DataTopic, 向mqtt-broker同步自身信息
schedule('*/15 * * * * *', ()=>{
    let body = {
        "name": deviceName,
        "cmd": "randnum",
        "randnum": getRandomFloat(25,29).toFixed(1)
    };
    publish( 'DataTopic', JSON.stringify(body));
});

// CommandHandler receives commands and sends response to MQTT broker
// 1. Receive the reading request, then return the response 
// 2. Receive the set request, then change the device value 
// 订阅CommandTopic, 即在创建设备时指定的Topic
subscribe( "CommandTopic" , (topic, val) => {
    var data = val;
    if (data.method == "set") {//在set方法中，根据topic负载信息中方法名和需要写入的数据, 更新本设备信息，并发布responseTopic
        switch(data.cmd) {
            case "message":
                console.log("in message set method")
                message = data[data.cmd];
              break;
            case "json":
                console.log("in json set method")
                json = data[data.cmd];
                break;
        }
    }else{//在get方法中，根据topic负载信息中方法名，读取本设备对应信息，更新到负载中，并发布responseTopic
        switch(data.cmd) {
            case "ping":
              data.ping = "pong";
              break;
            case "message":
              data.message = message;
              break;
            case "randnum":
                data.randnum = 12.123;
                break;
            case "json":
                data.json = json;
                break;
          }
    }
    publish( "ResponseTopic", JSON.stringify(data));
});
```


##### 2.4.2 使用python脚本模拟mock-device的实现与测试（推荐）

相比于上一种js脚本，py的可移植性更强，不需要依赖docker或者mqtt-scripts, 只需要python环境和对应的包即可(这么看来可移植性好像也不强)

```python
```

该脚本运行在小车上，连接到对应的mqtt-broker之后，即可向MQTT-Broker1883订阅CommandTopic和发布ResponseTopic

#### 2.5 core-command(:59882)与mqtt-broker(:1883)的关系

- 对于get和set方法，前端点击try按钮等同于向localhost:59882发送PUT和GET指令，59882接收到PUT和GET指令后，会自动向1883发布对应的CommandTopic


```sh
curl http://localhost:59882/api/v2/device/name/my-custom-device/message # message-GET指令 my-custom-device 对应添加设备时设备的名称，如果写错将收不到topic
curl http://localhost:59882/api/v2/device/name/my-custom-device/message \ 
# message-PUT指令 \
    -H "Content-Type:application/json" -X PUT  \
    -d '{"message":"Hello!"}'
```

- 同时，59882会自动订阅responseTopic, 并将设备返回结果以json展示


```json
//message GET命令返回
{
    "apiVersion": "v2",
    "statusCode": 200,
    "event": {
      "apiVersion": "v2",
      "id": "06ff457b-d789-41a3-8c84-1ce5522b4f87",
      "deviceName": "my-custom-device",
      "profileName": "my-custom-device-profile",
      "sourceName": "message",
      "origin": 1.7132456688195346e+18,
      "readings": [
        {
          "id": "639f8d6e-8b35-410f-8c63-be72018ccabb",
          "origin": 1.7132456688195313e+18,
          "deviceName": "my-custom-device",
          "resourceName": "message",
          "profileName": "my-custom-device-profile",
          "valueType": "String",
          "value": "Hello!"
        }
      ]
    }
}
//message PUT命令返回
{"apiVersion":"v2","statusCode":200}
```

- 事实上1883端口中的topic有效负载是如下格式，可以在js脚本中添加`console.log`输出查看


```
//set message CommandTopic/ResponseTopic的有效负载
{
  cmd: 'message',
  message: 'Hello',
  method: 'set',
  uuid: 'c397e54e-b515-4c43-b1c6-7342ca957cfa'
}
//get message CommandTopic的有效负载
{
  cmd: 'message',
  method: 'get',
  uuid: 'ef12e68a-64ea-4a53-8092-d99c5559bffb'
}
//get message ResponseTopic的有效负载, 比CommandTopic多了一个message属性，把本设备的message信息添加到了负载里返回
{"cmd":"message","method":"get","uuid":"ef12e68a-64ea-4a53-8092-d99c5559bffb","message":"Hello"}
//set json 的CommandTopic
{
  cmd: 'json',
  json: 'name: "caoxin"',
  method: 'set',
  uuid: 'e5dcbf0b-283a-4b42-ac3f-abf2e6647900'
}
//set json responsetopic
{"cmd":"json","json":"name: \"caoxin\"","method":"set","uuid":"e5dcbf0b-283a-4b42-ac3f-abf2e6647900"}

```

- 对于values这种复合命令，59882相当于同时发送了三个CommandTopic, 并且将三个ResponseTopic拼接起来作为json返回
- 禁止使用脚本越过59882端口直接向MQTT-Broker1883发送CommandTopic和直接尝试从MQTT-Broker1883获取ResponseTopic，这是不符合架构的

## 刘海涛圣经

除了系统架构图，别的都不能一样

本科45-50页论文

系统概述部分也是要自己的语言

不能文档风格，要有清晰的叙述脉络，文字要多

各种类图多画

不能GPT

UI好看点
