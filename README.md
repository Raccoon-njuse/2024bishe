# Edgex启动
```sh 
cd edgexService-docker
#TODO docker-compose.yml中的core-command和mqtt-broker的ip要换broker机器的ip
docker-compose -f docekr-compose.yml -f docker-compose.override.yml up -d
```
# 小车启动
```sh
cd rosDevice-python
#TODO1 改一下每个小车脚本头部的ip为broker机器的ip
#TODO2 每个小车里的 forward, backward, left, right, stop等方法，按照前端接口重新定义了一下，要重写
cp device1.py 小车1里面 && 在小车里run
cp device2.py 小车2里面 && 在小车里run
cp device3.py 小车3里面 && 在小车里run
#提供了一个脚本，在修改完device1.py后可以对应生成device2.py device3.py
chmod +x ./copy.sh
./copy.sh
```

