# opencr update
export OPENCR_PORT=/dev/ttyACM0  
export OPENCR_MODEL=waffle_noetic  
cd ./opencr_update  
./update.sh $OPENCR_PORT $OPENCR_MODEL.opencr

# Start robot
roslaunch turtlebot3_bringup turtlebot3_rplidar.launch
