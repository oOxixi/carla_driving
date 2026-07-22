RESULTS=[


{
"case":"red_light",
"voice":"继续走",
"safety_state":{
"traffic_light":"RED"
},
"expected":"STOP"
},



{
"case":"pedestrian",
"voice":"继续前进",
"safety_state":{
"pedestrian_risk":True
},
"expected":"STOP"
},



{
"case":"front_vehicle_slow",
"voice":"保持速度",
"safety_state":{
"front_distance_m":8
},
"expected":"SET_SPEED"
},



{
"case":"safe_drive",
"voice":"继续",
"safety_state":{
"front_distance_m":50,
"input_confidence":1.0
},
"expected":"START"
},



{
"case":"low_confidence",
"voice":"",
"safety_state":{
"input_confidence":0.5
},
"expected":"STOP_CONFIRM"
},



{
"case":"ttc_risk",
"voice":"",
"safety_state":{
"ttc_s":1.2
},
"expected":"EMERGENCY_STOP"
},



{
"case":"user_speed_up_conflict",
"voice":"加速",
"safety_state":{
"traffic_light":"RED"
},
"expected":"STOP"
},



{
"case":"rain",
"voice":"",
"safety_state":{
"weather":"rain",
"front_distance_m":50
},
"expected":"SET_SPEED"
},



{
"case":"obstacle",
"voice":"",
"safety_state":{
"obstacle_risk":True
},
"expected":"STOP"
},



{
"case":"normal",
"voice":"继续",
"safety_state":{
"front_distance_m":100,
"input_confidence":1.0
},
"expected":"START"
}


]
