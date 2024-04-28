#!/bin/bash
if [ ! -f "device1.py" ]; then
    echo "Error: File device1.py not found!"
    exit 1
fi

cp "device1.py" "device2.py"
sed -i 's/Car1/Car2/g' "device2.py"
sed -i 's/device1/device2/g' "device2.py"
cp "device1.py" "device3.py"
sed -i 's/Car1/Car3/g' "device3.py"
sed -i 's/device1/device3/g' "device3.py"

echo "File copied"
